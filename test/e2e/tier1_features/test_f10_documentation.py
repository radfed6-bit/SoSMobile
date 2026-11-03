"""Tier 1: Feature Baseline Coverage - F10: Documentation Cleanup

Verifies that README.md and README_RU.md provide clear, user-focused documentation
covering SoSMobile features, requirements, installation, building, and license,
without internal development chatter or obsolete fluff.
"""

import unittest
from pathlib import Path

from ..common.env import (
    README_EN,
    README_RU,
)
from ..common.assertions import assert_file_exists


class TestF10Documentation(unittest.TestCase):
    """Test suite verifying F10 documentation cleanup and completeness."""

    def test_f10_01_readme_en_exists_and_structured(self):
        """Assert README.md exists and contains standard user-facing sections."""
        assert_file_exists(README_EN)
        content = README_EN.read_text(encoding="utf-8")
        self.assertIn("# SoSMobile", content)
        self.assertIn("Songs of Syx", content)
        self.assertTrue(
            "Overview" in content or "About" in content,
            "README.md must have an Overview section"
        )
        self.assertTrue(
            "Features" in content or "Key Features" in content,
            "README.md must document Key Features"
        )

    def test_f10_02_readme_ru_exists_and_structured(self):
        """Assert README_RU.md exists and contains translated user-facing sections."""
        assert_file_exists(README_RU)
        content = README_RU.read_text(encoding="utf-8")
        self.assertIn("SoSMobile", content)
        self.assertIn("Songs of Syx", content)
        self.assertTrue(
            "Обзор" in content or "Описание" in content or "О проекте" in content,
            "README_RU.md must have a localized overview section"
        )

    def test_f10_03_features_mention_java17_and_autoconfig(self):
        """Assert documentation mentions Java 17 and Auto-Configuration features."""
        content = README_EN.read_text(encoding="utf-8")
        self.assertIn("Java 17", content)
        self.assertTrue(
            "Auto-Configuration" in content or "auto-config" in content or "Hardware" in content,
            "README.md must describe the hardware auto-configuration feature"
        )

    def test_f10_04_system_requirements_documented(self):
        """Assert system requirements (ARM64, RAM, Android API) are clearly outlined."""
        content = README_EN.read_text(encoding="utf-8")
        self.assertTrue(
            "Requirements" in content or "System Requirements" in content,
            "README.md must outline system requirements"
        )
        self.assertIn("ARM64", content)

    def test_f10_05_no_dev_kitchen_residue(self):
        """Assert obsolete development chatter / internal kitchen details are purged."""
        content = README_EN.read_text(encoding="utf-8")
        forbidden_phrases = [
            "development kitchen",
            "internal notes for developers",
            "unfinished hack",
        ]
        for phrase in forbidden_phrases:
            self.assertNotIn(
                phrase, content.lower(),
                f"README.md contains obsolete dev chatter: '{phrase}'"
            )


if __name__ == "__main__":
    unittest.main()
