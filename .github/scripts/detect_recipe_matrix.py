#!/usr/bin/env python3

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(os.environ.get("GITHUB_WORKSPACE", Path(__file__).resolve().parents[2])).resolve()
RECIPES_DIR = REPO_ROOT / "recipes"
VERSION_LINE_RE = re.compile(r'^  "([^"]+)":\s*$')
TOP_LEVEL_KEY_RE = re.compile(r"^(?P<key>[^\s#][^:]*):(?:\s|$)")
FULL_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")


def run_git(*args, check=True):
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            check=check,
            text=True,
            capture_output=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"git {' '.join(args)} failed in {REPO_ROOT}: {exc.stderr.strip() or exc.stdout.strip() or exc}"
        ) from exc


def git_commit_exists(ref):
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{ref}^{{commit}}"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def ensure_git_commit(ref):
    """Fetch an event commit that is no longer reachable after a force-push."""
    if git_commit_exists(ref):
        return

    # Only fetch an exact object ID. Event SHAs are trusted, while accepting an
    # arbitrary ref here would make local and CI behavior harder to reason about.
    if not FULL_SHA_RE.fullmatch(ref):
        raise RuntimeError(f"Git commit is unavailable locally: {ref}")

    run_git("fetch", "--no-tags", "--depth=1", "origin", ref)
    if not git_commit_exists(ref):
        raise RuntimeError(f"Git commit is unavailable after fetching it from origin: {ref}")


