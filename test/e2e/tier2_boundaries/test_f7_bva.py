"""Tier 2: Boundary Value Analysis - F7: Main Menu Rebranding Boundaries

Verifies RTL locales, case-insensitive branding absence, landscape layout parity,
and XML well-formedness across all 45+ strings files.
"""

import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from ..common.env import (
    RES_DIR,
    FRAGMENT_LAUNCHER_XML,
    FRAGMENT_LAUNCHER_LAND_XML,
)


class TestF7BVA(unittest.TestCase):
    """BVA test suite for F7 rebranding and locale XML parsing."""

    def test_f7_bva_01_xml_well_formedness_all_locales(self):
        """Assert all 45+ values*/strings.xml parse as well-formed XML without syntax errors."""
        strings_files = list(RES_DIR.glob("values*/strings.xml"))
        for f in strings_files:
            try:
                ET.parse(str(f))
            except ET.ParseError as e:
                self.fail(f"XML parse error in {f}: {e}")

    def test_f7_bva_02_rtl_locales_app_short_name(self):
        """Assert RTL locales (Arabic values-ar, Hebrew values-iw) have correct SoSMobile string."""
        for rtl_dir in ["values-ar", "values-iw"]:
            p = RES_DIR / rtl_dir / "strings.xml"
            if p.exists():
                content = p.read_text(encoding="utf-8")
                self.assertIn("<string name=\"app_short_name\">SoSMobile</string>", content)

    def test_f7_bva_03_case_insensitive_mjlauncher_absence_in_strings(self):
        """Assert 'mjlauncher' (case-insensitive) is absent from app_short_name across all locales."""
        strings_files = list(RES_DIR.glob("values*/strings.xml"))
        for f in strings_files:
            content = f.read_text(encoding="utf-8").lower()
            self.assertNotIn("<string name=\"app_short_name\">mjlauncher</string>", content)

    def test_f7_bva_04_landscape_and_portrait_button_removal_parity(self):
        """Assert landscape layout mirrors portrait layout in removing news_button and social_media_button."""
        if FRAGMENT_LAUNCHER_LAND_XML.exists() and FRAGMENT_LAUNCHER_XML.exists():
            land_content = FRAGMENT_LAUNCHER_LAND_XML.read_text(encoding="utf-8")
            port_content = FRAGMENT_LAUNCHER_XML.read_text(encoding="utf-8")
            for btn_id in ["news_button", "social_media_button", "social_divider"]:
                self.assertNotIn(btn_id, land_content, f"{btn_id} found in landscape layout")
                self.assertNotIn(btn_id, port_content, f"{btn_id} found in portrait layout")

    def test_f7_bva_05_obsolete_social_urls_purged(self):
        """Assert obsolete Discord invite URLs are not used in main layouts."""
        for layout in [FRAGMENT_LAUNCHER_XML, FRAGMENT_LAUNCHER_LAND_XML]:
            if layout.exists():
                content = layout.read_text(encoding="utf-8")
                self.assertNotIn("discord.gg", content)
                self.assertNotIn("t.me/MojoLauncher", content)


if __name__ == "__main__":
    unittest.main()
