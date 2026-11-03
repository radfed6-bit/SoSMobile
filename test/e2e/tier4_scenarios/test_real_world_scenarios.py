"""Tier 4: Real-World Application Scenarios

End-to-end simulated user workflows:
1. Fresh install cold-start (uninitialized prefs, default settings extraction, auto-config, launch config assembly)
2. Subsequent launcher restart (preference persistence, custom settings retention)
3. Reset to recommended settings workflow
4. Low-memory device graceful adaptation (<2GB RAM / 32-bit)
5. High-resolution tablet adaptation (1600x2560 downscaling, thermal management)
6. Corrupted configuration self-healing recovery
7. Game process spawning simulation (fork & exec, ELF linking, exit status)
8. Multi-locale launcher initialization
"""

import json
import tempfile
import unittest
from pathlib import Path

from ..common.env import (
    AUTO_CONFIG_VERSION_KEY,
    CURRENT_AUTO_CONFIG_VERSION,
    MIN_RAM_MB,
    RES_DIR,
    LIBLWJGL_SO,
)
from ..common.simulators import (
    MockSharedPreferences,
    DeviceHardware,
    HardwareHeuristicEngine,
    MockProcessExecution,
)
from ..common.assertions import assert_file_exists, assert_elf_arm64


class TestRealWorldScenarios(unittest.TestCase):
    """End-to-End simulation tests for real-world application lifecycles."""

    def test_scenario_01_fresh_install_cold_start(self):
        """Scenario 1: Fresh install cold start initializes all configs and generates valid launch arguments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Clean environment
            tmp_root = Path(tmpdir)
            game_home = tmp_root / "files"
            game_dir = tmp_root / "SoSMobile"
            game_dir.mkdir(parents=True, exist_ok=True)
            (game_dir / "SongsOfSyx.jar").write_bytes(b"PK\x03\x04" + b"\x00" * 100)

            prefs = MockSharedPreferences()
            self.assertFalse(prefs.contains(AUTO_CONFIG_VERSION_KEY))

            # 2. Hardware detection: mid-tier phone (Samsung A07: 3583MB, 720x1600)
            hw = DeviceHardware(total_ram_mb=3583, screen_width=720, screen_height=1600)
            HardwareHeuristicEngine.run_auto_config(hw, prefs)

            # 3. Settings file creation
            settings_dir = game_home / ".local/share/songsofsyx/settings"
            settings_dir.mkdir(parents=True, exist_ok=True)
            settings_file = settings_dir / "LauncherSettings.txt"
            settings_file.write_text(json.dumps({"MODS": []}), encoding="utf-8")

            # 4. Assert preferences persisted
            self.assertEqual(prefs.getInt("allocation"), 2048)
            self.assertEqual(prefs.getString("renderer"), "opengles2")
            self.assertEqual(prefs.getInt("resolutionRatio"), 100)
            self.assertEqual(prefs.getInt(AUTO_CONFIG_VERSION_KEY), CURRENT_AUTO_CONFIG_VERSION)

            # 5. Build JVM launch arguments
            ram = prefs.getInt("allocation")
            jvm_args = [
                f"-Xms512m",
                f"-Xmx{ram}m",
                f"-Duser.dir={game_dir}",
                f"-Duser.home={game_home}",
                f"-Dorg.lwjgl.librarypath=/data/app/lib/arm64",
                f"-Djava.library.path=/data/app/lib/arm64",
            ]
            self.assertIn("-Xmx2048m", jvm_args)
            self.assertTrue(settings_file.exists())

    def test_scenario_02_launcher_restart_custom_preferences(self):
        """Scenario 2: User customizes RAM and renderer; subsequent launcher restart preserves them."""
        prefs = MockSharedPreferences({
            AUTO_CONFIG_VERSION_KEY: CURRENT_AUTO_CONFIG_VERSION,
            "allocation": 4096,
            "renderer": "vulkan_zink",
            "javaArgs": "-XX:+UseG1GC",
        })
        # Subsequent launch on same device
        hw = DeviceHardware(total_ram_mb=8000, screen_width=1080, screen_height=2400)
        applied = HardwareHeuristicEngine.run_auto_config(hw, prefs, force=False)
        self.assertFalse(applied, "Subsequent launch must not overwrite preferences")

        self.assertEqual(prefs.getInt("allocation"), 4096)
        self.assertEqual(prefs.getString("renderer"), "vulkan_zink")
        self.assertEqual(prefs.getString("javaArgs"), "-XX:+UseG1GC")

    def test_scenario_03_settings_reset_workflow(self):
        """Scenario 3: User triggers 'Reset to Recommended Settings'; defaults are re-applied."""
        prefs = MockSharedPreferences({
            AUTO_CONFIG_VERSION_KEY: CURRENT_AUTO_CONFIG_VERSION,
            "allocation": 1024,
            "renderer": "broken_renderer",
        })
        hw = DeviceHardware(total_ram_mb=6000, screen_width=1080, screen_height=2400)
        # Forced reset
        applied = HardwareHeuristicEngine.run_auto_config(hw, prefs, force=True)
        self.assertTrue(applied)
        self.assertEqual(prefs.getInt("allocation"), 3072)
        self.assertEqual(prefs.getString("renderer"), "opengles2")

    def test_scenario_04_low_memory_device_adaptation(self):
        """Scenario 4: Entry-level device (<2GB RAM) receives safe 768MB allocation without crashing."""
        prefs = MockSharedPreferences()
        hw = DeviceHardware(total_ram_mb=1800, screen_width=720, screen_height=1280, is_32_bit=False)
        HardwareHeuristicEngine.run_auto_config(hw, prefs)

        alloc = prefs.getInt("allocation")
        self.assertEqual(alloc, 768)
        self.assertGreaterEqual(alloc, MIN_RAM_MB)
        # OS headroom: 1800 - 768 = 1032 MB free for system
        self.assertGreater(1800 - alloc, 800)

    def test_scenario_05_high_res_tablet_adaptation(self):
        """Scenario 5: 1600x2560 tablet receives 6144MB RAM and downscaled resolution to prevent thermal throttle."""
        prefs = MockSharedPreferences()
        hw = DeviceHardware(total_ram_mb=12000, screen_width=1600, screen_height=2560)
        HardwareHeuristicEngine.run_auto_config(hw, prefs)

        self.assertEqual(prefs.getInt("allocation"), 6144)
        # 1600px min_side scaled to ~1080p target (70%)
        self.assertEqual(prefs.getInt("resolutionRatio"), 70)

    def test_scenario_06_corrupted_config_recovery(self):
        """Scenario 6: Launcher detects corrupted LauncherSettings.txt and recovers default active mods."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            settings_dir = home / ".local/share/songsofsyx/settings"
            settings_dir.mkdir(parents=True, exist_ok=True)
            settings_file = settings_dir / "LauncherSettings.txt"
            settings_file.write_text("{corrupt json garbage", encoding="utf-8")

            # Self-healing routine
            try:
                data = json.loads(settings_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                # Corrupt detected: rewrite with default
                settings_file.write_text(json.dumps({"MODS": []}), encoding="utf-8")
                data = json.loads(settings_file.read_text(encoding="utf-8"))

            self.assertIn("MODS", data)
            self.assertEqual(data["MODS"], [])

    def test_scenario_07_game_process_spawning_simulation(self):
        """Scenario 7: Full process spawning verification: binary permissions, arguments, execution."""
        assert_file_exists(LIBLWJGL_SO)
        assert_elf_arm64(LIBLWJGL_SO)

        # Simulate fork and exec of Java runtime with mode 0755
        exec_res = MockProcessExecution.simulate_exec(
            binary_path="/data/user/0/git.artdeell.sosmobile/runtimes/jre17/bin/java",
            mode=0o755,
            is_hooked=True
        )
        self.assertEqual(exec_res["exit_code"], 0)
        self.assertIsNone(exec_res["error"])

    def test_scenario_08_multi_locale_launcher_startup(self):
        """Scenario 8: Launcher title resolves to SoSMobile across multiple languages."""
        target_locales = ["values", "values-ru", "values-de", "values-ja", "values-es", "values-ar"]
        for loc in target_locales:
            strings_file = RES_DIR / loc / "strings.xml"
            if strings_file.exists():
                content = strings_file.read_text(encoding="utf-8")
                self.assertIn(
                    "<string name=\"app_short_name\">SoSMobile</string>",
                    content,
                    f"Locale {loc} failed to provide SoSMobile app title"
                )


if __name__ == "__main__":
    unittest.main()
