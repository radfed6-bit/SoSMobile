"""Tier 2: Boundary Value Analysis - F6: SoS Hardware Heuristics Boundaries

Verifies extreme RAM inputs, under-allocation clamping, extreme screen aspect ratios,
and 32-bit device constraints.
"""

import unittest

from ..common.env import (
    MIN_RAM_MB,
    SEEKBAR_RAM_INCREMENT,
    SEEKBAR_RESOLUTION_INCREMENT,
)
from ..common.simulators import (
    HardwareHeuristicEngine,
)


class TestF6BVA(unittest.TestCase):
    """BVA test suite for F6 hardware heuristics extreme values."""

    def test_f6_bva_01_under_minimum_ram_clamping(self):
        """Assert device RAM below 512 MB (e.g. 256 MB or 400 MB) is clamped to MIN_RAM_MB (512 MB)."""
        alloc = HardwareHeuristicEngine.compute_optimal_ram(total_ram_mb=300, is_32_bit=False)
        self.assertEqual(alloc, MIN_RAM_MB)

    def test_f6_bva_02_extreme_high_ram_cap(self):
        """Assert extreme high RAM devices (e.g. 32GB or 64GB) cap at 8192 MB."""
        alloc_32gb = HardwareHeuristicEngine.compute_optimal_ram(total_ram_mb=32768, is_32_bit=False)
        self.assertEqual(alloc_32gb, 8192)

        alloc_64gb = HardwareHeuristicEngine.compute_optimal_ram(total_ram_mb=65536, is_32_bit=False)
        self.assertEqual(alloc_64gb, 8192)

    def test_f6_bva_03_32bit_device_hard_cap(self):
        """Assert 32-bit devices cap allocation at 800 MB even with 4GB+ physical RAM."""
        alloc = HardwareHeuristicEngine.compute_optimal_ram(total_ram_mb=4096, is_32_bit=True)
        self.assertLessEqual(alloc, 800)
        self.assertGreaterEqual(alloc, MIN_RAM_MB)

    def test_f6_bva_04_extreme_aspect_ratio_min_side_derivation(self):
        """Assert unusual aspect ratio (foldable/tall screen e.g. 1080x3200) derives minSide accurately."""
        ratio = HardwareHeuristicEngine.compute_optimal_resolution_ratio(min_side=1080, total_ram_mb=4000)
        self.assertEqual(ratio, 85)

    def test_f6_bva_05_ultra_low_resolution_clamping(self):
        """Assert low-resolution screen (480px) remains clamped between 25% and 100%."""
        ratio = HardwareHeuristicEngine.compute_optimal_resolution_ratio(min_side=480, total_ram_mb=2000)
        self.assertEqual(ratio, 100)
        self.assertTrue(25 <= ratio <= 100)


if __name__ == "__main__":
    unittest.main()
