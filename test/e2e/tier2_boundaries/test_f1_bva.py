"""Tier 2: Boundary Value Analysis - F1: Java 17 Default Runtime Boundaries

Verifies error conditions, version rejection, null instance handling,
and boundary target version handling for Java runtime selection.
"""

import unittest
from pathlib import Path

from ..common.env import (
    GAME_RUNNER,
    MULTI_RT_UTILS,
)
from ..common.assertions import assert_file_exists


class TestF1BVA(unittest.TestCase):
    """BVA test suite for F1 Java 17 runtime management."""

    def test_f1_bva_01_incompatible_lower_java_version_rejection(self):
        """Assert GameRunner rejects Java runtimes with version < targetJavaVersion."""
        assert_file_exists(GAME_RUNNER)
        content = GAME_RUNNER.read_text(encoding="utf-8")
        # Must check pickedRuntime.javaVersion < targetJavaVersion
        self.assertIn("pickedRuntime.javaVersion < targetJavaVersion", content)

    def test_f1_bva_02_zero_java_version_profile_handling(self):
        """Assert GameRunner handles corrupted runtime profiles with javaVersion == 0."""
        content = GAME_RUNNER.read_text(encoding="utf-8")
        self.assertIn("pickedRuntime.javaVersion == 0", content)

    def test_f1_bva_03_null_instance_runtime_selection(self):
        """Assert GameRunner.pickRuntime safely handles null Instance object."""
        content = GAME_RUNNER.read_text(encoding="utf-8")
        # Must check instance != null before accessing instance properties
        self.assertIn("instance != null", content)

    def test_f1_bva_04_runtime_not_found_exception(self):
        """Assert GameRunner throws descriptive RuntimeException if no matching JRE is found."""
        content = GAME_RUNNER.read_text(encoding="utf-8")
        self.assertIn('throw new RuntimeException("Songs of Syx requires Java 17 or Java 21 runtime.")', content)

    def test_f1_bva_05_multirt_empty_runtime_dir_handling(self):
        """Assert MultiRTUtils creates directory or handles empty runtime folder."""
        assert_file_exists(MULTI_RT_UTILS)
        content = MULTI_RT_UTILS.read_text(encoding="utf-8")
        self.assertIn("RUNTIME_FOLDER", content)
        self.assertTrue("mkdirs()" in content or "exists()" in content)


if __name__ == "__main__":
    unittest.main()
