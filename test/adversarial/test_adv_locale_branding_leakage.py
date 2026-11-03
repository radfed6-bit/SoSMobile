"""Tier 5 Adversarial Test: Locale Coverage & Mojo/MJ Branding Leakage

Adversarially tests all 47 locale XML resources and Java source files for
non-standard transliterations, residual 'MJ' / 'Mojo' branding, and community links.
"""

import glob
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_ROOT = Path("/workspaces/SoSMobile").resolve()
RES_VALUES_DIR = PROJECT_ROOT / "app_mojo/src/main/res"
JAVA_SRC_DIR = PROJECT_ROOT / "app_mojo/src/main/java"


class TestAdvLocaleBrandingLeakage(unittest.TestCase):
    """Adversarial suite for zero Mojo/MJ branding leakage across locales and code."""

    def test_app_short_name_zero_non_latin_mojo_pojav_leaks(self):
        """Assert no non-standard locale has transliterated Mojo/Pojav launcher names."""
        strings_files = list(RES_VALUES_DIR.glob("values*/strings.xml"))
        self.assertGreaterEqual(len(strings_files), 40)

        violations = []
        for sf in strings_files:
            try:
                tree = ET.parse(sf)
                for s in tree.getroot().findall("string"):
                    if s.get("name") == "app_short_name":
                        val = s.text or ""
                        # Bengali transliteration of MojoLauncher
                        if "মোজো" in val:
                            violations.append((str(sf), "app_short_name", val, "Contains Bengali 'মোজোলঞ্চার' (MojoLauncher)"))
                        # Persian transliteration of PojavLauncher
                        if "پوجاو" in val:
                            violations.append((str(sf), "app_short_name", val, "Contains Persian 'پوجاو لانچر' (Pojav Launcher)"))
                        # Punjabi launcher joke string
                        if "Punjabi" in val:
                            violations.append((str(sf), "app_short_name", val, "Contains 'Punjabi launcher'"))
                        # Ensure it's SoSMobile
                        if val != "SoSMobile":
                            violations.append((str(sf), "app_short_name", val, f"Expected 'SoSMobile', got '{val}'"))
            except Exception as e:
                self.fail(f"Failed to parse XML in {sf}: {e}")

        if violations:
            msg = "\n".join([f"  - {v[0]} [{v[1]}]: '{v[2]}' -> {v[3]}" for v in violations])
            self.fail(f"Found app_short_name branding violations across locales:\n{msg}")

    def test_notification_and_service_titles_for_mj(self):
        """Assert service notification titles don't contain residual 'MJ' branding."""
        strings_files = list(RES_VALUES_DIR.glob("values*/strings.xml"))
        mj_service_violations = []

        for sf in strings_files:
            try:
                tree = ET.parse(sf)
                for s in tree.getroot().findall("string"):
                    name = s.get("name", "")
                    val = s.text or ""
                    if name in ("lazy_service_default_title", "modpack_install_notification_title"):
                        # Check for MJ as standalone word or hyphenated prefix (e.g. "MJ-")
                        if re.search(r"\bMJ\b|MJ-|-MJ|MJu\b", val):
                            mj_service_violations.append((str(sf), name, val))
            except Exception as e:
                self.fail(f"Failed to parse XML in {sf}: {e}")

        if mj_service_violations:
            msg = "\n".join([f"  - {v[0]} [{v[1]}]: '{v[2]}'" for v in mj_service_violations])
            self.fail(f"Found residual 'MJ' branding in notification titles across locales:\n{msg}")

    def test_dialog_and_error_strings_for_mj_or_pojav(self):
        """Assert error and permission dialogs do not leak Mojo, Pojav, or MJ."""
        strings_files = list(RES_VALUES_DIR.glob("values*/strings.xml"))
        dialog_violations = []

        target_string_names = {
            "error_fatal",
            "notification_permission_dialog_text",
            "forge_dl_no_installer",
        }

        for sf in strings_files:
            try:
                tree = ET.parse(sf)
                for s in tree.getroot().findall("string"):
                    name = s.get("name", "")
                    val = s.text or ""
                    if name in target_string_names:
                        if re.search(r"\b(MJ|Mojo|MJLauncher|Pojav|PojavLauncher)\b", val, re.I):
                            dialog_violations.append((str(sf), name, val))
            except Exception as e:
                self.fail(f"Failed to parse XML in {sf}: {e}")

        if dialog_violations:
            msg = "\n".join([f"  - {v[0]} [{v[1]}]: '{v[2]}'" for v in dialog_violations])
            self.fail(f"Found residual branding in dialog/error strings:\n{msg}")

    def test_zero_community_links_in_strings(self):
        """Assert zero external Discord or MojoLauncher Telegram links in strings.xml."""
        strings_files = list(RES_VALUES_DIR.glob("values*/strings.xml"))
        link_violations = []

        forbidden_links = ["discord.gg", "t.me/MojoLauncher", "mojolauncher.github.io"]
        for sf in strings_files:
            content = sf.read_text(encoding="utf-8")
            for fl in forbidden_links:
                if fl in content:
                    link_violations.append((str(sf), fl))

        if link_violations:
            msg = "\n".join([f"  - {v[0]}: contains '{v[1]}'" for v in link_violations])
            self.fail(f"Found forbidden external links in strings files:\n{msg}")

    def test_java_source_clipboard_and_telemetry(self):
        """Assert Java source code does not use 'MJ' or 'MojoLauncher' user-facing strings."""
        clipboard_file = JAVA_SRC_DIR / "git/artdeell/mojo/game/platform/clipboard/AndroidClipboard.java"
        if clipboard_file.exists():
            content = clipboard_file.read_text(encoding="utf-8")
            self.assertNotIn('"MJ Paste"', content,
                             "AndroidClipboard.java should use 'SoSMobile Paste' or generic label instead of 'MJ Paste'")


if __name__ == "__main__":
    unittest.main()
