#!/usr/bin/env python3

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "detect_recipe_matrix.py"
SPEC = importlib.util.spec_from_file_location("detect_recipe_matrix", SCRIPT_PATH)
DETECTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DETECTOR)


class EnsureGitCommitTests(unittest.TestCase):
    def test_existing_commit_does_not_fetch(self):
        with (
            mock.patch.object(DETECTOR, "git_commit_exists", return_value=True),
            mock.patch.object(DETECTOR, "run_git") as run_git,
        ):
            DETECTOR.ensure_git_commit("a" * 40)

        run_git.assert_not_called()

    def test_missing_event_sha_is_fetched_directly(self):
        sha = "a" * 40
        with (
            mock.patch.object(DETECTOR, "git_commit_exists", side_effect=(False, True)),
            mock.patch.object(DETECTOR, "run_git") as run_git,
        ):
            DETECTOR.ensure_git_commit(sha)

        run_git.assert_called_once_with("fetch", "--no-tags", "--depth=1", "origin", sha)

    def test_missing_symbolic_ref_is_not_fetched(self):
        with (
            mock.patch.object(DETECTOR, "git_commit_exists", return_value=False),
            mock.patch.object(DETECTOR, "run_git") as run_git,
        ):
            with self.assertRaisesRegex(RuntimeError, "unavailable locally"):
                DETECTOR.ensure_git_commit("refs/heads/untrusted")

        run_git.assert_not_called()

    def test_fetch_must_make_commit_available(self):
        sha = "b" * 40
        with (
            mock.patch.object(DETECTOR, "git_commit_exists", return_value=False),
            mock.patch.object(DETECTOR, "run_git"),
        ):
            with self.assertRaisesRegex(RuntimeError, "unavailable after fetching"):
                DETECTOR.ensure_git_commit(sha)


class ParseConandataVersionsTests(unittest.TestCase):
    CONANDATA = """\
sources:
  "1.0.0":
    url: "https://example.invalid/1.0.0.tar.gz"
    sha256: "aaaa"
  "2.0.0":
    url: "https://example.invalid/2.0.0.tar.gz"
    sha256: "bbbb"

patches:
  "1.0.0":
    - patch_file: "patches/0001-one.patch"
  "2.0.0":
    - patch_file: "patches/0001-one.patch"
"""

    def test_versions_come_from_sources(self):
        versions = DETECTOR.parse_conandata_versions(self.CONANDATA)

        self.assertEqual(sorted(versions), ["1.0.0", "2.0.0"])
        self.assertIn("sha256: \"aaaa\"", versions["1.0.0"])
        self.assertNotIn("patch_file", versions["1.0.0"])

    def test_patches_block_does_not_shadow_sources(self):
        bumped = self.CONANDATA.replace('sha256: "bbbb"', 'sha256: "cccc"')

        before = DETECTOR.parse_conandata_versions(self.CONANDATA)
        after = DETECTOR.parse_conandata_versions(bumped)

        self.assertEqual(before["1.0.0"], after["1.0.0"])
        self.assertNotEqual(before["2.0.0"], after["2.0.0"])

    def test_a_new_patch_entry_does_not_change_a_source_block(self):
        with_patch = self.CONANDATA.replace(
            '  "2.0.0":\n    - patch_file: "patches/0001-one.patch"',
            '  "2.0.0":\n    - patch_file: "patches/0001-one.patch"\n'
            '    - patch_file: "patches/0002-two.patch"',
        )

        self.assertEqual(
            DETECTOR.parse_conandata_versions(self.CONANDATA),
            DETECTOR.parse_conandata_versions(with_patch),
        )

    def test_patches_declared_before_sources(self):
        head, _, tail = self.CONANDATA.partition("\npatches:\n")
        reordered = "patches:\n" + tail + "\n" + head

        self.assertEqual(
            sorted(DETECTOR.parse_conandata_versions(reordered)), ["1.0.0", "2.0.0"]
        )

    def test_comments_do_not_close_the_sources_block(self):
        commented = "# leading comment\n" + self.CONANDATA.replace(
            '  "2.0.0":', '  # the newest release\n  "2.0.0":'
        )

        self.assertEqual(
            sorted(DETECTOR.parse_conandata_versions(commented)), ["1.0.0", "2.0.0"]
        )

    def test_missing_or_empty_conandata(self):
        self.assertEqual(DETECTOR.parse_conandata_versions(None), {})
        self.assertEqual(DETECTOR.parse_conandata_versions(""), {})
        self.assertEqual(DETECTOR.parse_conandata_versions("patches:\n  \"1.0.0\":\n"), {})


