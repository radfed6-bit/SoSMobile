"""Tier 2: Boundary Value Analysis - F5: Device Auto-Config Coordinator Boundaries

Verifies boundary conditions for version flags, partial preferences,
consecutive executions, and storage state handling.
"""

import unittest

from ..common.env import (
    AUTO_CONFIG_VERSION_KEY,
    CURRENT_AUTO_CONFIG_VERSION,
)
from ..common.simulators import (
    MockSharedPreferences,
    DeviceHardware,
    HardwareHeuristicEngine,
)


class TestF5BVA(unittest.TestCase):
    """BVA test suite for F5 auto-config coordinator execution boundaries."""

    def test_f5_bva_01_future_version_flag_boundary(self):
        """Assert auto-config is skipped if auto_config_version is higher than current."""
        prefs = MockSharedPreferences({
            AUTO_CONFIG_VERSION_KEY: 999,
            "allocation": 5555,
        })
        hw = DeviceHardware(total_ram_mb=4000, screen_width=1080, screen_height=2400)
        applied = HardwareHeuristicEngine.run_auto_config(hw, prefs, force=False)
        self.assertFalse(applied)
        self.assertEqual(prefs.getInt("allocation"), 5555)

    def test_f5_bva_02_negative_version_flag_boundary(self):
        """Assert auto-config executes when auto_config_version is negative."""
        prefs = MockSharedPreferences({
            AUTO_CONFIG_VERSION_KEY: -1,
        })
        hw = DeviceHardware(total_ram_mb=4000, screen_width=1080, screen_height=2400)
        applied = HardwareHeuristicEngine.run_auto_config(hw, prefs, force=False)
        self.assertTrue(applied)
        self.assertEqual(prefs.getInt(AUTO_CONFIG_VERSION_KEY), CURRENT_AUTO_CONFIG_VERSION)

    def test_f5_bva_03_partial_preferences_without_version(self):
        """Assert auto-config executes if user has some keys but no version key."""
        prefs = MockSharedPreferences({
            "buttonscale": 80,
        })
        hw = DeviceHardware(total_ram_mb=6000, screen_width=1080, screen_height=2400)
        applied = HardwareHeuristicEngine.run_auto_config(hw, prefs, force=False)
        self.assertTrue(applied)
        self.assertEqual(prefs.getInt("buttonscale"), 80)
        self.assertTrue(prefs.contains("allocation"))

    def test_f5_bva_04_consecutive_idempotent_runs(self):
        """Assert consecutive non-forced runs return False and preserve state."""
        prefs = MockSharedPreferences()
        hw = DeviceHardware(total_ram_mb=8000, screen_width=1080, screen_height=2400)

        run1 = HardwareHeuristicEngine.run_auto_config(hw, prefs, force=False)
        self.assertTrue(run1)

        run2 = HardwareHeuristicEngine.run_auto_config(hw, prefs, force=False)
        self.assertFalse(run2)

        run3 = HardwareHeuristicEngine.run_auto_config(hw, prefs, force=False)
        self.assertFalse(run3)

    def test_f5_bva_05_editor_commit_contract(self):
        """Verify MockSharedPreferences editor commit correctly applies staged changes."""
        prefs = MockSharedPreferences()
        editor = prefs.edit()
        editor.putInt("test_int", 42)
        editor.putString("test_str", "hello")
        editor.putBoolean("test_bool", True)
        self.assertFalse(prefs.contains("test_int"))
        editor.commit()
        self.assertEqual(prefs.getInt("test_int"), 42)
        self.assertEqual(prefs.getString("test_str"), "hello")
        self.assertTrue(prefs.getBoolean("test_bool"))


if __name__ == "__main__":
    unittest.main()
