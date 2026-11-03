"""Tier 2: Boundary Value Analysis - F8: Icon Assets Boundaries

Verifies binary format chunk headers, IHDR chunk dimensions, non-zero file sizes,
and WebP structural integrity across mipmap and drawable assets.
"""

import struct
import unittest
from pathlib import Path

from ..common.env import RES_DIR
from ..common.assertions import assert_file_exists


class TestF8BVA(unittest.TestCase):
    """BVA test suite for F8 icon binary headers and chunk verification."""

    def test_f8_bva_01_webp_riff_chunk_structure(self):
        """Assert all mipmap launcher icons start with RIFF header and WEBP fourcc."""
        for p in RES_DIR.glob("mipmap-*/ic_launcher*.webp"):
            data = p.read_bytes()
            self.assertGreaterEqual(len(data), 12, f"File {p} is too small to be WebP")
            self.assertEqual(data[:4], b"RIFF", f"{p} missing RIFF magic")
            self.assertEqual(data[8:12], b"WEBP", f"{p} missing WEBP fourcc")

    def test_f8_bva_02_png_ihdr_chunk_structure(self):
        """Assert all notification PNG icons contain valid IHDR chunk."""
        for p in RES_DIR.glob("drawable-*/notif_icon.png"):
            data = p.read_bytes()
            self.assertGreaterEqual(len(data), 24, f"{p} too small for PNG IHDR")
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(data[12:16], b"IHDR")

    def test_f8_bva_03_notification_icons_square_aspect(self):
        """Assert notification icons have 1:1 square aspect ratio from IHDR width/height."""
        for p in RES_DIR.glob("drawable-*/notif_icon.png"):
            data = p.read_bytes()
            width, height = struct.unpack(">II", data[16:24])
            self.assertEqual(width, height, f"{p} has non-square dimensions: {width}x{height}")
            self.assertGreater(width, 0)

    def test_f8_bva_04_no_empty_image_files(self):
        """Assert no webp or png file in res/ is empty (0 bytes)."""
        image_files = list(RES_DIR.glob("**/*.webp")) + list(RES_DIR.glob("**/*.png"))
        for img in image_files:
            self.assertGreater(img.stat().st_size, 0, f"Found empty image file: {img}")

    def test_f8_bva_05_ic_mojo_full_size_bounds(self):
        """Assert full launcher icon is properly detailed (> 1 KB)."""
        full_icon = RES_DIR / "drawable/ic_mojo_full.webp"
        assert_file_exists(full_icon)
        self.assertGreater(full_icon.stat().st_size, 1024)


if __name__ == "__main__":
    unittest.main()
