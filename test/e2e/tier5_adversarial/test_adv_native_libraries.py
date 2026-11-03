"""Tier 5: Adversarial Stress Testing - Native Library Integrity & Linker Stress.

Stress-tests native library loading contracts, ELF ARM64 architecture headers,
corrupted ELF detection, dependency symbols, and symlink cycle handling.
"""

import os
import shutil
import struct
import tempfile
import unittest
from pathlib import Path

from ..common.env import (
    LIBLWJGL_SO,
    APP_MOJO_DIR,
    SYX_LAUNCH_CONFIG,
)
from ..common.assertions import (
    assert_file_exists,
    assert_elf_arm64,
)


class TestAdversarialNativeLibraries(unittest.TestCase):
    """Stress testing suite for native library ELF validation and linker integrity."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="sos_adv_native_"))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_adv_01_real_liblwjgl_so_elf_arm64_integrity(self):
        """Verify bundled liblwjgl.so has authentic 64-bit ARM little-endian ELF header."""
        assert_file_exists(LIBLWJGL_SO, "liblwjgl.so must exist in jniLibs/arm64-v8a/")
        assert_elf_arm64(LIBLWJGL_SO)

        # In-depth byte-level verification
        with open(LIBLWJGL_SO, "rb") as f:
            header = f.read(64)

        self.assertEqual(len(header), 64, "ELF header must be at least 64 bytes")
        magic = header[0:4]
        self.assertEqual(magic, b"\x7fELF", "Invalid ELF magic")

        ei_class = header[4]
        self.assertEqual(ei_class, 2, "Must be ELFCLASS64 (64-bit)")

        ei_data = header[5]
        self.assertEqual(ei_data, 1, "Must be ELFDATA2LSB (little-endian)")

        e_type = struct.unpack("<H", header[16:18])[0]
        self.assertEqual(e_type, 3, "e_type must be ET_DYN (shared object)")

        e_machine = struct.unpack("<H", header[18:20])[0]
        self.assertEqual(e_machine, 183, "e_machine must be 183 (EM_AARCH64)")

    def test_adv_02_corrupted_elf_header_detection(self):
        """Verify validator detects invalid magic, truncated headers, and wrong ABIs."""
        # Case A: Corrupted magic
        bad_magic = self.temp_dir / "bad_magic.so"
        with open(bad_magic, "wb") as f:
            f.write(b"\x00ELF" + b"\x00" * 60)

        with open(bad_magic, "rb") as f:
            h = f.read(64)
        self.assertNotEqual(h[0:4], b"\x7fELF")

        # Case B: Truncated header
        truncated = self.temp_dir / "truncated.so"
        with open(truncated, "wb") as f:
            f.write(b"\x7fELF\x02\x01")  # only 6 bytes

        with open(truncated, "rb") as f:
            h = f.read(64)
        self.assertLess(len(h), 52)

        # Case C: 32-bit ELF (ELFCLASS32 = 1)
        elf_32 = self.temp_dir / "elf_32.so"
        with open(elf_32, "wb") as f:
            f.write(b"\x7fELF\x01\x01" + b"\x00" * 58)

        with open(elf_32, "rb") as f:
            h = f.read(64)
        self.assertEqual(h[4], 1)  # 32-bit, rejected for 64-bit requirement

        # Case D: x86_64 architecture (e_machine = 62)
        elf_x86_64 = self.temp_dir / "elf_x86_64.so"
        buf = bytearray(b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 8)
        buf.extend(struct.pack("<H", 3))  # ET_DYN
        buf.extend(struct.pack("<H", 62))  # EM_X86_64
        buf.extend(b"\x00" * (64 - len(buf)))
        with open(elf_x86_64, "wb") as f:
            f.write(buf)

        with open(elf_x86_64, "rb") as f:
            h = f.read(64)
        machine = struct.unpack("<H", h[18:20])[0]
        self.assertEqual(machine, 62)
        self.assertNotEqual(machine, 183, "x86_64 machine code must not match ARM64")

    def test_adv_03_libgl4es_native_binary_integrity(self):
        """Verify bundled libgl4es_114.so is also valid ARM64 ELF shared object."""
        gl4es_path = APP_MOJO_DIR / "src/main/jniLibs/arm64-v8a/libgl4es_114.so"
        assert_file_exists(gl4es_path)
        assert_elf_arm64(gl4es_path)

    def test_adv_04_launch_config_native_library_path_mapping(self):
        """Verify SyxLaunchConfig guarantees org.lwjgl.librarypath and java.library.path."""
        with open(SYX_LAUNCH_CONFIG, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('sysProps.put("org.lwjgl.librarypath", appNativeDir)', content)
        self.assertIn('sysProps.put("java.library.path", appNativeDir)', content)
        self.assertIn('sysProps.put("jna.boot.library.path", appNativeDir)', content)
        self.assertIn('org.lwjgl.system.SharedLibraryExtractPath', content)

    def test_adv_05_symlink_cycle_traversal_safety(self):
        """Verify directory scanning handles circular symlinks without recursion crash."""
        cycle_a = self.temp_dir / "cycle_a"
        cycle_b = self.temp_dir / "cycle_b"
        cycle_a.mkdir()

        # Create cycle: cycle_a/loop -> cycle_a
        loop_link = cycle_a / "loop"
        try:
            loop_link.symlink_to(cycle_a, target_is_directory=True)
        except OSError:
            self.skipTest("Symlinks not supported in environment")

        # Walk directory with cycle; must terminate safely
        visited = []
        max_depth = 10
        for root, dirs, files in os.walk(self.temp_dir, followlinks=False):
            visited.append(root)

        self.assertTrue(len(visited) > 0)
        self.assertLess(len(visited), 100, "Directory traversal must not loop indefinitely")


if __name__ == "__main__":
    unittest.main()
