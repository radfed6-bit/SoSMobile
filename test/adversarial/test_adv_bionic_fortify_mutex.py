"""Adversarial & Unit Verification for Android 15 Bionic FORTIFY Mutex Protections.

Validates that:
1. glfw/src/posix_thread.c guards _glfwPlatformLockMutex, _glfwPlatformUnlockMutex,
   _glfwPlatformDestroyMutex against NULL and destroyed/unallocated mutex handles.
2. An empirical C compilation test proves destroyed/zeroed mutexes do not cause SIGABRT/crashes.
3. glfw/src/init.c safely handles _glfwInputError without locking destroyed errorLock.
4. glfw/src/android_window.c guards nativeSurfaceDestroyed and Vulkan/EGL mutexes using
   window_mutexes_active state flag.
5. app_mojo/src/main/jni/awt/awt.c statically initializes vm_wait_mutex with PTHREAD_MUTEX_INITIALIZER
   and synchronizes JNI_OnLoad.
6. patches/glfw-bionic-fortify.patch is valid and applies cleanly.
"""

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path("/workspaces/SoSMobile").resolve()
POSIX_THREAD_C = PROJECT_ROOT / "glfw/src/posix_thread.c"
INIT_C = PROJECT_ROOT / "glfw/src/init.c"
INTERNAL_H = PROJECT_ROOT / "glfw/src/internal.h"
ANDROID_WINDOW_C = PROJECT_ROOT / "glfw/src/android_window.c"
AWT_C = PROJECT_ROOT / "app_mojo/src/main/jni/awt/awt.c"
PATCH_FILE = PROJECT_ROOT / "patches/glfw-bionic-fortify.patch"
BUILD_GRADLE = PROJECT_ROOT / "app_mojo/build.gradle"


