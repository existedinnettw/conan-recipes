#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).with_name("detect_recipe_matrix.py")
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


if __name__ == "__main__":
    unittest.main()
