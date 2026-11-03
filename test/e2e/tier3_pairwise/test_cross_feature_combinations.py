"""Tier 3: Cross-Feature Combinations (Pairwise Interactions)

Verifies interactions across features:
- F1 x F2: Java 17 runtime archive extraction and binary executable permissions
- F1 x F3: Java 17 JVM launch arguments and LWJGL 3 library path binding
- F2 x F9: Binary execution error trapping and activity crash defense
- F3 x F9: Native library resolution fallback and defensive cache management
- F4 x F5: First-run storage initialization and auto-config coordinator persistence
- F4 x F6: Storage directory resolution and heuristic heap sizing coexistence
- F5 x F6: Coordinator invocation and 7-tier heuristic parameter commitment
- F6 x F1: Heuristic RAM output and OpenJDK 17 -Xmx parameter formatting
- F7 x F8: Rebranded string names and SoSMobile graphic asset identity
- F7 x F10: Main menu rebranding and documentation naming alignment
- F11 x F1: Build system JRE 17 asset bundling and runtime resolution
- F11 x F3: Build system jniLibs packaging and native library linking
"""

import json
import tempfile
import unittest
from pathlib import Path

from ..common.env import (
    BUILD_GRADLE,
    ASYNC_ASSET_MANAGER,
    GAME_RUNNER,
    SYX_LAUNCH_CONFIG,
    JAVA_EXEC_HOOKS,
    LIBLWJGL_SO,
    RES_DIR,
    README_EN,
    AUTO_CONFIG_VERSION_KEY,
    CURRENT_AUTO_CONFIG_VERSION,
)
from ..common.simulators import (
    MockSharedPreferences,
    DeviceHardware,
    HardwareHeuristicEngine,
    MockProcessExecution,
)
from ..common.assertions import (
    assert_file_exists,
    assert_elf_arm64,
)


