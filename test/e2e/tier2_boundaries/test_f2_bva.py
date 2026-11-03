"""Tier 2: Boundary Value Analysis - F2: Runtime Binary Execution & Permissions

Verifies boundary conditions for POSIX file permissions, mode masks,
and process execution interception under simulated SELinux/W^X environments.
"""

import unittest
from ..common.simulators import MockProcessExecution
from ..common.env import JAVA_EXEC_HOOKS
from ..common.assertions import assert_file_exists


class TestF2BVA(unittest.TestCase):
    """BVA test suite for F2 binary execution & permissions."""

    def test_f2_bva_01_mode_zero_binary_exec_failure(self):
        """Assert mode 0000 fails with EACCES error=13 when not hooked."""
        res = MockProcessExecution.simulate_exec("/data/user/0/bin/java", mode=0o000, is_hooked=False)
        self.assertEqual(res["exit_code"], 13)
        self.assertEqual(res["status"], "EACCES")
        self.assertIn("error=13", res["error"])

    def test_f2_bva_02_mode_644_read_only_failure(self):
        """Assert mode 0644 (rw-r--r--) lacks execute bits and fails without hook."""
        res = MockProcessExecution.simulate_exec("/data/user/0/bin/java", mode=0o644, is_hooked=False)
        self.assertEqual(res["exit_code"], 13)
        self.assertEqual(res["status"], "EACCES")

    def test_f2_bva_03_non_java_binary_unhooked_exec(self):
        """Assert non-java binaries (e.g. ffmpeg or utility) with 0755 execute directly."""
        res = MockProcessExecution.simulate_exec("/data/user/0/bin/custom_tool", mode=0o755, is_hooked=True)
        self.assertEqual(res["exit_code"], 0)
        self.assertEqual(res["status"], "SUCCESS_DIRECT")

    def test_f2_bva_04_java_exec_hook_structure(self):
        """Assert java_exec_hooks.c includes hooked_ProcessImpl_forkAndExec implementation."""
        assert_file_exists(JAVA_EXEC_HOOKS)
        content = JAVA_EXEC_HOOKS.read_text(encoding="utf-8")
        self.assertIn("hooked_ProcessImpl_forkAndExec", content)
        self.assertIn("orig_ProcessImpl_forkAndExec", content)

    def test_f2_bva_05_hook_intercepts_java_under_unexecutable_mode(self):
        """Assert hooked execution safely handles unexecutable java binary."""
        res = MockProcessExecution.simulate_exec("/data/user/0/runtimes/jre17/bin/java", mode=0o444, is_hooked=True)
        self.assertEqual(res["exit_code"], 0)
        self.assertEqual(res["status"], "SUCCESS_HOOKED")


if __name__ == "__main__":
    unittest.main()
