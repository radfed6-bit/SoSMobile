"""Tier 1: Feature Baseline Coverage - F1: Java 17 Default Runtime

Verifies that the launcher bundles, selects, and executes OpenJDK 17 by default
without requiring manual user installation.
"""

import re
import unittest
from pathlib import Path

from ..common.env import (
    BUILD_GRADLE,
    ASYNC_ASSET_MANAGER,
    GAME_RUNNER,
    MULTI_RT_UTILS,
)
from ..common.assertions import (
    assert_file_exists,
    assert_file_contains_regex,
    assert_file_not_contains_regex,
)


class TestF1Java17Default(unittest.TestCase):
    """Test suite verifying F1 Java 17 default runtime configuration."""

    def test_f1_01_build_gradle_jre_dependency(self):
        """Assert build.gradle bundles Java 17 instead of legacy Java 8."""
        assert_file_exists(BUILD_GRADLE)
        content = BUILD_GRADLE.read_text(encoding="utf-8")
        # Must configure JRE 17 dependency
        pattern = r"registrar\.jreRuntimeDependency\s+17\b"
        self.assertRegex(
            content,
            pattern,
            "app_mojo/build.gradle must specify Java 17 runtime dependency (registrar.jreRuntimeDependency 17)"
        )

    def test_f1_02_async_asset_manager_version_check(self):
        """Assert AsyncAssetManager checks and extracts Java 17 runtime."""
        assert_file_exists(ASYNC_ASSET_MANAGER)
        content = ASYNC_ASSET_MANAGER.read_text(encoding="utf-8")
        # Must check exact JRE name for 17
        self.assertRegex(
            content,
            r"MultiRTUtils\.getExactJreName\(\s*17\s*\)",
            "AsyncAssetManager must check for Java 17 via MultiRTUtils.getExactJreName(17)"
        )

    def test_f1_03_game_runner_requires_java_17(self):
        """Assert GameRunner sets required Java version to 17."""
        assert_file_exists(GAME_RUNNER)
        content = GAME_RUNNER.read_text(encoding="utf-8")
        self.assertRegex(
            content,
            r"requiredJavaVersion\s*=\s*17\b",
            "GameRunner must require Java 17 (requiredJavaVersion = 17)"
        )

    def test_f1_04_game_runner_fallback_targets_java_17(self):
        """Assert GameRunner resolves nearest/preferred runtime with target 17."""
        assert_file_exists(GAME_RUNNER)
        content = GAME_RUNNER.read_text(encoding="utf-8")
        # Must pick runtime targeting Java 17
        self.assertRegex(
            content,
            r"getNearestJreName\(\s*(?:targetJavaVersion|17)\s*\)",
            "GameRunner must resolve nearest JRE targeting 17"
        )

    def test_f1_05_runtime_naming_convention(self):
        """Assert MultiRTUtils defines runtime version matching methods."""
        assert_file_exists(MULTI_RT_UTILS)
        content = MULTI_RT_UTILS.read_text(encoding="utf-8")
        self.assertTrue(
            "getExactJreName" in content and "getNearestJreName" in content,
            "MultiRTUtils must provide getExactJreName and getNearestJreName methods"
        )


if __name__ == "__main__":
    unittest.main()