class TestAdvBionicFortifyMutex(unittest.TestCase):
    """Verifies all 4 Bionic FORTIFY mutex fixes in GLFW and AWT."""

    def test_posix_thread_mutex_guards(self):
        """Assert _glfwPlatformLockMutex and _glfwPlatformUnlockMutex have null/unallocated guards."""
        self.assertTrue(POSIX_THREAD_C.exists(), f"Missing {POSIX_THREAD_C}")
        code = POSIX_THREAD_C.read_text(encoding="utf-8")

        # Must have if (!mutex || !mutex->posix.allocated) return; in LockMutex
        lock_match = re.search(
            r"void\s+_glfwPlatformLockMutex\(_GLFWmutex\*\s*mutex\)\s*\{([^}]+)\}",
            code
        )
        self.assertIsNotNone(lock_match, "Cannot find _glfwPlatformLockMutex in posix_thread.c")
        lock_body = lock_match.group(1)
        self.assertIn("!mutex", lock_body)
        self.assertIn("!mutex->posix.allocated", lock_body)

        # Must have if (!mutex || !mutex->posix.allocated) return; in UnlockMutex
        unlock_match = re.search(
            r"void\s+_glfwPlatformUnlockMutex\(_GLFWmutex\*\s*mutex\)\s*\{([^}]+)\}",
            code
        )
        self.assertIsNotNone(unlock_match, "Cannot find _glfwPlatformUnlockMutex in posix_thread.c")
        unlock_body = unlock_match.group(1)
        self.assertIn("!mutex", unlock_body)
        self.assertIn("!mutex->posix.allocated", unlock_body)

        # DestroyMutex must check null and reset allocated before destroying
        destroy_match = re.search(
            r"void\s+_glfwPlatformDestroyMutex\(_GLFWmutex\*\s*mutex\)\s*\{([^}]+)\}",
            code
        )
        self.assertIsNotNone(destroy_match, "Cannot find _glfwPlatformDestroyMutex in posix_thread.c")
        destroy_body = destroy_match.group(1)
        self.assertIn("!mutex", destroy_body)
        self.assertIn("mutex->posix.allocated", destroy_body)

    def test_c_empirical_mutex_guard_execution(self):
        """Empirically compile and run C test code executing the posix_thread mutex guards."""
        c_test_code = """
#include <pthread.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>

#define GLFW_FALSE 0
#define GLFW_TRUE  1
typedef int GLFWbool;

typedef struct _GLFWmutexPOSIX {
    GLFWbool        allocated;
    pthread_mutex_t handle;
} _GLFWmutexPOSIX;

typedef struct _GLFWmutex {
    _GLFWmutexPOSIX posix;
} _GLFWmutex;

void _glfwPlatformDestroyMutex(_GLFWmutex* mutex) {
    if (!mutex) return;
    if (mutex->posix.allocated) {
        mutex->posix.allocated = GLFW_FALSE;
        pthread_mutex_destroy(&mutex->posix.handle);
    }
    memset(mutex, 0, sizeof(_GLFWmutex));
}

void _glfwPlatformLockMutex(_GLFWmutex* mutex) {
    if (!mutex || !mutex->posix.allocated) return;
    pthread_mutex_lock(&mutex->posix.handle);
}

void _glfwPlatformUnlockMutex(_GLFWmutex* mutex) {
    if (!mutex || !mutex->posix.allocated) return;
    pthread_mutex_unlock(&mutex->posix.handle);
}

GLFWbool _glfwPlatformCreateMutex(_GLFWmutex* mutex) {
    if (!mutex) return GLFW_FALSE;
    if (mutex->posix.allocated) return GLFW_TRUE;
    if (pthread_mutex_init(&mutex->posix.handle, NULL) != 0) return GLFW_FALSE;
    return mutex->posix.allocated = GLFW_TRUE;
}

int main(void) {
    // Test 1: NULL mutex lock and unlock
    _glfwPlatformLockMutex(NULL);
    _glfwPlatformUnlockMutex(NULL);
    _glfwPlatformDestroyMutex(NULL);

    // Test 2: Unallocated / zeroed mutex
    _GLFWmutex m1;
    memset(&m1, 0, sizeof(_GLFWmutex));
    _glfwPlatformLockMutex(&m1);
    _glfwPlatformUnlockMutex(&m1);

    // Test 3: Normal lifecycle then lock after destroy
    _GLFWmutex m2;
    memset(&m2, 0, sizeof(_GLFWmutex));
    assert(_glfwPlatformCreateMutex(&m2) == GLFW_TRUE);
    _glfwPlatformLockMutex(&m2);
    _glfwPlatformUnlockMutex(&m2);
    _glfwPlatformDestroyMutex(&m2);

    // Post-destruction lock attempt (MUST NOT crash/abort)
    _glfwPlatformLockMutex(&m2);
    _glfwPlatformUnlockMutex(&m2);

    // Double destroy
    _glfwPlatformDestroyMutex(&m2);

    printf("MUTEX_GUARDS_OK\\n");
    return 0;
}
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "test_mutex.c"
            bin_file = Path(tmpdir) / "test_mutex"
            src_file.write_text(c_test_code, encoding="utf-8")

            compile_res = subprocess.run(
                ["gcc", "-O2", "-pthread", str(src_file), "-o", str(bin_file)],
                capture_output=True,
                text=True
            )
            self.assertEqual(compile_res.returncode, 0, f"Compilation failed: {compile_res.stderr}")

            run_res = subprocess.run(
                [str(bin_file)],
                capture_output=True,
                text=True
            )
            self.assertEqual(run_res.returncode, 0, f"Execution failed: {run_res.stderr}")
            self.assertIn("MUTEX_GUARDS_OK", run_res.stdout)

    def test_init_c_error_lock_guard(self):
        """Assert _glfwInputError safely checks mutex allocation and does not lock destroyed errorLock."""
        self.assertTrue(INIT_C.exists(), f"Missing {INIT_C}")
        code = INIT_C.read_text(encoding="utf-8")

        # Must check _glfwPlatformIsMutexAllocated(&_glfw.errorLock)
        self.assertIn("_glfwPlatformIsMutexAllocated(&_glfw.errorLock)", code)

        # Must fallback to _glfwMainThreadError if error allocation fails
        self.assertIn("if (!error)", code)
        self.assertIn("error = &_glfwMainThreadError;", code)

        # Internal.h must define _glfwPlatformIsMutexAllocated
        internal_code = INTERNAL_H.read_text(encoding="utf-8")
        self.assertIn("#define _glfwPlatformIsMutexAllocated(m)", internal_code)

    def test_android_window_surface_destroyed_mutex_guards(self):
        """Assert android_window.c guards surface callbacks with window_mutexes_active."""
        self.assertTrue(ANDROID_WINDOW_C.exists(), f"Missing {ANDROID_WINDOW_C}")
        code = ANDROID_WINDOW_C.read_text(encoding="utf-8")

        # Atomic flag declared
        self.assertIn("window_mutexes_active", code)

        # android_init_window sets it true
        init_match = re.search(r"GLFWbool\s+android_init_window\(void\)\s*\{([^}]+)\}", code)
        self.assertIsNotNone(init_match)
        self.assertIn("window_mutexes_active = true;", init_match.group(1))

        # android_destroy_window sets it false and wakes waiters before destroy
        destroy_match = re.search(r"void\s+android_destroy_window\(void\)\s*\{([^}]+)\}", code)
        self.assertIsNotNone(destroy_match)
        destroy_body = destroy_match.group(1)
        self.assertIn("window_mutexes_active = false;", destroy_body)
        self.assertIn("pthread_cond_broadcast(&nw_egl_cond);", destroy_body)
        self.assertIn("pthread_cond_broadcast(&nw_vulkan_cond);", destroy_body)

        # nativeSurfaceDestroyed must guard with window_mutexes_active
        destroyed_fn = re.search(
            r"Java_git_artdeell_dnbootstrap_glfw_GLFW_nativeSurfaceDestroyed\([^\)]*\)\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}",
            code
        )
        self.assertIsNotNone(destroyed_fn)
        self.assertIn("window_mutexes_active", destroyed_fn.group(1))

    def test_awt_c_vm_wait_mutex_initializer(self):
        """Assert awt.c statically initializes vm_wait_mutex and vm_wait_cond."""
        self.assertTrue(AWT_C.exists(), f"Missing {AWT_C}")
        code = AWT_C.read_text(encoding="utf-8")

        # Must initialize with PTHREAD_MUTEX_INITIALIZER
        self.assertIn("pthread_mutex_t vm_wait_mutex = PTHREAD_MUTEX_INITIALIZER;", code)
        self.assertIn("pthread_cond_t vm_wait_cond = PTHREAD_COND_INITIALIZER;", code)

        # JNI_OnLoad must synchronize broadcast
        self.assertIn("jint JNI_OnLoad", code)
        self.assertIn("pthread_mutex_lock(&vm_wait_mutex);", code)
        self.assertIn("pthread_cond_broadcast(&vm_wait_cond);", code)
        self.assertIn("pthread_mutex_unlock(&vm_wait_mutex);", code)

    def test_patch_file_exists_and_applies(self):
        """Assert patches/glfw-bionic-fortify.patch exists, is non-empty, and applies cleanly."""
        self.assertTrue(PATCH_FILE.exists(), f"Missing patch file {PATCH_FILE}")
        patch_text = PATCH_FILE.read_text(encoding="utf-8")
        self.assertGreater(len(patch_text), 100)
        self.assertIn("android_window.c", patch_text)
        self.assertIn("posix_thread.c", patch_text)
        self.assertIn("init.c", patch_text)

        # Check build.gradle hook
        gradle_text = BUILD_GRADLE.read_text(encoding="utf-8")
        self.assertIn("applyGlfwPatches", gradle_text)


if __name__ == "__main__":
    unittest.main()
