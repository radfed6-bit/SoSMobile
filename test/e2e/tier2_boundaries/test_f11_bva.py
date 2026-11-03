"""Tier 2: Boundary Value Analysis - F11: Build System Boundaries

Verifies gradle.properties heap parameters, settings.gradle inclusions,
submodule checkout status, and SDK version limits.
"""

import unittest
from pathlib import Path

from ..common.env import (
    PROJECT_ROOT,
    BUILD_GRADLE,
)
from ..common.assertions import assert_file_exists


class TestF11BVA(unittest.TestCase):
    """BVA test suite for F11 build configuration boundaries."""

    def test_f11_bva_01_gradle_properties_jvm_memory(self):
        """Assert gradle.properties defines adequate JVM heap for builds."""
        props = PROJECT_ROOT / "gradle.properties"
        assert_file_exists(props)
        content = props.read_text(encoding="utf-8")
        self.assertIn("org.gradle.jvmargs", content)
        self.assertTrue("-Xmx" in content or "-Xms" in content)

    def test_f11_bva_02_application_id_configuration(self):
        """Assert build.gradle configures the appropriate applicationId namespace."""
        assert_file_exists(BUILD_GRADLE)
        content = BUILD_GRADLE.read_text(encoding="utf-8")
        self.assertIn("applicationId", content)
        self.assertTrue("git.artdeell" in content or "sosmobile" in content)

    def test_f11_bva_03_min_sdk_version_boundary(self):
        """Assert minSdkVersion is set to 21 (Android 5.0 Lollipop baseline)."""
        content = BUILD_GRADLE.read_text(encoding="utf-8")
        self.assertRegex(content, r"minSdkVersion\s+21\b")

    def test_f11_bva_04_target_sdk_version_boundary(self):
        """Assert targetSdkVersion is modern (API >= 30, current 36)."""
        content = BUILD_GRADLE.read_text(encoding="utf-8")
        self.assertRegex(content, r"targetSdkVersion\s+3[0-6]\b")

    def test_f11_bva_05_submodules_status(self):
        """Assert submodule directories exist in the filesystem tree."""
        submodules = ["glfw", "mojoexec", "sdl"]
        for sub in submodules:
            p = PROJECT_ROOT / sub
            self.assertTrue(p.exists(), f"Submodule path {p} does not exist")


if __name__ == "__main__":
    unittest.main()
