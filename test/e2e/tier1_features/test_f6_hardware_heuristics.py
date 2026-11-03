"""Tier 1: Feature Baseline Coverage - F6: SoS Hardware Heuristics

Verifies the 7-tier RAM scaling algorithm, resolution downscaling to prevent QHD+ thermal
throttling, seekbar step alignment, and opengles2 renderer default.
"""

import unittest

from ..common.env import (
    SEEKBAR_RAM_INCREMENT,
    SEEKBAR_RESOLUTION_INCREMENT,
    MIN_RAM_MB,
)
from ..common.simulators import (
    DeviceHardware,
    HardwareHeuristicEngine,
)


class TestF6HardwareHeuristics(unittest.TestCase):
    """Test suite verifying F6 hardware heuristic mapping calculations."""

    def test_f6_01_seven_tier_ram_allocation_benchmarks(self):
        """Assert RAM calculation matches the 7 tiers specified in PROJECT.md."""
        test_cases = [
            # (total_ram_mb, is_32_bit, expected_ram)
            (1500, False, 768),   # Tier 1 (< 2048 MB)
            (3000, False, 1536),  # Tier 2 (2048 - 3500 MB)
            (3583, False, 2048),  # Tier 3 (3501 - 5000 MB, e.g. Samsung SM-A075F in latestlog.txt)
            (6000, False, 3072),  # Tier 4 (5001 - 7000 MB)
            (8000, False, 4608),  # Tier 5 (7001 - 9500 MB)
            (12000, False, 6144), # Tier 6 (9501 - 13000 MB)
            (16000, False, 8192), # Tier 7 (> 13000 MB)
        ]
        for ram_mb, is_32bit, expected in test_cases:
            with self.subTest(ram_mb=ram_mb, is_32bit=is_32bit):
                actual = HardwareHeuristicEngine.compute_optimal_ram(ram_mb, is_32bit)
                self.assertEqual(actual, expected)

    def test_f6_02_ram_seekbar_increment_alignment(self):
        """Assert all calculated RAM values are exact multiples of SEEKBAR_RAM_INCREMENT (8MB)."""
        test_rams = [1024, 2048, 3583, 4096, 6144, 7680, 8192, 11500, 15800]
        for ram in test_rams:
            alloc = HardwareHeuristicEngine.compute_optimal_ram(ram, is_32_bit=False)
            self.assertEqual(
                alloc % SEEKBAR_RAM_INCREMENT, 0,
                f"RAM allocation {alloc} for {ram}MB must be multiple of {SEEKBAR_RAM_INCREMENT}"
            )
            self.assertGreaterEqual(alloc, MIN_RAM_MB)

    def test_f6_03_display_resolution_heuristics(self):
        """Assert resolution ratio scales appropriately for HD+, FHD+, and QHD+ displays."""
        # HD+ (<= 720px): must not downscale below 100% to keep fonts readable
        ratio_hd = HardwareHeuristicEngine.compute_optimal_resolution_ratio(min_side=720, total_ram_mb=3583)
        self.assertEqual(ratio_hd, 100)

        # FHD+ (1080px): 85% for mid-low device, 100% for high-tier device
        ratio_fhd_mid = HardwareHeuristicEngine.compute_optimal_resolution_ratio(
            min_side=1080, total_ram_mb=3583, is_adreno=False
        )
        self.assertEqual(ratio_fhd_mid, 85)

        ratio_fhd_high = HardwareHeuristicEngine.compute_optimal_resolution_ratio(
            min_side=1080, total_ram_mb=8000, is_adreno=True
        )
        self.assertEqual(ratio_fhd_high, 100)

        # QHD+ (1440px): downscale to ~1080p target (75%)
        ratio_qhd = HardwareHeuristicEngine.compute_optimal_resolution_ratio(min_side=1440, total_ram_mb=8000)
        self.assertEqual(ratio_qhd, 75)

    def test_f6_04_resolution_seekbar_increment_alignment(self):
        """Assert all calculated resolution ratios are multiples of 5% and clamped to [25, 100]."""
        for min_side in [480, 720, 900, 1080, 1200, 1440, 1600, 2160]:
            ratio = HardwareHeuristicEngine.compute_optimal_resolution_ratio(min_side, total_ram_mb=4096)
            self.assertEqual(ratio % SEEKBAR_RESOLUTION_INCREMENT, 0)
            self.assertGreaterEqual(ratio, 25)
            self.assertLessEqual(ratio, 100)

    def test_f6_05_default_renderer_selection(self):
        """Assert the heuristic selects stable 'opengles2' (GL4ES) by default."""
        from ..common.simulators import MockSharedPreferences
        prefs = MockSharedPreferences()
        hw = DeviceHardware(total_ram_mb=3583, screen_width=720, screen_height=1600)
        HardwareHeuristicEngine.run_auto_config(hw, prefs)
        self.assertEqual(prefs.getString("renderer"), "opengles2")


if __name__ == "__main__":
    unittest.main()
