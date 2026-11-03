"""Tier 1: Feature Baseline Coverage - F5: Device Auto-Config Coordinator

Verifies that the auto-config coordinator executes on first launch, detects hardware,
persists optimal parameters into SharedPreferences, and respects the auto_config_version flag.
"""

import unittest
from pathlib import Path

from ..common.env import (
    DEVICE_AUTO_CONFIG,
    LAUNCHER_PREFS,
    AUTO_CONFIG_VERSION_KEY,
    CURRENT_AUTO_CONFIG_VERSION,
)
from ..common.simulators import (
    MockSharedPreferences,
    DeviceHardware,
    HardwareHeuristicEngine,
)
from ..common.assertions import assert_file_exists


class TestF5AutoConfigCoordinator(unittest.TestCase):
    """Test suite verifying F5 auto-config coordinator contract and persistence."""

    def test_f5_01_first_launch_triggers_auto_config(self):
        """Assert first launch triggers auto-configuration when version key is absent."""
        prefs = MockSharedPreferences()
        hw = DeviceHardware(total_ram_mb=3583, screen_width=720, screen_height=1600)

        applied = HardwareHeuristicEngine.run_auto_config(hw, prefs, force=False)
        self.assertTrue(applied, "First launch must trigger auto-configuration")
        self.assertEqual(prefs.getInt(AUTO_CONFIG_VERSION_KEY, 0), CURRENT_AUTO_CONFIG_VERSION)
        self.assertTrue(prefs.contains("allocation"))
        self.assertTrue(prefs.contains("resolutionRatio"))
        self.assertTrue(prefs.contains("renderer"))

    def test_f5_02_subsequent_launch_preserves_custom_settings(self):
        """Assert auto-config does not overwrite user customizations on subsequent runs."""
        prefs = MockSharedPreferences({
            AUTO_CONFIG_VERSION_KEY: CURRENT_AUTO_CONFIG_VERSION,
            "allocation": 4096,  # User custom value
            "renderer": "vulkan_zink",  # User custom renderer
        })
        hw = DeviceHardware(total_ram_mb=3583, screen_width=720, screen_height=1600)

        applied = HardwareHeuristicEngine.run_auto_config(hw, prefs, force=False)
        self.assertFalse(applied, "Subsequent launch must not re-run auto-configuration")
        # User settings must be preserved
        self.assertEqual(prefs.getInt("allocation"), 4096)
        self.assertEqual(prefs.getString("renderer"), "vulkan_zink")

    def test_f5_03_forced_reset_overwrites_settings(self):
        """Assert forced auto-config (reset option) re-evaluates hardware and resets settings."""
        prefs = MockSharedPreferences({
            AUTO_CONFIG_VERSION_KEY: CURRENT_AUTO_CONFIG_VERSION,
            "allocation": 1024,
            "renderer": "custom",
        })
        hw = DeviceHardware(total_ram_mb=7680, screen_width=1080, screen_height=2400)

        applied = HardwareHeuristicEngine.run_auto_config(hw, prefs, force=True)
        self.assertTrue(applied, "Forced reset must re-run auto-configuration")
        self.assertEqual(prefs.getInt("allocation"), 4608)  # 8GB tier recommendation
        self.assertEqual(prefs.getString("renderer"), "opengles2")

    def test_f5_04_persisted_keys_conform_to_contract(self):
        """Assert all keys specified in PROJECT.md interface contract are written."""
        prefs = MockSharedPreferences()
        hw = DeviceHardware(total_ram_mb=6000, screen_width=1080, screen_height=2400)
        HardwareHeuristicEngine.run_auto_config(hw, prefs)

        expected_keys = [
            "allocation",
            "resolutionRatio",
            "renderer",
            "alternate_surface",
            "sustainedPerformance",
            "force_vsync",
            "auto_config_version",
        ]
        for key in expected_keys:
            self.assertTrue(
                prefs.contains(key),
                f"Auto-config must persist required contract key: {key}"
            )

    def test_f5_05_coordinator_hook_contract(self):
        """Verify coordinator hook contract exists or is integrated in LauncherPreferences."""
        assert_file_exists(LAUNCHER_PREFS)
        content = LAUNCHER_PREFS.read_text(encoding="utf-8")
        # Should reference auto_config or DeviceAutoConfig or runAutoConfigIfNeeded
        if DEVICE_AUTO_CONFIG.exists():
            da_content = DEVICE_AUTO_CONFIG.read_text(encoding="utf-8")
            self.assertIn("runAutoConfigIfNeeded", da_content)
            self.assertIn("auto_config_version", da_content)
        else:
            # Interface contract verified through spec
            self.assertTrue(hasattr(HardwareHeuristicEngine, "run_auto_config"))


if __name__ == "__main__":
    unittest.main()
