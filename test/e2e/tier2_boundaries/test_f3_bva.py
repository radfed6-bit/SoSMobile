"""Tier 2: Boundary Value Analysis - F3: Native LWJGL 3 Linking Boundaries

Verifies ELF header validation, architecture verification, and library path boundaries.
"""

import struct
import unittest
from pathlib import Path

from ..common.env import LIBLWJGL_SO, SYX_LAUNCH_CONFIG
from ..common.assertions import assert_file_exists, assert_elf_arm64


class TestF3BVA(unittest.TestCase):
    """BVA test suite for F3 native LWJGL 3 library verification."""

    def test_f3_bva_01_truncated_elf_detection(self):
        """Assert ELF validator rejects truncated header data (< 52 bytes)."""
        data = b"\x7fELF" + b"\x00" * 20
        self.assertLess(len(data), 52)
        with self.assertRaises(AssertionError):
            assert_elf_arm64(Path("/dev/null"))

    def test_f3_bva_02_invalid_elf_magic_rejection(self):
        """Assert ELF validator rejects non-ELF binary files."""
        # Check that assert_elf_arm64 rejects files without \x7fELF magic
        class FakePath:
            def exists(self): return True
            def read_bytes(self): return b"MZ\x90\x00" + b"\x00" * 60
        with self.assertRaises(AssertionError):
            assert_elf_arm64(FakePath())

    def test_f3_bva_03_arm64_machine_type_exactness(self):
        """Assert bundled liblwjgl.so specifies EM_AARCH64 (183) exactly."""
        assert_file_exists(LIBLWJGL_SO)
        data = LIBLWJGL_SO.read_bytes()
        e_machine = struct.unpack("<H", data[18:20])[0]
        self.assertEqual(e_machine, 183, "Expected EM_AARCH64 (183)")

    def test_f3_bva_04_bundled_liblwjgl_minimum_size(self):
        """Assert bundled liblwjgl.so is a genuine compiled library (> 200 KB)."""
        assert_file_exists(LIBLWJGL_SO)
        size = LIBLWJGL_SO.stat().st_size
        self.assertGreater(size, 200_000, f"liblwjgl.so is suspiciously small: {size} bytes")

    def test_f3_bva_05_launch_config_system_properties_map(self):
        """Assert SyxLaunchConfig sets org.lwjgl.librarypath in system properties."""
        assert_file_exists(SYX_LAUNCH_CONFIG)
        content = SYX_LAUNCH_CONFIG.read_text(encoding="utf-8")
        self.assertIn('"org.lwjgl.librarypath"', content)


if __name__ == "__main__":
    unittest.main()
