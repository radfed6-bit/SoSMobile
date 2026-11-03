"""Tier 1: Feature Baseline Coverage - F2: Runtime Binary Execution & Permissions

Verifies that runtime binary permissions are preserved (mode 0755), setExecutable
is called, and java_exec_hooks.c handles java execution to prevent error=13 Permission denied.
"""

import unittest
from pathlib import Path

from ..common.env import (
    MULTI_RT_UTILS,
    JAVA_EXEC_HOOKS,
)
from ..common.assertions import (
    assert_file_exists,
    assert_file_contains_regex,
)
from ..common.simulators import MockProcessExecution


class TestF2RuntimePermissions(unittest.TestCase):
    """Test suite verifying F2 binary execution & permissions remediation."""

    def test_f2_01_tar_extractor_preserves_mode(self):
        """Assert uncompressTarXZ preserves POSIX mode from tar entry."""
        assert_file_exists(MULTI_RT_UTILS)
        content = MULTI_RT_UTILS.read_text(encoding="utf-8")
        # Should reference getMode() or setExecutable / chmod in tar extraction
        self.assertTrue(
            ("getMode" in content or "setExecutable" in content or "chmod" in content),
            "MultiRTUtils.uncompressTarXZ must preserve POSIX mode or set executable permissions"
        )

    def test_f2_02_post_prepare_sets_executable(self):
        """Assert postPrepare sets executable permissions on bin binaries."""
        assert_file_exists(MULTI_RT_UTILS)
        content = MULTI_RT_UTILS.read_text(encoding="utf-8")
        # postPrepare must ensure executable permissions
        self.assertRegex(
            content,
            r"setExecutable\s*\(\s*true\s*,\s*false\s*\)",
            "MultiRTUtils.postPrepare must call setExecutable(true, false) on runtime binaries"
        )

    def test_f2_03_java_exec_hooks_handles_java(self):
        """Assert java_exec_hooks.c intercepts 'java' to avoid W^X EACCES."""
        assert_file_exists(JAVA_EXEC_HOOKS)
        content = JAVA_EXEC_HOOKS.read_text(encoding="utf-8")
        # hooked_ProcessImpl_forkAndExec must handle "java"
        self.assertTrue(
            '"java"' in content or 'strcmp(prog_basename, "java")' in content,
            "java_exec_hooks.c must contain logic handling the 'java' executable"
        )

    def test_f2_04_process_exec_simulation_with_executable_permission(self):
        """Verify simulated execution succeeds when mode has 0755 executable bits."""
        result = MockProcessExecution.simulate_exec("/data/user/0/runtimes/bin/java", mode=0o755, is_hooked=False)
        self.assertEqual(result["exit_code"], 0)
        self.assertIsNone(result["error"])

    def test_f2_05_process_exec_simulation_hook_mitigation(self):
        """Verify simulated execution succeeds via hook even under restricted SELinux/W^X."""
        result = MockProcessExecution.simulate_exec("/data/user/0/runtimes/bin/java", mode=0o644, is_hooked=True)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["status"], "SUCCESS_HOOKED")


if __name__ == "__main__":
    unittest.main()
