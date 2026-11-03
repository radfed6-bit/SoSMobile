"""Tier 2: Boundary Value Analysis - F10: Documentation Boundaries

Verifies markdown syntax boundaries, code block balance, UTF-8 validity,
and structural parity between English and Russian READMEs.
"""

import re
import unittest
from pathlib import Path

from ..common.env import README_EN, README_RU
from ..common.assertions import assert_file_exists


class TestF10BVA(unittest.TestCase):
    """BVA test suite for F10 documentation markdown syntax and parity."""

    def test_f10_bva_01_code_block_backticks_balance(self):
        """Assert triple backticks for code blocks are balanced (even count) in both READMEs."""
        for p in [README_EN, README_RU]:
            content = p.read_text(encoding="utf-8")
            count = len(re.findall(r"```", content))
            self.assertEqual(
                count % 2, 0,
                f"Unbalanced code blocks in {p}: found {count} triple-backticks"
            )

    def test_f10_bva_02_utf8_encoding_cleanliness(self):
        """Assert both README files decode cleanly as UTF-8 without unicode replacement characters."""
        for p in [README_EN, README_RU]:
            data = p.read_bytes()
            decoded = data.decode("utf-8")
            self.assertNotIn("\ufffd", decoded, f"Found unicode replacement character in {p}")

    def test_f10_bva_03_markdown_heading_hierarchy(self):
        """Assert document starts with H1 title and subsequent sections use H2."""
        for p in [README_EN, README_RU]:
            lines = [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertTrue(lines[0].startswith("# "), f"First heading in {p} must be H1 (# )")
            h2_count = sum(1 for line in lines if line.startswith("## "))
            self.assertGreaterEqual(h2_count, 3, f"Expected at least 3 H2 sections in {p}")

    def test_f10_bva_04_no_empty_markdown_links(self):
        """Assert there are no empty links of form [text]() or [](url) in documentation."""
        for p in [README_EN, README_RU]:
            content = p.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"\[\s*\]\([^\)]+\)", content), f"Empty link text in {p}")
            self.assertIsNone(re.search(r"\[[^\]]+\]\(\s*\)", content), f"Empty link target in {p}")

    def test_f10_bva_05_bilingual_structural_parity(self):
        """Assert both English and Russian documentation contain comparable structural sections."""
        en_content = README_EN.read_text(encoding="utf-8")
        ru_content = README_RU.read_text(encoding="utf-8")

        self.assertIn("Requirements", en_content)
        self.assertIn("Требования", ru_content)

        self.assertTrue("Quick Start" in en_content or "Installation" in en_content)
        self.assertTrue("Быстрый старт" in ru_content or "Инструкция" in ru_content or "Запуск игры" in ru_content)


if __name__ == "__main__":
    unittest.main()
