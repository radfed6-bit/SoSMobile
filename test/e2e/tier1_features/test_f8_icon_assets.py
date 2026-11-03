"""Tier 1: Feature Baseline Coverage - F8: Icon Assets Replacement

Verifies that legacy MJ/MOJO icon assets across mipmap, drawable, assets,
and Play Store graphics have been replaced with valid SoSMobile assets.
"""

import unittest
from pathlib import Path

from ..common.env import (
    APP_MOJO_DIR,
    RES_DIR,
    PROJECT_ROOT,
)
from ..common.assertions import assert_file_exists


class TestF8IconAssets(unittest.TestCase):
    """Test suite verifying F8 launcher and notification icon replacements."""

    def test_f8_01_mipmap_launcher_icons_exist_and_non_empty(self):
        """Assert mipmap launcher webp icons exist for all screen densities."""
        densities = ["mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi"]
        for d in densities:
            icon = RES_DIR / f"mipmap-{d}/ic_launcher.webp"
            assert_file_exists(icon, f"Launcher icon missing for density {d}")
            self.assertGreater(icon.stat().st_size, 100, f"Icon {icon} appears empty or truncated")

    def test_f8_02_mipmap_round_icons_exist(self):
        """Assert round launcher icons exist for all densities."""
        densities = ["mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi"]
        for d in densities:
            icon = RES_DIR / f"mipmap-{d}/ic_launcher_round.webp"
            assert_file_exists(icon, f"Round launcher icon missing for density {d}")
            self.assertGreater(icon.stat().st_size, 100)

    def test_f8_03_notification_icons_replaced(self):
        """Assert notification icons exist in drawable directories with non-empty PNG data."""
        densities = ["mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi"]
        for d in densities:
            icon = RES_DIR / f"drawable-{d}/notif_icon.png"
            assert_file_exists(icon, f"Notification icon missing for {d}")
            header = icon.read_bytes()[:8]
            self.assertEqual(header, b"\x89PNG\r\n\x1a\n", f"Invalid PNG magic in {icon}")

    def test_f8_04_full_launcher_drawable_icon(self):
        """Assert ic_mojo_full.webp exists, is non-empty, and has valid WebP header."""
        full_icon = RES_DIR / "drawable/ic_mojo_full.webp"
        assert_file_exists(full_icon)
        data = full_icon.read_bytes()
        self.assertGreater(len(data), 500)
        self.assertEqual(data[:4], b"RIFF")
        self.assertEqual(data[8:12], b"WEBP")

    def test_f8_05_playstore_and_assets_icons(self):
        """Assert Play Store icon (ic_launcher-playstore.png) and assets/mojo.png exist and valid."""
        ps_icon = PROJECT_ROOT / "ic_launcher-playstore.png"
        assert_file_exists(ps_icon)
        self.assertEqual(ps_icon.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

        asset_icon = APP_MOJO_DIR / "src/main/assets/mojo.png"
        assert_file_exists(asset_icon)
        self.assertEqual(asset_icon.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()
