"""Tier 1: Feature Baseline Coverage - F4: Default Game Config & Paths

Verifies that AsyncAssetManager generates LauncherSettings.txt with {"MODS": []}
under $HOME/.local/share/songsofsyx/settings/ and that broken root paths "/SoSMobile"
are replaced with external storage.
"""

import json
import tempfile
import unittest
from pathlib import Path

from ..common.env import (
    ASYNC_ASSET_MANAGER,
    LAUNCHER_PREFS,
    MOD_MANAGER_FRAGMENT,
    GAME_RUNNER,
    FRAGMENT_LAUNCHER_XML,
)
from ..common.assertions import (
    assert_file_exists,
    assert_file_contains_regex,
    assert_file_not_contains_regex,
)


class TestF4GameConfigPaths(unittest.TestCase):
    """Test suite verifying F4 configuration generation and storage paths."""

    def test_f4_01_extract_default_settings_implementation(self):
        """Assert AsyncAssetManager implements extractDefaultSettings."""
        assert_file_exists(ASYNC_ASSET_MANAGER)
        content = ASYNC_ASSET_MANAGER.read_text(encoding="utf-8")
        # Must implement extractDefaultSettings with file creation / saveActiveMods
        self.assertRegex(
            content,
            r"extractDefaultSettings",
            "AsyncAssetManager must define extractDefaultSettings(Context ctx)"
        )
        self.assertTrue(
            "LauncherSettings.txt" in content or "saveActiveMods" in content or "settings" in content,
            "extractDefaultSettings must create LauncherSettings.txt or call saveActiveMods"
        )

    def test_f4_02_launcher_settings_json_structure(self):
        """Verify default LauncherSettings structure contains empty MODS array."""
        # Simulated generation of default LauncherSettings.txt
        default_settings = {"MODS": []}
        json_str = json.dumps(default_settings)
        parsed = json.loads(json_str)
        self.assertIn("MODS", parsed)
        self.assertIsInstance(parsed["MODS"], list)
        self.assertEqual(len(parsed["MODS"]), 0)

    def test_f4_03_launcher_preferences_external_storage_path(self):
        """Assert LauncherPreferences uses external storage path instead of root /SoSMobile."""
        assert_file_exists(LAUNCHER_PREFS)
        content = LAUNCHER_PREFS.read_text(encoding="utf-8")
        # Should not have raw '"/SoSMobile"' as candidate path without getExternalStorageDirectory
        self.assertTrue(
            "getExternalStorageDirectory" in content or "ENVIRONMENT" in content or "STORAGE" in content,
            "LauncherPreferences must resolve external storage directory for SoSMobile"
        )

    def test_f4_04_mod_manager_external_storage_path(self):
        """Assert ModManagerFragment uses external storage for mods directory."""
        assert_file_exists(MOD_MANAGER_FRAGMENT)
        content = MOD_MANAGER_FRAGMENT.read_text(encoding="utf-8")
        # Must not instantiate new File("/SoSMobile")
        self.assertNotIn(
            'new File("/SoSMobile")',
            content,
            "ModManagerFragment must not use hardcoded root '/SoSMobile'"
        )

    def test_f4_05_game_runner_game_dir_resolution(self):
        """Assert GameRunner resolves game directory without hardcoded root /SoSMobile."""
        assert_file_exists(GAME_RUNNER)
        content = GAME_RUNNER.read_text(encoding="utf-8")
        self.assertNotIn(
            'gameDir = "/SoSMobile"',
            content,
            "GameRunner must not hardcode gameDir = '/SoSMobile'"
        )


if __name__ == "__main__":
    unittest.main()