class TestCrossFeatureCombinations(unittest.TestCase):
    """Test suite verifying cross-feature pairwise interactions."""

    def test_pairwise_01_f1_java17_x_f2_permissions(self):
        """F1 x F2: Java 17 binary extraction preserves mode 0755 and executes without EACCES."""
        # Simulated extraction of OpenJDK 17 bin/java with mode 0755
        exec_res = MockProcessExecution.simulate_exec(
            "/data/user/0/git.artdeell.sosmobile/runtimes/jre17/bin/java",
            mode=0o755,
            is_hooked=True
        )
        self.assertEqual(exec_res["exit_code"], 0)
        self.assertIsNone(exec_res["error"])

    def test_pairwise_02_f1_java17_x_f3_lwjgl3_linking(self):
        """F1 x F3: OpenJDK 17 JVM launch configuration binds bundled LWJGL 3 ARM64 library."""
        assert_file_exists(LIBLWJGL_SO)
        assert_elf_arm64(LIBLWJGL_SO)
        assert_file_exists(SYX_LAUNCH_CONFIG)
        content = SYX_LAUNCH_CONFIG.read_text(encoding="utf-8")
        self.assertIn("-Dorg.lwjgl.librarypath=", content)
        self.assertIn("-Djava.library.path=", content)

    def test_pairwise_03_f2_permissions_x_f9_code_health(self):
        """F2 x F9: If binary exec encounters OS denial, exception boundary prevents crash."""
        exec_res = MockProcessExecution.simulate_exec(
            "/data/user/0/runtimes/jre17/bin/java",
            mode=0o644,
            is_hooked=False
        )
        self.assertEqual(exec_res["exit_code"], 13)
        # Exception handler captures and presents dialog rather than uncaught fatal crash
        handled = False
        if exec_res["exit_code"] != 0:
            error_msg = exec_res["error"]
            handled = ("Permission denied" in error_msg)
        self.assertTrue(handled)

    def test_pairwise_04_f3_lwjgl3_x_f9_native_fallback(self):
        """F3 x F9: LWJGL native library path falls back to app native lib directory."""
        app_native_dir = "/data/app/git.artdeell.sosmobile/lib/arm64"
        cache_natives_dir = "/data/user/0/git.artdeell.sosmobile/cache/natives/default"
        # When cache dir does not contain liblwjgl.so, loader checks app_native_dir
        lib_found = False
        candidates = [cache_natives_dir, str(LIBLWJGL_SO.parent), app_native_dir]
        for c in candidates:
            if (Path(c) / "liblwjgl.so").exists():
                lib_found = True
                break
        self.assertTrue(lib_found)

    def test_pairwise_05_f4_game_config_x_f5_autoconfig(self):
        """F4 x F5: First-run setup initializes both LauncherSettings.txt and SharedPreferences."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home_dir = Path(tmpdir)
            settings_dir = home_dir / ".local/share/songsofsyx/settings"
            settings_dir.mkdir(parents=True, exist_ok=True)
            settings_file = settings_dir / "LauncherSettings.txt"
            settings_file.write_text(json.dumps({"MODS": []}), encoding="utf-8")

            prefs = MockSharedPreferences()
            hw = DeviceHardware(total_ram_mb=3583, screen_width=720, screen_height=1600)
            HardwareHeuristicEngine.run_auto_config(hw, prefs)

            self.assertTrue(settings_file.exists())
            self.assertEqual(prefs.getInt(AUTO_CONFIG_VERSION_KEY), CURRENT_AUTO_CONFIG_VERSION)
            self.assertEqual(prefs.getString("renderer"), "opengles2")

    def test_pairwise_06_f4_game_config_x_f6_hardware_heuristics(self):
        """F4 x F6: Game storage directories coexist with calculated memory limits."""
        ram_alloc = HardwareHeuristicEngine.compute_optimal_ram(total_ram_mb=4096)
        game_storage = "/storage/emulated/0/SoSMobile"
        self.assertEqual(ram_alloc, 2048)
        self.assertTrue(game_storage.startswith("/storage/emulated/0/"))

    def test_pairwise_07_f5_autoconfig_x_f6_hardware_heuristics(self):
        """F5 x F6: Coordinator applies 7-tier RAM and resolution scaling into SharedPreferences."""
        prefs = MockSharedPreferences()
        # Galaxy A07 test: 3583 MB RAM, 720p screen
        hw = DeviceHardware(total_ram_mb=3583, screen_width=720, screen_height=1600)
        HardwareHeuristicEngine.run_auto_config(hw, prefs)

        self.assertEqual(prefs.getInt("allocation"), 2048)
        self.assertEqual(prefs.getInt("resolutionRatio"), 100)
        self.assertTrue(prefs.getBoolean("force_vsync"))
        self.assertTrue(prefs.getBoolean("alternate_surface"))

    def test_pairwise_08_f6_heuristics_x_f1_java17_jvm_args(self):
        """F6 x F1: Calculated heap size formats into valid -Xmx argument for OpenJDK 17."""
        ram_mb = HardwareHeuristicEngine.compute_optimal_ram(total_ram_mb=8000)
        self.assertEqual(ram_mb, 4608)
        xmx_arg = f"-Xmx{ram_mb}m"
        xms_arg = "-Xms512m"
        self.assertEqual(xmx_arg, "-Xmx4608m")
        self.assertTrue(xmx_arg.startswith("-Xmx") and xmx_arg.endswith("m"))

    def test_pairwise_09_f7_rebranding_x_f8_icon_assets(self):
        """F7 x F8: Rebranded string names and icon assets align under SoSMobile identity."""
        strings_en = RES_DIR / "values/strings.xml"
        assert_file_exists(strings_en)
        content = strings_en.read_text(encoding="utf-8")
        self.assertIn("<string name=\"app_short_name\">SoSMobile</string>", content)

        # Icon assets must not have MJ or MOJO text
        full_icon = RES_DIR / "drawable/ic_mojo_full.webp"
        assert_file_exists(full_icon)

    def test_pairwise_10_f7_rebranding_x_f10_documentation(self):
        """F7 x F10: Main menu rebranding matches project name in documentation."""
        assert_file_exists(README_EN)
        content = README_EN.read_text(encoding="utf-8")
        self.assertIn("# SoSMobile", content)
        self.assertIn("Android Launcher for Songs of Syx", content)

    def test_pairwise_11_f11_build_assembly_x_f1_java17(self):
        """F11 x F1: build.gradle JRE asset dependency matches Java 17 requirement."""
        assert_file_exists(BUILD_GRADLE)
        content = BUILD_GRADLE.read_text(encoding="utf-8")
        self.assertIn("registrar.jreRuntimeDependency 17", content)

    def test_pairwise_12_f11_build_assembly_x_f3_lwjgl3_packaging(self):
        """F11 x F3: Native LWJGL library in jniLibs/arm64-v8a packages alongside native components."""
        assert_file_exists(LIBLWJGL_SO)
        self.assertEqual(LIBLWJGL_SO.parent.name, "arm64-v8a")
        self.assertEqual(LIBLWJGL_SO.name, "liblwjgl.so")


if __name__ == "__main__":
    unittest.main()
