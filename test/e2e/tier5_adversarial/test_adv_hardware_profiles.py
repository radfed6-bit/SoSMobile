"""Tier 5: Adversarial Stress Testing - Extreme Hardware Profiles & Boundaries.

Stress-tests hardware heuristics with extreme RAM values (0MB, negative, 128GB, 1TB),
unusual screen resolutions (8K, 4K, 1x1, 0x0, ultra-wide, foldable), 32-bit clamping,
and compatibility with JVM launch arguments.
"""

import unittest
from ..common.env import (
    MIN_RAM_MB,
    SEEKBAR_RAM_INCREMENT,
    SEEKBAR_RESOLUTION_INCREMENT,
)
from ..common.simulators import (
    HardwareHeuristicEngine,
    DeviceHardware,
)

MAX_REASONABLE_RAM_MB = 16384



class TestAdversarialHardwareProfiles(unittest.TestCase):
    """Adversarial stress tests for hardware heuristics and boundary integrity."""

    def test_adv_01_ram_zero_and_negative_inputs(self):
        """Stress-test RAM allocation with zero and negative RAM values."""
        extreme_negatives = [0, -1, -100, -512, -4096, -2147483648]
        for ram in extreme_negatives:
            with self.subTest(ram=ram):
                # 64-bit device
                alloc_64 = HardwareHeuristicEngine.compute_optimal_ram(ram, is_32_bit=False)
                self.assertGreaterEqual(
                    alloc_64, MIN_RAM_MB,
                    f"Allocated RAM {alloc_64} for negative input {ram} is below MIN_RAM_MB"
                )
                self.assertEqual(
                    alloc_64 % SEEKBAR_RAM_INCREMENT, 0,
                    f"Allocated RAM {alloc_64} is not aligned to {SEEKBAR_RAM_INCREMENT} MB"
                )

                # 32-bit device
                alloc_32 = HardwareHeuristicEngine.compute_optimal_ram(ram, is_32_bit=True)
                self.assertGreaterEqual(alloc_32, MIN_RAM_MB)
                self.assertLessEqual(alloc_32, 800)
                self.assertEqual(alloc_32 % SEEKBAR_RAM_INCREMENT, 0)

    def test_adv_02_ram_extreme_large_inputs(self):
        """Stress-test RAM allocation with massive device memory (up to 1TB and INT_MAX)."""
        huge_rams = [
            16384,      # 16 GB
            32768,      # 32 GB
            65536,      # 64 GB
            131072,     # 128 GB
            1048576,    # 1 TB
            2147483647  # Integer.MAX_VALUE
        ]
        for ram in huge_rams:
            with self.subTest(ram=ram):
                alloc = HardwareHeuristicEngine.compute_optimal_ram(ram, is_32_bit=False)
                self.assertEqual(
                    alloc, 8192,
                    f"Expected 8192 MB cap for extreme RAM {ram}MB, got {alloc}MB"
                )
                self.assertLessEqual(alloc, MAX_REASONABLE_RAM_MB)
                self.assertEqual(alloc % SEEKBAR_RAM_INCREMENT, 0)

    def test_adv_03_32bit_hard_envelope_across_all_inputs(self):
        """Verify 32-bit devices strictly stay within [512, 800] MB for all inputs."""
        test_inputs = [
            -4096, -512, 0, 256, 512, 768, 1024, 2048, 4096, 8192,
            16384, 131072, 2147483647
        ]
        for ram in test_inputs:
            with self.subTest(ram=ram):
                alloc = HardwareHeuristicEngine.compute_optimal_ram(ram, is_32_bit=True)
                self.assertGreaterEqual(
                    alloc, MIN_RAM_MB,
                    f"32-bit RAM {alloc} below MIN_RAM_MB for input {ram}"
                )
                self.assertLessEqual(
                    alloc, 800,
                    f"32-bit RAM {alloc} exceeds 800 MB ceiling for input {ram}"
                )
                self.assertEqual(alloc % SEEKBAR_RAM_INCREMENT, 0)

    def test_adv_04_ram_tier_monotonicity_and_step_boundaries(self):
        """Verify monotonic non-decreasing allocation and exact tier thresholds."""
        thresholds = [
            (1023, 512), (1024, 768),
            (2048, 768), (2049, 1536),
            (3500, 1536), (3501, 2048),
            (5000, 2048), (5001, 3072),
            (7000, 3072), (7001, 4608),
            (9500, 4608), (9501, 6144),
            (13000, 6144), (13001, 8192)
        ]
        prev_alloc = 0
        for ram, expected in thresholds:
            alloc = HardwareHeuristicEngine.compute_optimal_ram(ram, is_32_bit=False)
            self.assertEqual(
                alloc, expected,
                f"RAM {ram}MB: expected {expected}MB, got {alloc}MB"
            )
            self.assertGreaterEqual(
                alloc, prev_alloc,
                f"Allocation decreased from {prev_alloc} to {alloc} at {ram}MB"
            )
            prev_alloc = alloc

    def test_adv_05_resolution_extreme_displays_and_bounds(self):
        """Stress-test resolution scaling for 8K, 4K, 1440p, foldable, smartwatch, 0x0."""
        cases = [
            # (min_side, ram_mb, is_adreno, expected_ratio, description)
            (4320, 8192, True, 25, "8K UHD display (7680x4320) -> downscaled to 25%"),
            (2160, 6144, True, 50, "4K UHD display (3840x2160) -> downscaled to 50%"),
            (1440, 8192, True, 75, "QHD/1440p display (2560x1440) -> downscaled to 75%"),
            (1440, 8192, False, 75, "QHD/1440p display Mali/Vulkan -> downscaled to 75%"),
            (1600, 8192, True, 70, "1600p tablet -> raw 67.5% -> rounded to 70%"),
            (1080, 6144, True, 100, "1080p FHD Adreno with 6GB RAM -> 100%"),
            (1080, 3000, True, 85, "1080p FHD Adreno with low RAM (3GB) -> 85%"),
            (1080, 6144, False, 85, "1080p FHD Mali/Non-Adreno -> 85%"),
            (720, 3000, False, 100, "720p HD display -> 100%"),
            (480, 2048, False, 100, "480p low-res display -> 100%"),
            (240, 1024, False, 100, "240p smartwatch display -> 100%"),
            (1, 4096, False, 100, "1px anomaly min_side -> 100%"),
            (0, 4096, False, 100, "0px uninitialized min_side -> 100%"),
            (-1080, 4096, False, 100, "Negative min_side -> 100%"),
            (16000, 8192, True, 25, "Extreme 16K display -> clamped to min 25%"),
        ]

        for min_side, ram, adreno, expected, desc in cases:
            with self.subTest(desc=desc):
                ratio = HardwareHeuristicEngine.compute_optimal_resolution_ratio(
                    min_side, ram, is_adreno=adreno
                )
                self.assertEqual(ratio, expected, f"{desc}: expected {expected}%, got {ratio}%")
                self.assertTrue(
                    25 <= ratio <= 100,
                    f"Ratio {ratio} outside valid seekbar bounds [25, 100]"
                )
                self.assertEqual(
                    ratio % SEEKBAR_RESOLUTION_INCREMENT, 0,
                    f"Ratio {ratio} not aligned to {SEEKBAR_RESOLUTION_INCREMENT}% increment"
                )

    def test_adv_06_device_hardware_container_edge_cases(self):
        """Verify DeviceHardware dataclass properties with extreme inputs."""
        # Ultra-wide 32:9 monitor
        hw_ultrawide = DeviceHardware(total_ram_mb=12000, screen_width=5120, screen_height=1440)
        self.assertEqual(hw_ultrawide.min_screen_side, 1440)
        self.assertEqual(hw_ultrawide.max_screen_side, 5120)

        # Ultra-tall foldable phone
        hw_foldable = DeviceHardware(total_ram_mb=8000, screen_width=1080, screen_height=3840)
        self.assertEqual(hw_foldable.min_screen_side, 1080)
        self.assertEqual(hw_foldable.max_screen_side, 3840)

        # Inverted orientation (portrait vs landscape)
        hw_portrait = DeviceHardware(total_ram_mb=4000, screen_width=1080, screen_height=2400)
        hw_landscape = DeviceHardware(total_ram_mb=4000, screen_width=2400, screen_height=1080)
        self.assertEqual(hw_portrait.min_screen_side, hw_landscape.min_screen_side)


if __name__ == "__main__":
    unittest.main()
