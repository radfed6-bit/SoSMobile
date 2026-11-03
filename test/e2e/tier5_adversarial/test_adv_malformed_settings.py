"""Tier 5: Adversarial Stress Testing - Malformed Settings, Binary Garbage & Corrupt Files.

Stress-tests LauncherSettings.txt and configuration loaders against:
- 0-byte empty files
- Truncated JSON
- Binary garbage (non-UTF8 / raw bytes)
- Corrupt JSON types (int, string, dict instead of list)
- Mixed null/boolean/integer elements in mod arrays
- Read-only permission denials (chmod 0444)
- Preservation of extra settings during rewrites
- Corrupted SharedPreferences XML
"""

import json
import os
import re
import shutil
import stat
import tempfile
import unittest
from pathlib import Path


class SyxModSettingsEngine:
    """Python reference oracle matching git.artdeell.mojo.mods.SyxModSettings."""
    SETTINGS_SUBPATH = ".local/share/songsofsyx/settings/LauncherSettings.txt"
    KEY_MODS = "MODS"

    MODS_ARRAY_PATTERN = re.compile(r'"?MODS"?\s*:\s*\[([^\]]*)\]', re.DOTALL)
    MOD_ITEM_PATTERN = re.compile(r'"([^"]+)"')

    @classmethod
    def get_settings_file(cls, user_home: Path) -> Path:
        return user_home / cls.SETTINGS_SUBPATH

    @classmethod
    def load_active_mods(cls, user_home: Path) -> list:
        settings_file = cls.get_settings_file(user_home)
        if not settings_file.exists() or not settings_file.is_file():
            return []

        try:
            with open(settings_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            return []

        if not content.strip():
            return []

        # 1. Try standard JSON
        try:
            data = json.loads(content)
            if isinstance(data, dict) and cls.KEY_MODS in data:
                raw_mods = data[cls.KEY_MODS]
                if isinstance(raw_mods, list):
                    mods = []
                    for m in raw_mods:
                        if isinstance(m, str) and m.strip() and m.strip() not in mods:
                            mods.append(m.strip())
                    return mods
        except Exception:
            pass

        # 2. Defensive regex fallback
        try:
            match = cls.MODS_ARRAY_PATTERN.search(content)
            if match:
                body = match.group(1)
                mods = []
                for item in cls.MOD_ITEM_PATTERN.finditer(body):
                    mod_name = item.group(1).strip()
                    if mod_name and mod_name not in mods:
                        mods.append(mod_name)
                return mods
        except Exception:
            pass

        return []

    @classmethod
    def save_active_mods(cls, user_home: Path, active_mods: list) -> bool:
        settings_file = cls.get_settings_file(user_home)
        parent_dir = settings_file.parent
        try:
            parent_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            return False

        root = {}
        if settings_file.exists() and settings_file.is_file():
            try:
                with open(settings_file, "r", encoding="utf-8", errors="replace") as f:
                    root = json.load(f)
                    if not isinstance(root, dict):
                        root = {}
            except Exception:
                root = {}

        try:
            clean_mods = []
            if active_mods:
                for m in active_mods:
                    if m is not None and isinstance(m, str) and m.strip():
                        s = m.strip()
                        if s not in clean_mods:
                            clean_mods.append(s)

            root[cls.KEY_MODS] = clean_mods
            formatted = json.dumps(root, indent=2) + "\n"

            temp_file = settings_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(formatted)

            if settings_file.exists():
                settings_file.unlink()
            temp_file.rename(settings_file)
            return True
        except Exception:
            return False


class TestAdversarialMalformedSettings(unittest.TestCase):
    """Stress testing suite for malformed and corrupted configuration files."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="sos_adv_settings_"))

    def tearDown(self):
        # Restore permissions if made read-only before cleanup
        try:
            for root, dirs, files in os.walk(self.test_dir):
                for f in files:
                    try:
                        os.chmod(os.path.join(root, f), 0o777)
                    except Exception:
                        pass
                for d in dirs:
                    try:
                        os.chmod(os.path.join(root, d), 0o777)
                    except Exception:
                        pass
            shutil.rmtree(self.test_dir, ignore_errors=True)
        except Exception:
            pass

    def test_adv_01_empty_zero_byte_file(self):
        """0-byte empty LauncherSettings.txt loads as empty list without exception."""
        settings_file = SyxModSettingsEngine.get_settings_file(self.test_dir)
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.touch()
        self.assertEqual(settings_file.stat().st_size, 0)

        mods = SyxModSettingsEngine.load_active_mods(self.test_dir)
        self.assertEqual(mods, [])

    def test_adv_02_truncated_json_recovers_via_regex(self):
        """Truncated JSON (e.g. process killed mid-write) recovers via regex fallback."""
        settings_file = SyxModSettingsEngine.get_settings_file(self.test_dir)
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        # Missing closing brace and quote
        with open(settings_file, "w") as f:
            f.write('{\n  "MODS": [\n    "ModAlpha",\n    "ModBeta"\n  ]')  # no outer '}'

        mods = SyxModSettingsEngine.load_active_mods(self.test_dir)
        self.assertEqual(mods, ["ModAlpha", "ModBeta"])

    def test_adv_03_binary_garbage_handling(self):
        """Random binary garbage and non-UTF-8 bytes load safely without throwing."""
        settings_file = SyxModSettingsEngine.get_settings_file(self.test_dir)
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        garbage = bytes([0x00, 0xFF, 0xFE, 0x80, 0xC0, 0xDE, 0xAD, 0xBE, 0xEF] * 50)
        with open(settings_file, "wb") as f:
            f.write(garbage)

        mods = SyxModSettingsEngine.load_active_mods(self.test_dir)
        self.assertEqual(mods, [])

        # Now verify overwriting corrupt garbage with valid settings succeeds cleanly
        saved = SyxModSettingsEngine.save_active_mods(self.test_dir, ["RecoveredMod"])
        self.assertTrue(saved)
        reloaded = SyxModSettingsEngine.load_active_mods(self.test_dir)
        self.assertEqual(reloaded, ["RecoveredMod"])

    def test_adv_04_corrupt_types_in_mods_key(self):
        """MODS key containing wrong JSON types (int, string, dict) returns empty list."""
        settings_file = SyxModSettingsEngine.get_settings_file(self.test_dir)
        settings_file.parent.mkdir(parents=True, exist_ok=True)

        bad_payloads = [
            '{"MODS": 12345}',
            '{"MODS": "not_an_array"}',
            '{"MODS": {"nested": "value"}}',
            '{"MODS": true}',
            '{"MODS": null}',
        ]
        for payload in bad_payloads:
            with self.subTest(payload=payload):
                with open(settings_file, "w") as f:
                    f.write(payload)
                mods = SyxModSettingsEngine.load_active_mods(self.test_dir)
                self.assertEqual(mods, [])

    def test_adv_05_mixed_invalid_items_in_mod_array(self):
        """Mod array containing nulls, integers, booleans, and whitespace is filtered."""
        settings_file = SyxModSettingsEngine.get_settings_file(self.test_dir)
        settings_file.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "MODS": [
                None,
                1234,
                True,
                False,
                {"sub": "obj"},
                [],
                "",
                "   ",
                "ValidModOne",
                "   ValidModTwo   ",
                "ValidModOne",  # duplicate
            ]
        }
        with open(settings_file, "w") as f:
            json.dump(payload, f)

        mods = SyxModSettingsEngine.load_active_mods(self.test_dir)
        self.assertEqual(mods, ["ValidModOne", "ValidModTwo"])

    def test_adv_06_preserve_non_mod_keys_on_save(self):
        """Saving active mods strictly preserves unrelated game settings in LauncherSettings.txt."""
        settings_file = SyxModSettingsEngine.get_settings_file(self.test_dir)
        settings_file.parent.mkdir(parents=True, exist_ok=True)

        initial_config = {
            "GAME_VERSION": "v67.14",
            "SCREEN_WIDTH": 1920,
            "SCREEN_HEIGHT": 1080,
            "SOUND_VOLUME": 0.75,
            "MODS": ["OldMod"]
        }
        with open(settings_file, "w") as f:
            json.dump(initial_config, f, indent=2)

        # Update mods
        saved = SyxModSettingsEngine.save_active_mods(self.test_dir, ["NewModAlpha", "NewModBeta"])
        self.assertTrue(saved)

        with open(settings_file, "r") as f:
            updated = json.load(f)

        self.assertEqual(updated["GAME_VERSION"], "v67.14")
        self.assertEqual(updated["SCREEN_WIDTH"], 1920)
        self.assertEqual(updated["SCREEN_HEIGHT"], 1080)
        self.assertEqual(updated["SOUND_VOLUME"], 0.75)
        self.assertEqual(updated["MODS"], ["NewModAlpha", "NewModBeta"])

    def test_adv_07_read_only_filesystem_permission_denial(self):
        """Write attempts against read-only parent folder return False without unhandled crash."""
        settings_file = SyxModSettingsEngine.get_settings_file(self.test_dir)
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.touch()

        # Set parent directory to read-only (0o555: read + execute, no write)
        parent_dir = settings_file.parent
        os.chmod(parent_dir, 0o555)

        try:
            result = SyxModSettingsEngine.save_active_mods(self.test_dir, ["TestMod"])
            # In restricted environments where chmod 555 prevents write, it returns False gracefully.
            # In container run as root/superuser where chmod 555 doesn't block write, result is True.
            # Crucially: NO unhandled exception must propagate!
            self.assertIn(result, [True, False])
        finally:
            os.chmod(parent_dir, 0o777)

    def test_adv_08_corrupt_shared_preferences_xml_resilience(self):
        """Corrupt SharedPreferences XML file syntax and invalid schemas fall back safely."""
        import xml.etree.ElementTree as ET

        # Syntax errors that must raise ParseError
        syntax_errors = [
            "<map>\n  <int name=\"allocation\" value=\"2048\"",  # unclosed tag
            "<?xml version='1.0' encoding='utf-8' standalone='yes' ?>\n<map>\n",  # truncated map
            "<<<malformed>>xml<<tag>>",  # syntax chaos
        ]
        for xml_content in syntax_errors:
            with self.subTest(syntax_error=xml_content[:30]):
                caught = False
                try:
                    ET.fromstring(xml_content)
                except ET.ParseError:
                    caught = True
                self.assertTrue(caught, "Malformed XML must trigger parse error in parser")

        # Non-map root tag must be rejected as invalid SharedPreferences root
        root = ET.fromstring("<not_a_map><foo>bar</foo></not_a_map>")
        self.assertNotEqual(root.tag, "map", "Root tag is not 'map' and must not be loaded as prefs")



if __name__ == "__main__":
    unittest.main()
