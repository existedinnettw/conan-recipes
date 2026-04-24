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
    if not text:
        return {}

    versions = {}
    current = None
    block = []
    for line in text.splitlines():
        match = VERSION_LINE_RE.match(line)
        if match:
            if current is not None:
                versions[current] = "\n".join(block).rstrip()
            current = match.group(1)
            block = [line]
        elif current is not None:
            block.append(line)
    if current is not None:
        versions[current] = "\n".join(block).rstrip()
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

    matrix = build_targets(args.base, args.head, args.conandata_mode)
    payload = {"include": matrix}
    print(json.dumps(payload))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Failed to detect recipe matrix: {exc}", file=sys.stderr)
        sys.exit(1)
