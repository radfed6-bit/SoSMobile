"""Tier 5: Adversarial Stress Testing - SELinux W^X Restrictions & Process Execution Hooks.

Stress-tests OpenJDK process execution hooks, POSIX permission failures (error=13),
SELinux W^X bypass emulation, and discrimination between 'java' and non-java processes.
"""

import unittest
from pathlib import Path

from ..common.env import JAVA_EXEC_HOOKS
from ..common.simulators import MockProcessExecution
from ..common.assertions import assert_file_exists


class TestAdversarialSELinuxProcessExec(unittest.TestCase):
    """Stress testing suite for SELinux W^X constraints and process execution interception."""

    def test_adv_01_unhooked_binary_without_exec_permission_fails_with_error_13(self):
        """Binary without 0o111 executable permissions returns error=13 Permission denied."""
        res = MockProcessExecution.simulate_exec("/data/user/0/app/bin/java", mode=0o644, is_hooked=False)
        self.assertEqual(res["exit_code"], 13)
        self.assertEqual(res["status"], "EACCES")
        self.assertIn("error=13", res["error"])
        self.assertIn("Permission denied", res["error"])

    def test_adv_02_hooked_java_binary_intercepts_selinux_failure(self):
        """Hooked java binary clears pending exception and returns pid 0 on W^X failure."""
        res = MockProcessExecution.simulate_exec("/data/user/0/app/runtimes/Internal/bin/java", mode=0o644, is_hooked=True)
        self.assertEqual(res["exit_code"], 0)
        self.assertEqual(res["status"], "SUCCESS_HOOKED")
        self.assertIsNone(res["error"])

    def test_adv_03_hook_only_intercepts_java_and_not_arbitrary_binaries(self):
        """Hook does not mask errors for non-java executables (e.g. scripts or utilities)."""
        non_java_binaries = [
            "/data/user/0/app/bin/tar",
            "/data/user/0/app/bin/sh",
            "/data/user/0/app/bin/custom_tool",
            "python3",
            "some_binary"
        ]
        for bin_path in non_java_binaries:
            with self.subTest(binary=bin_path):
                res = MockProcessExecution.simulate_exec(bin_path, mode=0o644, is_hooked=True)
                self.assertEqual(res["exit_code"], 13, f"Non-java binary {bin_path} should fail with 13")
                self.assertEqual(res["status"], "EACCES")
                self.assertIsNotNone(res["error"])

    def test_adv_04_direct_exec_with_correct_permissions_succeeds(self):
        """Direct execution of binary with 0o755 permissions succeeds."""
        res = MockProcessExecution.simulate_exec("/data/user/0/app/bin/java", mode=0o755, is_hooked=False)
        self.assertEqual(res["exit_code"], 0)
        self.assertEqual(res["status"], "SUCCESS_DIRECT")
        self.assertIsNone(res["error"])

    def test_adv_05_c_source_java_exec_hook_implementation_audit(self):
        """Verify java_exec_hooks.c implements basename check, exception clearing, and dummy fds."""
        assert_file_exists(JAVA_EXEC_HOOKS)
        code = JAVA_EXEC_HOOKS.read_text(encoding="utf-8")

        # 1. Intercepts basename "java"
        self.assertIn('strcmp(prog_basename, "java") == 0', code)

        # 2. Checks and clears Java exception
        self.assertIn('(*env)->ExceptionCheck(env)', code)
        self.assertIn('(*env)->ExceptionClear(env)', code)

        # 3. Sets dummy file descriptors {-1, -1, -1}
        self.assertIn('jint dummy_fds[3] = {-1, -1, -1};', code)
        self.assertIn('(*env)->SetIntArrayRegion(env, std_fds, 0, 3, dummy_fds);', code)

        # 4. Returns 0 to indicate fallback success
        self.assertIn('return 0;', code)


if __name__ == "__main__":
    unittest.main()
