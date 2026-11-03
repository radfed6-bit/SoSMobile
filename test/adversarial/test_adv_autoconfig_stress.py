"""Tier 5 Adversarial Test: DeviceAutoConfig Concurrency, Idempotency & Boundaries

Stress-tests DeviceAutoConfig across multi-threaded execution, process restart lifecycles,
extreme RAM profiles (negative, 0MB, 1TB), and non-standard display geometries.
"""

import concurrent.futures
import threading
import unittest
from pathlib import Path
from typing import Dict, Any

from test.e2e.common.env import (
    AUTO_CONFIG_VERSION_KEY,
    CURRENT_AUTO_CONFIG_VERSION,
    MIN_RAM_MB,
    SEEKBAR_RAM_INCREMENT,
    SEEKBAR_RESOLUTION_INCREMENT,
)
from test.e2e.common.simulators import (
    DeviceHardware,
    HardwareHeuristicEngine,
    MockSharedPreferences,
)

PROJECT_ROOT = Path("/workspaces/SoSMobile").resolve()
DEVICE_AUTO_CONFIG_JAVA = PROJECT_ROOT / "app_mojo/src/main/java/git/artdeell/mojo/prefs/DeviceAutoConfig.java"
LAUNCHER_PREFS_JAVA = PROJECT_ROOT / "app_mojo/src/main/java/git/artdeell/mojo/prefs/LauncherPreferences.java"


class ThreadSafeMockPrefs(MockSharedPreferences):
    """Thread-safe SharedPreferences simulator to detect concurrency races."""

    def __init__(self, initial=None):
        super().__init__(initial)
        self._lock = threading.Lock()
        self.apply_counter = 0

    def edit(self):
        class LockedEditor:
            def __init__(self, outer):
                self.outer = outer
                self.staged = {}

            def putInt(self, k, v):
                self.staged[k] = int(v)
                return self

            def putString(self, k, v):
                self.staged[k] = str(v)
                return self

            def putBoolean(self, k, v):
                self.staged[k] = bool(v)
                return self

            def apply(self):
                with self.outer._lock:
                    self.outer._storage.update(self.staged)
                    self.outer.apply_counter += 1

        return LockedEditor(self)

    def getInt(self, key: str, default: int = 0) -> int:
        with self._lock:
            return super().getInt(key, default)


