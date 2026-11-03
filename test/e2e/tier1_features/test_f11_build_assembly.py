"""Tier 1: Feature Baseline Coverage - F11: Build System & Assembly

Verifies Gradle build configuration, AGP settings, submodules presence,
and build wrapper files.
"""

import unittest
from pathlib import Path

from ..common.env import (
    PROJECT_ROOT,
    BUILD_GRADLE,
    APP_MOJO_DIR,
)
from ..common.assertions import assert_file_exists


class TestF11BuildAssembly(unittest.TestCase):
    """Test suite verifying F11 build system configuration and files."""

    def test_f11_01_gradle_wrapper_files_present(self):
        """Assert gradlew and wrapper files exist and are executable."""
        gradlew = PROJECT_ROOT / "gradlew"
        assert_file_exists(gradlew)
        self.assertTrue(gradlew.stat().st_mode & 0o111, "gradlew must have execute permission")

        wrapper_properties = PROJECT_ROOT / "gradle/wrapper/gradle-wrapper.properties"
        assert_file_exists(wrapper_properties)
        content = wrapper_properties.read_text(encoding="utf-8")
        self.assertIn("distributionUrl", content)

    def test_f11_02_android_application_plugin_and_sdk_configured(self):
        """Assert app_mojo/build.gradle configures com.android.application and compileSdk."""
        assert_file_exists(BUILD_GRADLE)
        content = BUILD_GRADLE.read_text(encoding="utf-8")
        self.assertIn("com.android.application", content)
        self.assertIn("compileSdk", content)
        self.assertIn("minSdkVersion", content)

    def test_f11_03_cmake_native_build_configured(self):
        """Assert build.gradle links CMakeLists.txt for native C/C++ components."""
        assert_file_exists(BUILD_GRADLE)
        content = BUILD_GRADLE.read_text(encoding="utf-8")
        self.assertIn("cmake", content)
        cmakelists = APP_MOJO_DIR / "src/main/jni/CMakeLists.txt"
        assert_file_exists(cmakelists)

    def test_f11_04_gitmodules_submodules_registered(self):
        """Assert .gitmodules registers required native submodules."""
        gitmodules = PROJECT_ROOT / ".gitmodules"
        assert_file_exists(gitmodules)
        content = gitmodules.read_text(encoding="utf-8")
        self.assertIn("glfw", content)
        self.assertIn("mojoexec", content)
        self.assertIn("sdl", content)

    def test_f11_05_root_settings_gradle_includes_app_mojo(self):
        """Assert settings.gradle includes the app_mojo module."""
        settings_gradle = PROJECT_ROOT / "settings.gradle"
        assert_file_exists(settings_gradle)
        content = settings_gradle.read_text(encoding="utf-8")
        self.assertIn(":app_mojo", content)


if __name__ == "__main__":
    unittest.main()