def git_file(ref, path):
    spec = f"{ref}:{path}"
    result = subprocess.run(
        ["git", "show", spec],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def parse_conandata_versions(text):
    """Map each version under the top-level `sources:` key to its literal block.

    Only `sources:` is scanned. Other top-level keys such as `patches:` repeat the
    same version keys, and letting their blocks overwrite the source ones would
    hide a url/sha256 bump from compute_changed_versions().
    """
    if not text:
        return {}

    versions = {}
    in_sources = False
    current = None
    block = []

    def flush():
        nonlocal current, block
        if current is not None:
            versions[current] = "\n".join(block).rstrip()
        current = None
        block = []

    for line in text.splitlines():
        top_level = TOP_LEVEL_KEY_RE.match(line)
        if top_level:
            flush()
            in_sources = top_level.group("key").strip() == "sources"
            continue

        if not in_sources:
            continue

        match = VERSION_LINE_RE.match(line)
        if match:
            flush()
            current = match.group(1)
            block = [line]
        elif current is not None:
            block.append(line)

    flush()
    return versions


def list_versions_from_tree(recipe):
    conandata = REPO_ROOT / "recipes" / recipe / "all" / "conandata.yml"
    if not conandata.exists():
        return []
    return sorted(parse_conandata_versions(conandata.read_text()).keys())


def list_versions_from_ref(ref, recipe):
    path = f"recipes/{recipe}/all/conandata.yml"
    return sorted(parse_conandata_versions(git_file(ref, path)).keys())


def compute_changed_versions(base, head, recipe):
    path = f"recipes/{recipe}/all/conandata.yml"
    before = parse_conandata_versions(git_file(base, path))
    after = parse_conandata_versions(git_file(head, path))
    changed = []
    for version in sorted(set(before) | set(after)):
        if before.get(version) != after.get(version):
            changed.append(version)
    return changed


def list_changed_files(base, head):
    act_changed_files = os.environ.get("ACT_CHANGED_FILES", "").strip()
    if act_changed_files:
        return [line.strip() for line in act_changed_files.splitlines() if line.strip()]
    return run_git("diff", "--name-only", f"{base}..{head}").splitlines()


def build_targets(base, head, mode):
    if not os.environ.get("ACT_CHANGED_FILES", "").strip():
        ensure_git_commit(base)
        ensure_git_commit(head)
    changed_files = list_changed_files(base, head)
    targets = {}

    for relpath in changed_files:
        parts = Path(relpath).parts
        if len(parts) < 2 or parts[0] != "recipes":
            continue

        recipe = parts[1]
        recipe_bucket = targets.setdefault(recipe, {"all_versions": False, "versions": set()})

        if len(parts) >= 3 and parts[2] != "all":
            recipe_bucket["versions"].add(parts[2])
            continue

        if len(parts) >= 4 and parts[2] == "all" and parts[3] == "conandata.yml":
            if mode == "all":
                recipe_bucket["all_versions"] = True
            else:
                recipe_bucket["versions"].update(compute_changed_versions(base, head, recipe))
            continue

        recipe_bucket["all_versions"] = True

    matrix = []
    for recipe, state in sorted(targets.items()):
        if state["all_versions"]:
            versions = list_versions_from_tree(recipe) or list_versions_from_ref(head, recipe)
        else:
            versions = sorted(v for v in state["versions"] if v != "all")

        for version in versions:
            matrix.append(
                {
                    "name": recipe,
                    "version": version,
                    "path": f"recipes/{recipe}/all",
                    "reference": f"{recipe}/{version}",
                }
            )

    return matrix


def recipe_dependencies(recipe, candidates, recipes_dir=None):
    """Return the recipes in `candidates` that `recipe` (or its test package) references.

    A plain text scan for "<name>/" string literals: it covers requires(),
    tool_requires() and test_requires() with fixed versions and version ranges, and
    it is only asked about recipes of this repository.
    """
    recipe_dir = (recipes_dir or RECIPES_DIR) / recipe / "all"
    text = ""
    for conanfile in (recipe_dir / "conanfile.py", recipe_dir / "test_package" / "conanfile.py"):
        if conanfile.exists():
            text += conanfile.read_text()
    return {
        other
        for other in candidates
        if other != recipe and re.search(rf"[\"']{re.escape(other)}/", text)
    }


def group_targets(targets, dependencies):
    """Put targets whose recipes depend on each other into one ordered group.

    Each group becomes one CI job that exports all of its recipes and then creates
    them dependencies first, so a recipe can depend on one that is only added in the
    same change. Unrelated recipes stay in separate, parallel jobs.
    """
    recipes = []
    for target in targets:
        if target["name"] not in recipes:
            recipes.append(target["name"])
    deps = {recipe: set(dependencies.get(recipe, ())) & set(recipes) for recipe in recipes}

    parent = {recipe: recipe for recipe in recipes}

    def find(recipe):
        while parent[recipe] != recipe:
            parent[recipe] = parent[parent[recipe]]
            recipe = parent[recipe]
        return recipe

    for recipe, requirements in deps.items():
        for requirement in requirements:
            parent[find(recipe)] = find(requirement)

    components = {}
    for recipe in recipes:
        components.setdefault(find(recipe), []).append(recipe)

    groups = []
    for members in components.values():
        # Kahn's algorithm, taking the alphabetically first ready recipe each round so
        # the order is stable. Recipes left in a cycle are appended alphabetically;
        # exporting everything up front still lets them resolve each other.
        ordered = []
        remaining = sorted(members)
        while remaining:
            ready = [recipe for recipe in remaining if not (deps[recipe] - set(ordered))]
            recipe = ready[0] if ready else remaining[0]
            ordered.append(recipe)
            remaining.remove(recipe)
        groups.append(
            {
                "name": "+".join(ordered),
                "targets": [target for recipe in ordered for target in targets if target["name"] == recipe],
            }
        )

    return sorted(groups, key=lambda group: group["name"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument(
        "--conandata-mode",
        choices=("changed", "all"),
        default="changed",
        help="How to treat changes to recipes/<name>/all/conandata.yml",
    )
    args = parser.parse_args()

    targets = build_targets(args.base, args.head, args.conandata_mode)
    names = {target["name"] for target in targets}
    dependencies = {name: recipe_dependencies(name, names) for name in names}
    payload = {"include": group_targets(targets, dependencies)}
    print(json.dumps(payload))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Failed to detect recipe matrix: {exc}", file=sys.stderr)
        sys.exit(1)
