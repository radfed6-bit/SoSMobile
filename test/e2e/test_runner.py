#!/usr/bin/env python3
"""SoSMobile Comprehensive E2E Test Suite Runner

Discovers, executes, and reports on all 4 testing tiers:
- Tier 1: Feature Baseline Coverage (F1-F11)
- Tier 2: Boundary Value Analysis & Corner Cases (F1-F11)
- Tier 3: Cross-Feature Combinations (Pairwise Interactions)
- Tier 4: Real-World Application Scenarios (End-to-End Workflows)

Produces clear pass/fail status and exits with code 0 on success, 1 on failure.
"""

import argparse
import os
import sys
import time
import unittest
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path("/workspaces/SoSMobile").resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TEST_DIR = PROJECT_ROOT / "test/e2e"

TIER_DIRS = {
    1: ("Tier 1: Feature Baseline Coverage", TEST_DIR / "tier1_features"),
    2: ("Tier 2: Boundary Value Analysis & Corner Cases", TEST_DIR / "tier2_boundaries"),
    3: ("Tier 3: Cross-Feature Combinations", TEST_DIR / "tier3_pairwise"),
    4: ("Tier 4: Real-World Application Scenarios", TEST_DIR / "tier4_scenarios"),
}


class ColoredTestResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.successes = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.successes.append(test)
        if self.showAll:
            self.stream.write(" \033[92m[PASS]\033[0m\n")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        if self.showAll:
            self.stream.write(" \033[91m[FAIL]\033[0m\n")

    def addError(self, test, err):
        super().addError(test, err)
        if self.showAll:
            self.stream.write(" \033[91m[ERROR]\033[0m\n")


def run_tier(tier_num: int, tier_name: str, tier_path: Path, verbose: bool):
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(tier_path), top_level_dir=str(PROJECT_ROOT))

    print(f"\n\033[1;34m{'=' * 75}\033[0m")
    print(f"\033[1;36m▶ Running {tier_name} ({tier_path.relative_to(PROJECT_ROOT)})\033[0m")
    print(f"\033[1;34m{'=' * 75}\033[0m")

    stream = sys.stdout
    runner = unittest.TextTestRunner(
        stream=stream,
        resultclass=ColoredTestResult,
        verbosity=2 if verbose else 1
    )

    start_time = time.time()
    result = runner.run(suite)
    elapsed = time.time() - start_time

    pass_count = len(result.successes)
    fail_count = len(result.failures)
    error_count = len(result.errors)
    total_count = result.testsRun

    return {
        "tier": tier_num,
        "name": tier_name,
        "total": total_count,
        "passed": pass_count,
        "failed": fail_count,
        "errors": error_count,
        "elapsed": elapsed,
        "result": result,
    }


def main():
    parser = argparse.ArgumentParser(description="Run SoSMobile E2E Test Suite")
    parser.add_argument(
        "--tier",
        type=int,
        choices=[1, 2, 3, 4],
        help="Run only a specific tier (1, 2, 3, or 4). Default: run all tiers."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable detailed verbose output for each test case."
    )
    args = parser.parse_args()

    tiers_to_run = [args.tier] if args.tier else [1, 2, 3, 4]

    print("\033[1;35m" + "#" * 75)
    print("  SoSMobile End-to-End Test Suite Execution Harness")
    print("  Testing Features F1-F11 across Tiers 1-4")
    print("#" * 75 + "\033[0m")

    overall_start = time.time()
    tier_results = []
    total_run = 0
    total_passed = 0
    total_failed = 0
    total_errors = 0

    for t in tiers_to_run:
        name, path = TIER_DIRS[t]
        res = run_tier(t, name, path, args.verbose)
        tier_results.append(res)
        total_run += res["total"]
        total_passed += res["passed"]
        total_failed += res["failed"]
        total_errors += res["errors"]

    overall_elapsed = time.time() - overall_start

    print("\n\033[1;35m" + "=" * 75)
    print("                      TEST SUITE EXECUTION SUMMARY")
    print("=" * 75 + "\033[0m")

    for res in tier_results:
        status_str = "\033[92mPASS\033[0m" if (res["failed"] == 0 and res["errors"] == 0) else "\033[91mFAIL\033[0m"
        print(f"  [{status_str}] Tier {res['tier']}: {res['name']}")
        print(f"         Total: {res['total']} | Passed: {res['passed']} | Failed: {res['failed']} | Errors: {res['errors']} | Time: {res['elapsed']:.3f}s")

    print("-" * 75)
    print(f"  \033[1mAggregate Metrics:\033[0m")
    print(f"  Total Test Cases:    \033[1m{total_run}\033[0m (Minimum Required: 127)")
    print(f"  Passed:              \033[92m{total_passed}\033[0m")
    print(f"  Failed:              \033[91m{total_failed}\033[0m")
    print(f"  Errors:              \033[91m{total_errors}\033[0m")
    print(f"  Total Duration:      {overall_elapsed:.3f}s")
    print("=" * 75)

    if total_failed == 0 and total_errors == 0 and total_run >= 127:
        print("\033[1;92m✔ ALL E2E TESTS PASSED SUCCESSFULLY! Exit code: 0\033[0m\n")
        sys.exit(0)
    else:
        print(f"\033[1;91m✖ TEST SUITE FAILED ({total_failed} failures, {total_errors} errors, {total_run} tests run). Exit code: 1\033[0m\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
