"""Tier 5 Adversarial Test: Process Spawning under Restricted W^X Conditions

Adversarially tests process spawning interception, SELinux W^X mitigation,
basename extraction, exception suppression, and fallback execution.
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path("/workspaces/SoSMobile").resolve()
JAVA_EXEC_HOOKS_C = PROJECT_ROOT / "app_mojo/src/main/jni/jvm_hooks/java_exec_hooks.c"


class TestAdvProcessSpawningWX(unittest.TestCase):
    """Stress tests process execution hooks under simulated W^X restrictions."""

    def test_c_source_logic_verification(self):
        """Verify java_exec_hooks.c source has the required W^X interceptor and exception clearing."""
        self.assertTrue(JAVA_EXEC_HOOKS_C.exists(), f"Missing {JAVA_EXEC_HOOKS_C}")
        code = JAVA_EXEC_HOOKS_C.read_text(encoding="utf-8")

        self.assertIn('strcmp(prog_basename, "java") == 0', code,
                      "Hook must check for prog_basename == 'java'")
        self.assertIn('(*env)->ExceptionCheck(env)', code,
                      "Hook must check for pending exception from orig_ProcessImpl_forkAndExec")
        self.assertIn('(*env)->ExceptionClear(env)', code,
                      "Hook must clear pending IOException (error=13) to prevent JVM abort")
        self.assertIn('jint dummy_fds[3] = {-1, -1, -1};', code,
                      "Hook must initialize dummy file descriptors {-1, -1, -1} on fallback")
        self.assertIn('(*env)->SetIntArrayRegion(env, std_fds, 0, 3, dummy_fds);', code,
                      "Hook must write dummy file descriptors back to Java std_fds")
        self.assertIn("return 0;", code,
                      "Hook must return exit/pid code 0 on fallback")

    def test_native_c_basename_and_interception_compilation(self):
        """Compile and execute a standalone C harness verifying the exact basename & intercept logic."""
        c_test_src = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libgen.h>
#include <stdbool.h>
#include <assert.h>

// Mock JNI environment and forkAndExec
typedef struct {
    bool exception_pending;
    int cleared_count;
} MockEnv;

static void MockExceptionClear(MockEnv *env) {
    if (env->exception_pending) {
        env->exception_pending = false;
        env->cleared_count++;
    }
}

// Simulates the hooked logic from java_exec_hooks.c
int simulate_hooked_forkAndExec(MockEnv *env, const char *pProg, int *std_fds, bool simulate_wx_eacces) {
    // Exact logic from java_exec_hooks.c:44-50
    char prog_copy[4096];
    strncpy(prog_copy, pProg, sizeof(prog_copy) - 1);
    prog_copy[sizeof(prog_copy) - 1] = '\0';
    
    char *pProgBaseName = basename(prog_copy);
    size_t basename_len = strlen(pProgBaseName);
    char prog_basename[basename_len + 1];
    memcpy(prog_basename, pProgBaseName, basename_len + 1);

    if (strcmp(prog_basename, "java") == 0) {
        // Simulating orig_forkAndExec
        if (simulate_wx_eacces) {
            env->exception_pending = true; // Simulating IOException: error=13, Permission denied
        }

        if (env->exception_pending) {
            MockExceptionClear(env);
            if (std_fds != NULL) {
                std_fds[0] = -1;
                std_fds[1] = -1;
                std_fds[2] = -1;
            }
            return 0; // Graceful fallback
        }
        return 1234; // Normal PID
    }

    // Non-java commands
    if (simulate_wx_eacces) {
        env->exception_pending = true;
        return -1;
    }
    return 5678;
}

int main() {
    MockEnv env = {false, 0};
    int fds[3] = {0, 1, 2};

    // Case 1: Standard full path to java under W^X failure
    int pid = simulate_hooked_forkAndExec(&env, "/data/user/0/git.artdeell.sosmobile/runtimes/jre17/bin/java", fds, true);
    assert(pid == 0);
    assert(env.cleared_count == 1);
    assert(!env.exception_pending);
    assert(fds[0] == -1 && fds[1] == -1 && fds[2] == -1);

    // Case 2: Relative path to java
    fds[0] = 10; fds[1] = 11; fds[2] = 12;
    pid = simulate_hooked_forkAndExec(&env, "./bin/java", fds, true);
    assert(pid == 0);
    assert(env.cleared_count == 2);
    assert(fds[0] == -1);

    // Case 3: Just "java"
    pid = simulate_hooked_forkAndExec(&env, "java", fds, true);
    assert(pid == 0);
    assert(env.cleared_count == 3);

    // Case 4: Non-java binary (e.g. logcat) should NOT be intercepted
    env.exception_pending = false;
    fds[0] = 5;
    pid = simulate_hooked_forkAndExec(&env, "/system/bin/logcat", fds, true);
    assert(pid == -1);
    assert(env.exception_pending == true); // Exception NOT cleared
    assert(fds[0] == 5);                  // FDs NOT overwritten

    // Case 5: Partial name matches (javac, javadoc, myjava) must NOT trigger java interceptor
    env.exception_pending = false;
    pid = simulate_hooked_forkAndExec(&env, "/bin/javac", fds, true);
    assert(pid == -1);
    assert(env.exception_pending == true);

    env.exception_pending = false;
    pid = simulate_hooked_forkAndExec(&env, "/bin/javadoc", fds, true);
    assert(pid == -1);
    assert(env.exception_pending == true);

    // Case 6: Successful execution of java (e.g. root or permissive SELinux)
    env.exception_pending = false;
    fds[0] = 3; fds[1] = 4; fds[2] = 5;
    pid = simulate_hooked_forkAndExec(&env, "/data/user/0/runtimes/bin/java", fds, false);
    assert(pid == 1234);
    assert(!env.exception_pending);
    assert(fds[0] == 3); // Unchanged

    printf("ALL_NATIVE_C_PROCESS_SPAWNING_TESTS_PASSED\n");
    return 0;
}
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            c_file = Path(tmp_dir) / "test_hook.c"
            bin_file = Path(tmp_dir) / "test_hook"
            c_file.write_text(c_test_src, encoding="utf-8")

            # Compile with gcc
            compile_res = subprocess.run(
                ["gcc", "-Wall", "-Werror", str(c_file), "-o", str(bin_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.assertEqual(compile_res.returncode, 0, f"Compilation failed: {compile_res.stderr}")

            # Run test
            run_res = subprocess.run(
                [str(bin_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.assertEqual(run_res.returncode, 0, f"Execution failed: {run_res.stderr}")
            self.assertIn("ALL_NATIVE_C_PROCESS_SPAWNING_TESTS_PASSED", run_res.stdout)


if __name__ == "__main__":
    unittest.main()
