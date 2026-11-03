"""Tier 5: Adversarial Stress Testing - DeviceAutoConfig Concurrency, Idempotency & State Integrity.

Stress-tests DeviceAutoConfig coordinator against:
- High-concurrency multithreaded races (50 concurrent threads)
- High-frequency consecutive idempotency cycles (200 cycles)
- Preservation of user-customized preferences across auto-config invocations
- Reset to recommended state lifecycle
- Corrupt/non-standard auto_config_version values
"""

import concurrent.futures
import threading
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


class ThreadSafeMockSharedPreferences(MockSharedPreferences):
    """Thread-safe variant of MockSharedPreferences to verify concurrent editor transactions."""
    def __init__(self, initial=None):
        super().__init__(initial)
        self._lock = threading.Lock()

    def getInt(self, key: str, default: int = 0) -> int:
        with self._lock:
            return super().getInt(key, default)

    def getString(self, key: str, default=None):
        with self._lock:
            return super().getString(key, default)

    def getBoolean(self, key: str, default: bool = False) -> bool:
        with self._lock:
            return super().getBoolean(key, default)

    def contains(self, key: str) -> bool:
        with self._lock:
            return super().contains(key)

    def edit(self):
        return ThreadSafeEditor(self)


class ThreadSafeEditor:
    def __init__(self, prefs: ThreadSafeMockSharedPreferences):
        self.prefs = prefs
        self.staged = {}

    def putInt(self, key: str, value: int):
        self.staged[key] = int(value)
        return self

    def putString(self, key: str, value: str):
        self.staged[key] = str(value)
        return self

    def putBoolean(self, key: str, value: bool):
        self.staged[key] = bool(value)
        return self

    def apply(self):
        with self.prefs._lock:
            self.prefs._storage.update(self.staged)
        self.staged.clear()

    def commit(self) -> bool:
        self.apply()
        return True


class TestAdversarialAutoConfigConcurrency(unittest.TestCase):
    """Stress testing suite for concurrency, idempotency, and state corruption."""

    def test_adv_01_multithreaded_concurrent_auto_config(self):
        """50 concurrent worker threads race to execute auto-config on shared preferences."""
        prefs = ThreadSafeMockSharedPreferences()
        hw = DeviceHardware(total_ram_mb=8000, screen_width=1080, screen_height=2400)

        num_threads = 50
        barrier = threading.Barrier(num_threads)
        results = []

        def worker():
            barrier.wait()  # synchronize all threads to start simultaneously
            applied = HardwareHeuristicEngine.run_auto_config(hw, prefs, force=False)
            results.append(applied)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # At least one thread must have applied the configuration
        self.assertTrue(any(results), "At least one thread must successfully apply auto-config")
        # Final preferences state must be fully populated and valid
        self.assertEqual(prefs.getInt(AUTO_CONFIG_VERSION_KEY), CURRENT_AUTO_CONFIG_VERSION)
        self.assertEqual(prefs.getInt("allocation"), 4608)
        self.assertEqual(prefs.getString("renderer"), "opengles2")
        self.assertTrue(prefs.getBoolean("force_vsync"))

    def test_adv_02_idempotency_over_200_consecutive_runs(self):
        """200 consecutive auto-config runs without force do not alter preferences state."""
        prefs = MockSharedPreferences()
        hw = DeviceHardware(total_ram_mb=6000, screen_width=1080, screen_height=2400)

        first_run = HardwareHeuristicEngine.run_auto_config(hw, prefs, force=False)
        self.assertTrue(first_run)
        snapshot = dict(prefs.getAll())

        for i in range(200):
            applied = HardwareHeuristicEngine.run_auto_config(hw, prefs, force=False)
            self.assertFalse(applied, f"Run {i+1} altered state unexpectedly")
            self.assertEqual(prefs.getAll(), snapshot, f"Snapshot diverged at run {i+1}")

    def test_adv_03_user_customizations_strictly_preserved(self):
        """User-customized preferences remain completely untouched across repeated launches."""
        prefs = MockSharedPreferences()
        hw = DeviceHardware(total_ram_mb=8000, screen_width=1080, screen_height=2400)

        # 1. Initial first-launch auto-config
        HardwareHeuristicEngine.run_auto_config(hw, prefs, force=False)
        self.assertEqual(prefs.getInt("allocation"), 4608)

        # 2. User manually customizes settings in UI
        prefs.edit() \
            .putInt("allocation", 3072) \
            .putString("renderer", "vulkan") \
            .putInt("resolutionRatio", 50) \
            .putBoolean("force_vsync", False) \
            .apply()

        # 3. App restarts multiple times
        for _ in range(50):
            applied = HardwareHeuristicEngine.run_auto_config(hw, prefs, force=False)
            self.assertFalse(applied)
            self.assertEqual(prefs.getInt("allocation"), 3072)
            self.assertEqual(prefs.getString("renderer"), "vulkan")
            self.assertEqual(prefs.getInt("resolutionRatio"), 50)
            self.assertFalse(prefs.getBoolean("force_vsync"))

    def test_adv_04_forced_reset_lifecycle(self):
        """Reset to Recommended Settings overrides custom values and re-establishes idempotency."""
        prefs = MockSharedPreferences()
        hw = DeviceHardware(total_ram_mb=8000, screen_width=1080, screen_height=2400)

        HardwareHeuristicEngine.run_auto_config(hw, prefs, force=False)

        # Custom values
        prefs.edit() \
            .putInt("allocation", 1024) \
            .putString("renderer", "software") \
            .apply()

        # Force reset
        reset_applied = HardwareHeuristicEngine.run_auto_config(hw, prefs, force=True)
        self.assertTrue(reset_applied)
        self.assertEqual(prefs.getInt("allocation"), 4608)
        self.assertEqual(prefs.getString("renderer"), "opengles2")

        # Subsequent regular launch does not re-apply
        subsequent = HardwareHeuristicEngine.run_auto_config(hw, prefs, force=False)
        self.assertFalse(subsequent)

    def test_adv_05_corrupt_version_values_graceful_handling(self):
        """Non-standard or corrupted version values (negative, 0, None) handle gracefully."""
        cases = [
            (-999, True),   # Negative version -> triggers auto-config
            (0, True),      # Version 0 -> triggers auto-config
            (1, False),     # Version 1 -> already configured
            (2, False),     # Version 2 (future) -> already configured
        ]
        hw = DeviceHardware(total_ram_mb=4000, screen_width=1080, screen_height=2400)
        for ver, expected_applied in cases:
            with self.subTest(version=ver):
                prefs = MockSharedPreferences({AUTO_CONFIG_VERSION_KEY: ver})
                applied = HardwareHeuristicEngine.run_auto_config(hw, prefs, force=False)
                self.assertEqual(
                    applied, expected_applied,
                    f"Version {ver}: expected applied={expected_applied}, got {applied}"
                )


if __name__ == "__main__":
    unittest.main()
