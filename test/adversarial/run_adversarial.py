#!/usr/bin/env python3
"""Runner for Tier 5 Adversarial Stress & Hardening Test Suite."""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path("/workspaces/SoSMobile").resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ADV_DIR = PROJECT_ROOT / "test/adversarial"


def main():
    print("=" * 75)
    print("  SoSMobile Tier 5 Adversarial Stress & Coverage Hardening Test Suite")
    print("=" * 75)

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(ADV_DIR), pattern="test_adv_*.py", top_level_dir=str(PROJECT_ROOT))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 75)
    print(f"Tier 5 Results: Ran {result.testsRun} tests | Failures: {len(result.failures)} | Errors: {len(result.errors)}")
    print("=" * 75)

    if not result.wasSuccessful():
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
