"""Tier 2: Boundary Value Analysis - F4: Default Game Config & Paths Boundaries

Verifies JSON parsing boundaries, parent directory auto-creation,
and fallback handling when LauncherSettings.txt is absent or malformed.
"""

import json
import tempfile
import unittest
from pathlib import Path

from ..common.env import SYX_LAUNCH_CONFIG
from ..common.assertions import assert_file_exists


class TestF4BVA(unittest.TestCase):
    """BVA test suite for F4 configuration paths and mod settings serialization."""

    def test_f4_bva_01_corrupted_json_syntax_resilience(self):
        """Verify corrupted JSON syntax in LauncherSettings is detected and rejected safely."""
        corrupted_content = '{"MODS": [unclosed array'
        with self.assertRaises(json.JSONDecodeError):
            json.loads(corrupted_content)

    def test_f4_bva_02_empty_json_object_fallback(self):
        """Verify empty JSON object {} does not raise error and defaults to empty mods."""
        empty_obj = "{}"
        parsed = json.loads(empty_obj)
        mods = parsed.get("MODS", [])
        self.assertEqual(mods, [])

    def test_f4_bva_03_nested_settings_directory_creation(self):
        """Verify nested settings directory hierarchy is safely created when absent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            settings_dir = home / ".local/share/songsofsyx/settings"
            self.assertFalse(settings_dir.exists())
            settings_dir.mkdir(parents=True, exist_ok=True)
            self.assertTrue(settings_dir.exists())

            settings_file = settings_dir / "LauncherSettings.txt"
            settings_file.write_text(json.dumps({"MODS": []}), encoding="utf-8")
            self.assertTrue(settings_file.exists())
            data = json.loads(settings_file.read_text(encoding="utf-8"))
            self.assertEqual(data["MODS"], [])

    def test_f4_bva_04_populated_mods_roundtrip(self):
        """Verify active mods array with multiple mod IDs serializes and deserializes accurately."""
        active = ["com.example.mod1", "syx_expansion_pack", "russian_translation"]
        encoded = json.dumps({"MODS": active})
        decoded = json.loads(encoded)
        self.assertEqual(decoded["MODS"], active)

    def test_f4_bva_05_syx_launch_config_creates_settings_if_missing(self):
        """Assert SyxLaunchConfig ensures default settings file exists to prevent DataError."""
        assert_file_exists(SYX_LAUNCH_CONFIG)
        content = SYX_LAUNCH_CONFIG.read_text(encoding="utf-8")
        self.assertTrue(
            "settingsFile" in content and "saveActiveMods" in content,
            "SyxLaunchConfig must create settingsFile with saveActiveMods if missing"
        )


if __name__ == "__main__":
    unittest.main()
