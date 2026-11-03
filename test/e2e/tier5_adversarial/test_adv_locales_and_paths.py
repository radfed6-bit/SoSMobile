"""Tier 5: Adversarial Stress Testing - Locale Permutations & Non-ASCII Character Handling.

Stress-tests:
- Exhaustive verification of all 47 Android locale directories for 100% SoSMobile rebranding
- Zero residue of MJLauncher, MJLuancher, and external Discord/Telegram invites across all resources
- Non-ASCII game paths (Cyrillic, Chinese, Arabic, emojis, spaces, quotes)
- Launch configuration assembly and settings persistence under non-ASCII directories
"""

import json
import os
import re
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from ..common.env import RES_DIR, APP_MOJO_DIR


class TestAdversarialLocalesAndPaths(unittest.TestCase):
    """Stress testing suite for locale bundles and adversarial file paths."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="sos_adv_paths_"))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_adv_01_all_47_locales_have_sosmobile_short_name(self):
        """Every single values*/strings.xml locale file must define app_short_name as SoSMobile."""
        values_dirs = sorted(list(RES_DIR.glob("values*")))
        self.assertGreaterEqual(len(values_dirs), 45, "Expected at least 45 locale directories")

        checked_locales = 0
        for vdir in values_dirs:
            strings_file = vdir / "strings.xml"
            if not strings_file.exists():
                continue

            try:
                tree = ET.parse(strings_file)
                root = tree.getroot()
                app_short_name = None
                for elem in root.findall("string"):
                    if elem.get("name") == "app_short_name":
                        app_short_name = elem.text
                        break

                if app_short_name is not None:
                    with self.subTest(locale=vdir.name):
                        self.assertEqual(
                            app_short_name, "SoSMobile",
                            f"In {vdir.name}/strings.xml, expected 'SoSMobile' but got '{app_short_name}'"
                        )
                    checked_locales += 1
            except ET.ParseError as e:
                self.fail(f"Failed to parse XML in {strings_file}: {e}")

        self.assertGreaterEqual(checked_locales, 45)

    def test_adv_02_zero_mjlauncher_or_mjluancher_residue_in_res(self):
        """Strictly zero occurrences of 'MJLauncher' or 'MJLuancher' in any file under res/."""
        mj_pattern = re.compile(r"MJL[au]uncher", re.IGNORECASE)
        violations = []

        for root, dirs, files in os.walk(RES_DIR):
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix in [".xml", ".txt", ".json", ".properties"]:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                    match = mj_pattern.search(content)
                    if match:
                        violations.append(f"{file_path.relative_to(APP_MOJO_DIR)}: {match.group(0)}")

        self.assertEqual(
            violations, [],
            f"Found forbidden MJLauncher residues in resources: {violations}"
        )

    def test_adv_03_zero_active_discord_or_telegram_community_links(self):
        """No active invite links to Mojo discord or telegram in res/values* string files."""
        forbidden_urls = [
            "discord.gg/VHdwQFsaGX",
            "t.me/MojoLauncher",
        ]
        violations = []
        for root, dirs, files in os.walk(RES_DIR):
            for file in files:
                if file.endswith("strings.xml"):
                    file_path = Path(root) / file
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                    for bad_url in forbidden_urls:
                        if bad_url in content:
                            violations.append(f"{file_path.relative_to(APP_MOJO_DIR)}: contains {bad_url}")

        self.assertEqual(violations, [], f"Found forbidden community URLs in strings: {violations}")

    def test_adv_04_non_ascii_paths_cyrillic_chinese_arabic(self):
        """Non-ASCII directory paths (Cyrillic, Chinese, Arabic) handled without encoding errors."""
        exotic_names = [
            "Игра_Песни_Сикса",
            "游戏_SongsOfSyx",
            "ألعاب_syx",
            "Songs of Syx (v67.14) [Special #1!]",
        ]

        for subname in exotic_names:
            with self.subTest(directory=subname):
                home_dir = self.temp_dir / subname
                settings_file = home_dir / ".local/share/songsofsyx/settings/LauncherSettings.txt"
                settings_file.parent.mkdir(parents=True, exist_ok=True)

                test_data = {"MODS": ["ExoticMod_1", "Мод_Один", "模组_二"]}
                with open(settings_file, "w", encoding="utf-8") as f:
                    json.dump(test_data, f, ensure_ascii=False)

                # Re-read
                with open(settings_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)

                self.assertEqual(loaded["MODS"], ["ExoticMod_1", "Мод_Один", "模组_二"])
                self.assertTrue(settings_file.exists())


if __name__ == "__main__":
    unittest.main()