class TestAdvAutoConfigStress(unittest.TestCase):
    """Stress testing suite for DeviceAutoConfig idempotency, concurrency, and hardware limits."""

    def test_source_integration_contracts(self):
        """Verify DeviceAutoConfig integration into LauncherPreferences."""
        self.assertTrue(DEVICE_AUTO_CONFIG_JAVA.exists())
        self.assertTrue(LAUNCHER_PREFS_JAVA.exists())

        dac_src = DEVICE_AUTO_CONFIG_JAVA.read_text(encoding="utf-8")
        lp_src = LAUNCHER_PREFS_JAVA.read_text(encoding="utf-8")

        # Check version constant
        self.assertIn("PREF_KEY_AUTO_CONFIG_VERSION = \"auto_config_version\"", dac_src)
        self.assertIn("CURRENT_AUTO_CONFIG_VERSION = 1", dac_src)

        # Check hook inside LauncherPreferences.loadPreferences
        self.assertIn("DeviceAutoConfig.runAutoConfigIfNeeded(ctx)", lp_src,
                      "LauncherPreferences.loadPreferences must invoke DeviceAutoConfig.runAutoConfigIfNeeded")

        # Check findBestRAMAllocation delegates to DeviceAutoConfig
        self.assertIn("DeviceAutoConfig.computeOptimalRam", lp_src,
                      "LauncherPreferences.findBestRAMAllocation must delegate to DeviceAutoConfig")

    def test_multi_threaded_concurrency_stress(self):
        """Stress-test 50 concurrent threads executing auto-config simultaneously."""
        prefs = ThreadSafeMockPrefs()
        hw = DeviceHardware(total_ram_mb=3583, screen_width=1080, screen_height=2400)

        def worker_task(thread_id: int):
            # Simulate runAutoConfigIfNeeded under concurrency
            if prefs.getInt(AUTO_CONFIG_VERSION_KEY, 0) < CURRENT_AUTO_CONFIG_VERSION:
                # Execute auto config
                HardwareHeuristicEngine.run_auto_config(hw, prefs, force=False)
            return prefs.getInt("allocation", 0)

        num_threads = 50
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_task, i) for i in range(num_threads)]
            results = [f.result() for f in futures]

        # Verify all threads read consistent allocation
        self.assertEqual(len(results), num_threads)
        for val in results:
            self.assertEqual(val, 2048, "Every thread must see the identical tuned RAM allocation (2048MB)")

        # Verify final state in prefs
        self.assertEqual(prefs.getInt(AUTO_CONFIG_VERSION_KEY, 0), 1)
        self.assertEqual(prefs.getInt("allocation", 0), 2048)
        self.assertEqual(prefs.getString("renderer", ""), "opengles2")

    def test_process_restart_lifecycle_and_customization_retention(self):
        """Simulate 10 consecutive app launches with user customizations in between."""
        prefs = MockSharedPreferences()
        hw = DeviceHardware(total_ram_mb=8192, screen_width=1440, screen_height=3200)

        # Launch 1: First launch
        run1 = HardwareHeuristicEngine.run_auto_config(hw, prefs, force=False)
        self.assertTrue(run1, "First launch must execute auto-configuration")
        self.assertEqual(prefs.getInt("allocation", 0), 4608)  # Tier 5 (7001-9500MB): 4608MB
        self.assertEqual(prefs.getInt("resolutionRatio", 0), 75)  # QHD scaled down
        self.assertEqual(prefs.getInt(AUTO_CONFIG_VERSION_KEY, 0), 1)

        # User customizes settings in UI
        prefs.edit() \
            .putInt("allocation", 3072) \
            .putInt("resolutionRatio", 60) \
            .putString("renderer", "vulkan") \
            .apply()

        # Launches 2 through 10: Repeated restarts
        for launch in range(2, 11):
            ran = HardwareHeuristicEngine.run_auto_config(hw, prefs, force=False)
            self.assertFalse(ran, f"Launch {launch} must NOT re-run auto configuration")
            self.assertEqual(prefs.getInt("allocation", 0), 3072,
                             f"Launch {launch} must preserve user-customized RAM")
            self.assertEqual(prefs.getInt("resolutionRatio", 0), 60,
                             f"Launch {launch} must preserve user-customized resolution")
            self.assertEqual(prefs.getString("renderer", ""), "vulkan",
                             f"Launch {launch} must preserve user-customized renderer")

        # User presses "Reset to Recommended Settings"
        reset_ran = HardwareHeuristicEngine.run_auto_config(hw, prefs, force=True)
        self.assertTrue(reset_ran, "Forced reset must re-run auto-configuration")
        self.assertEqual(prefs.getInt("allocation", 0), 4608, "Reset must restore optimal RAM")
        self.assertEqual(prefs.getInt("resolutionRatio", 0), 75, "Reset must restore optimal resolution")
        self.assertEqual(prefs.getString("renderer", ""), "opengles2", "Reset must restore default opengles2")

    def test_extreme_ram_boundary_stress(self):
        """Test extreme, negative, and astronomical RAM values across 32 and 64-bit."""
        test_cases_64bit = [
            (-1000, 512),
            (0, 512),
            (256, 512),
            (512, 512),
            (1024, 768),
            (2048, 768),
            (2049, 1536),
            (3500, 1536),
            (3583, 2048),  # latestlog.txt exact device RAM
            (4096, 2048),
            (6000, 3072),
            (8000, 4608),
            (12000, 6144),
            (16000, 8192),
            (32000, 8192),
            (1048576, 8192),  # 1 TB RAM
        ]

        for ram_input, expected_ram in test_cases_64bit:
            val = HardwareHeuristicEngine.compute_optimal_ram(ram_input, is_32_bit=False)
            self.assertEqual(val, expected_ram, f"Failed for 64-bit RAM={ram_input}")
            self.assertGreaterEqual(val, MIN_RAM_MB, "RAM allocation must never fall below 512MB")
            self.assertEqual(val % SEEKBAR_RAM_INCREMENT, 0, "RAM allocation must align to 8MB seekbar step")

        # 32-bit tests: must be capped at 800 MB and >= 512 MB
        test_cases_32bit = [-500, 0, 512, 1024, 2048, 4096, 8192]
        for ram_input in test_cases_32bit:
            val = HardwareHeuristicEngine.compute_optimal_ram(ram_input, is_32_bit=True)
            self.assertGreaterEqual(val, MIN_RAM_MB, "32-bit RAM allocation must be >= 512MB")
            self.assertLessEqual(val, 800, "32-bit RAM allocation must not exceed 800MB")
            self.assertEqual(val % SEEKBAR_RAM_INCREMENT, 0, "32-bit RAM must align to 8MB step")

    def test_extreme_screen_resolution_boundary_stress(self):
        """Test bizarre and extreme screen dimensions (0x0, 8K, odd aspect ratios)."""
        test_cases = [
            # (min_side, total_ram, is_adreno, expected_ratio)
            (0, 4096, True, 100),       # Fallback minSide
            (480, 2048, False, 100),    # Low res
            (720, 3000, True, 100),     # 720p HD
            (1080, 3583, False, 85),    # 1080p non-adreno / <=4GB
            (1080, 8192, True, 100),    # 1080p adreno high RAM
            (1440, 6000, True, 75),     # 1440p QHD
            (1600, 8000, False, 70),    # 1600p Tablet
            (2160, 12000, True, 50),    # 4K UHD
            (4320, 16000, True, 25),    # 8K (clamped to min 25)
            (10000, 32000, True, 25),   # Extreme dimension clamped to 25
        ]

        for min_side, ram, is_adreno, expected_ratio in test_cases:
            effective_min = min_side if min_side > 0 else 720
            ratio = HardwareHeuristicEngine.compute_optimal_resolution_ratio(effective_min, ram, is_adreno)
            self.assertEqual(ratio, expected_ratio,
                             f"Failed for min_side={min_side}, ram={ram}, is_adreno={is_adreno}")
            self.assertGreaterEqual(ratio, 25, "Ratio must be >= 25%")
            self.assertLessEqual(ratio, 100, "Ratio must be <= 100%")
            self.assertEqual(ratio % SEEKBAR_RESOLUTION_INCREMENT, 0,
                             "Ratio must align to 5% seekbar increment")


if __name__ == "__main__":
    unittest.main()