def target(name, version="1.0"):
    return {
        "name": name,
        "version": version,
        "path": f"recipes/{name}/all",
        "reference": f"{name}/{version}",
    }


class RecipeDependenciesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.recipes = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, recipe, text, test_package=None):
        recipe_dir = self.recipes / recipe / "all"
        recipe_dir.mkdir(parents=True)
        (recipe_dir / "conanfile.py").write_text(text)
        if test_package is not None:
            (recipe_dir / "test_package").mkdir()
            (recipe_dir / "test_package" / "conanfile.py").write_text(test_package)

    def dependencies(self, recipe, candidates):
        return DETECTOR.recipe_dependencies(recipe, candidates, recipes_dir=self.recipes)

    def test_requires_with_version_and_range(self):
        self.write("app", 'self.requires("lib/1.0")\nself.tool_requires("tool/[>=2 <3]")\n')

        self.assertEqual(self.dependencies("app", {"app", "lib", "tool", "other"}), {"lib", "tool"})

    def test_test_package_requirements_count(self):
        self.write("lib", "", test_package='self.tool_requires("generator/1.0")\n')

        self.assertEqual(self.dependencies("lib", {"lib", "generator"}), {"generator"})

    def test_name_prefix_is_not_a_dependency(self):
        self.write("omsimulator", 'self.requires("omsimulator-fmi4c/cci.20241114")\n')
        self.write("omsimulator-fmi4c", "")

        self.assertEqual(
            self.dependencies("omsimulator", {"omsimulator", "omsimulator-fmi4c"}), {"omsimulator-fmi4c"}
        )
        self.assertEqual(self.dependencies("omsimulator-fmi4c", {"omsimulator", "omsimulator-fmi4c"}), set())

    def test_single_quotes_and_missing_recipe(self):
        self.write("app", "self.requires('lib/1.0')\n")

        self.assertEqual(self.dependencies("app", {"lib"}), {"lib"})
        self.assertEqual(self.dependencies("removed", {"lib"}), set())


class GroupTargetsTests(unittest.TestCase):
    def test_unrelated_recipes_stay_separate(self):
        groups = DETECTOR.group_targets([target("b"), target("a")], {})

        self.assertEqual(
            groups,
            [{"name": "a", "targets": [target("a")]}, {"name": "b", "targets": [target("b")]}],
        )

    def test_chain_is_ordered_dependencies_first(self):
        targets = [target(name) for name in ("omsimulator", "ctpl", "openmodelica", "msl")]
        dependencies = {"omsimulator": {"ctpl", "openmodelica"}, "openmodelica": {"msl"}}

        groups = DETECTOR.group_targets(targets, dependencies)

        self.assertEqual(len(groups), 1)
        self.assertEqual(
            [t["name"] for t in groups[0]["targets"]], ["ctpl", "msl", "openmodelica", "omsimulator"]
        )
        self.assertEqual(groups[0]["name"], "ctpl+msl+openmodelica+omsimulator")

    def test_versions_of_a_recipe_stay_together(self):
        targets = [target("app", "2.0"), target("lib", "1.0"), target("app", "1.0"), target("lib", "2.0")]

        groups = DETECTOR.group_targets(targets, {"app": {"lib"}})

        self.assertEqual(
            [t["reference"] for t in groups[0]["targets"]], ["lib/1.0", "lib/2.0", "app/2.0", "app/1.0"]
        )

    def test_dependencies_outside_the_change_are_ignored(self):
        groups = DETECTOR.group_targets([target("app")], {"app": {"zlib"}})

        self.assertEqual(groups, [{"name": "app", "targets": [target("app")]}])

    def test_cycle_still_forms_one_group(self):
        groups = DETECTOR.group_targets([target("b"), target("a")], {"a": {"b"}, "b": {"a"}})

        self.assertEqual([g["name"] for g in groups], ["a+b"])

    def test_no_targets(self):
        self.assertEqual(DETECTOR.group_targets([], {}), [])


if __name__ == "__main__":
    unittest.main()
