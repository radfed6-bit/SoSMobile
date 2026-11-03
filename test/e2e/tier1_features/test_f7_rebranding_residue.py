"""Tier 1: Feature Baseline Coverage - F7: Main Menu Rebranding & Residue

Verifies that app_short_name is updated to "SoSMobile" across all 45+ locales,
and that Wiki/Discord buttons, dividers, and listeners are purged from layouts and MainMenuFragment.
"""

import re
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

from ..common.env import (
    RES_DIR,
    FRAGMENT_LAUNCHER_XML,
    FRAGMENT_LAUNCHER_LAND_XML,
    MAIN_MENU_FRAGMENT,
)
from ..common.assertions import (
    assert_file_exists,
    assert_file_not_contains_regex,
)


class TestF7RebrandingResidue(unittest.TestCase):
    """Test suite verifying F7 rebranding and residual UI cleanup."""

    def test_f7_01_app_short_name_across_all_locales(self):
        """Assert app_short_name is 'SoSMobile' and never 'MJLauncher' across all values*/strings.xml."""
        strings_files = list(RES_DIR.glob("values*/strings.xml"))
        self.assertGreaterEqual(len(strings_files), 40, "Expected at least 40 locale strings files")

        for f in strings_files:
            content = f.read_text(encoding="utf-8")
            self.assertNotIn(
                "<string name=\"app_short_name\">MJLauncher</string>",
                content,
                f"Found legacy 'MJLauncher' app_short_name in {f}"
            )
            # Verify default values/strings.xml sets SoSMobile
            if f.parent.name == "values":
                self.assertIn(
                    "<string name=\"app_short_name\">SoSMobile</string>",
                    content,
                    f"Default {f} must define app_short_name as SoSMobile"
                )

    def test_f7_02_wiki_button_removed_from_layouts(self):
        """Assert news_button (Wiki) is removed from both portrait and landscape fragment_launcher.xml."""
        for layout_path in [FRAGMENT_LAUNCHER_XML, FRAGMENT_LAUNCHER_LAND_XML]:
            if layout_path.exists():
                content = layout_path.read_text(encoding="utf-8")
                self.assertNotIn(
                    "@+id/news_button",
                    content,
                    f"Wiki button (@+id/news_button) must be removed from {layout_path}"
                )

    def test_f7_03_discord_button_removed_from_layouts(self):
        """Assert social_media_button (Discord) is removed from fragment_launcher.xml."""
        for layout_path in [FRAGMENT_LAUNCHER_XML, FRAGMENT_LAUNCHER_LAND_XML]:
            if layout_path.exists():
                content = layout_path.read_text(encoding="utf-8")
                self.assertNotIn(
                    "@+id/social_media_button",
                    content,
                    f"Discord button (@+id/social_media_button) must be removed from {layout_path}"
                )

    def test_f7_04_social_divider_removed_from_layouts(self):
        """Assert social_divider is removed from fragment_launcher.xml."""
        for layout_path in [FRAGMENT_LAUNCHER_XML, FRAGMENT_LAUNCHER_LAND_XML]:
            if layout_path.exists():
                content = layout_path.read_text(encoding="utf-8")
                self.assertNotIn(
                    "@+id/social_divider",
                    content,
                    f"social_divider must be removed from {layout_path}"
                )

    def test_f7_05_main_menu_fragment_listeners_removed(self):
        """Assert MainMenuFragment has no active bindings/listeners for news or discord buttons."""
        assert_file_exists(MAIN_MENU_FRAGMENT)
        content = MAIN_MENU_FRAGMENT.read_text(encoding="utf-8")
        self.assertNotIn(
            "mNewsButton.setOnClickListener",
            content,
            "MainMenuFragment must not have click listener for news/wiki button"
        )
        self.assertNotIn(
            "mDiscordButton.setOnClickListener",
            content,
            "MainMenuFragment must not have click listener for discord button"
        )


if __name__ == "__main__":
    unittest.main()
