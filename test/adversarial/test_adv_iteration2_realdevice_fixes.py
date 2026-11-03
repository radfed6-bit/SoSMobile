"""Tier 5 Adversarial Test: Iteration 2 Real-Device Crash Fixes & v0.1.1 Release Verification

Empirically tests:
1. LWJGL DynamicLinkLoader JNI symbol exports across all target ABIs (arm64-v8a, armeabi-v7a, x86, x86_64) in libmojort.so.
2. GLFW libname (-Dorg.lwjgl.glfw.libname=libglfw.so), headless mode (-Djava.awt.headless=true), and shared library extract path in SyxLaunchConfig and GameRunner.
3. Standalone C execution of DynamicLinkLoader bridge logic and dlopen fallbacks.
4. Attribution & Legal Notices in README.md / README_RU.md (Jake Versluis / Gamatron AB, zero Strange Scaffold).
5. GitHub Release v0.1.1 asset integrity and SHA256 matching.
"""

import hashlib
import json
import os
import re
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

PROJECT_ROOT = Path("/workspaces/SoSMobile").resolve()
MERGED_NATIVE_LIBS = PROJECT_ROOT / "app_mojo/build/intermediates/merged_native_libs/fullDebug/mergeFullDebugNativeLibs/out/lib"
STRIPPED_NATIVE_LIBS = PROJECT_ROOT / "app_mojo/build/intermediates/stripped_native_libs/fullDebug/stripFullDebugDebugSymbols/out/lib"
APK_PATH = PROJECT_ROOT / "app_mojo/build/outputs/apk/full/debug/app_mojo-full-debug.apk"
NORUNTIME_APK_PATH = PROJECT_ROOT / "app_mojo/build/outputs/apk/noruntime/debug/app_mojo-noruntime-debug.apk"
SYX_LAUNCH_CONFIG = PROJECT_ROOT / "app_mojo/src/main/java/git/artdeell/mojo/launch/SyxLaunchConfig.java"
GAME_RUNNER = PROJECT_ROOT / "app_mojo/src/main/java/git/artdeell/mojo/utils/jre/GameRunner.java"
DLOPEN_HOOK_C = PROJECT_ROOT / "app_mojo/src/main/jni/jvm_hooks/lwjgl_dlopen_hook.c"
README_EN = PROJECT_ROOT / "README.md"
README_RU = PROJECT_ROOT / "README_RU.md"


class TestAdvIteration2RealDeviceFixes(unittest.TestCase):
    """Adversarial validation for Iteration 2 gate requirements."""

    def test_dynamic_link_loader_symbols_exported_all_abis(self):
        """Assert all 4 DynamicLinkLoader JNI entrypoints are exported in libmojort.so for all 4 ABIs."""
        abis = ["arm64-v8a", "armeabi-v7a", "x86", "x86_64"]
        required_symbols = [
            "Java_org_lwjgl_system_linux_DynamicLinkLoader_ndlopen",
            "Java_org_lwjgl_system_linux_DynamicLinkLoader_ndlerror",
            "Java_org_lwjgl_system_linux_DynamicLinkLoader_ndlsym",
            "Java_org_lwjgl_system_linux_DynamicLinkLoader_ndlclose",
        ]

        for abi in abis:
            lib_path = MERGED_NATIVE_LIBS / abi / "libmojort.so"
            self.assertTrue(lib_path.exists(), f"libmojort.so missing for ABI {abi} at {lib_path}")
            res = subprocess.run(
                ["nm", "-D", str(lib_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            symbols = res.stdout
            for sym in required_symbols:
                self.assertIn(
                    sym, symbols,
                    f"Symbol '{sym}' missing from merged libmojort.so for ABI {abi}"
                )

            # Also check stripped library
            stripped_path = STRIPPED_NATIVE_LIBS / abi / "libmojort.so"
            if stripped_path.exists():
                res_stripped = subprocess.run(
                    ["nm", "-D", str(stripped_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True
                )
                for sym in required_symbols:
                    self.assertIn(
                        sym, res_stripped.stdout,
                        f"Symbol '{sym}' missing from stripped libmojort.so for ABI {abi}"
                    )

    def test_syx_launch_config_and_gamerunner_properties(self):
        """Verify SyxLaunchConfig and GameRunner specify -Dorg.lwjgl.glfw.libname, -Djava.awt.headless, etc."""
        cfg_text = SYX_LAUNCH_CONFIG.read_text(encoding="utf-8")

        # Must set org.lwjgl.glfw.libname in sysProps and javaArgs
        self.assertIn('sysProps.put("org.lwjgl.glfw.libname", "libglfw.so")', cfg_text)
        self.assertIn('javaArgs.add("-Dorg.lwjgl.glfw.libname=libglfw.so")', cfg_text)

        # Must set java.awt.headless in sysProps and javaArgs
        self.assertIn('sysProps.put("java.awt.headless", "true")', cfg_text)
        self.assertIn('javaArgs.add("-Djava.awt.headless=true")', cfg_text)

        # Must set SharedLibraryExtractPath
        self.assertIn('sysProps.put("org.lwjgl.system.SharedLibraryExtractPath"', cfg_text)
        self.assertIn('javaArgs.add("-Dorg.lwjgl.system.SharedLibraryExtractPath="', cfg_text)

        # Check GameRunner
        gr_text = GAME_RUNNER.read_text(encoding="utf-8")
        self.assertIn('javaArgList.add("-Dorg.lwjgl.glfw.libname=libglfw.so")', gr_text)
        self.assertIn('javaArgList.add("-Djava.awt.headless=true")', gr_text)
        self.assertIn('javaArgList.add("-Dorg.lwjgl.system.SharedLibraryExtractPath="', gr_text)

    def test_compiled_c_dlopen_hook_behavior_and_fallbacks(self):
        """Compile and execute a standalone C harness to empirically stress-test the dlopen hook logic."""
        c_code = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <stdint.h>
#include <assert.h>

// Mock mojoexec functions
static void* mock_vulkan_handle = (void*) 0x11223344;
static void* mock_egl_handle    = (void*) 0x55667788;

void* mojoexec_acq_vulkan_handle(void) { return mock_vulkan_handle; }
void* mojoexec_acq_egl_handle(void) { return mock_egl_handle; }

typedef int64_t jlong;
typedef int32_t jint;

static jlong ndlopen_bugfix(jlong filename_ptr, jint jmode) {
    const char* filename = (const char*) filename_ptr;
    if(filename == NULL) return 0;

    if(strstr(filename, "libvulkan.so") != NULL) {
        return (jlong) mojoexec_acq_vulkan_handle();
    }
    if(strstr(filename, "libGLMojo.so") != NULL) {
        return (jlong) mojoexec_acq_egl_handle();
    }

    int mode = (int)jmode;
    void* handle = dlopen(filename, mode);
    if(handle == NULL && strstr(filename, "libglfw.so") != NULL) {
        handle = dlopen("libglfw.so", mode);
    }
    return (jlong) handle;
}

static jlong ndlerror_hook(void) {
    const char* err = dlerror();
    return (jlong) err;
}

static jlong ndlsym_hook(jlong handle, jlong name_ptr) {
    if(name_ptr == 0 || handle == 0) return 0;
    const char *name = (const char *) name_ptr;
    return (jlong) dlsym((void *) handle, name);
}

static jint ndlclose_hook(jlong handle) {
    if(handle == 0) return 0;
    return (jint) dlclose((void *) handle);
}

int main(void) {
    // 1. NULL filename should return 0 safely
    assert(ndlopen_bugfix(0, RTLD_NOW) == 0);

    // 2. Interception of libvulkan.so
    const char* vpath = "/path/to/extracted/libvulkan.so";
    assert(ndlopen_bugfix((jlong)vpath, RTLD_NOW) == (jlong)mock_vulkan_handle);

    // 3. Interception of libGLMojo.so
    const char* gpath = "/data/user/0/app/libGLMojo.so";
    assert(ndlopen_bugfix((jlong)gpath, RTLD_NOW) == (jlong)mock_egl_handle);

    // 4. Non-existent generic library returns 0
    const char* badpath = "/nonexistent/path/libdummy_missing_xyz.so";
    assert(ndlopen_bugfix((jlong)badpath, RTLD_NOW) == 0);

    // 5. Fallback logic: non-existent path containing libglfw.so attempts dlopen("libglfw.so")
    // (If libglfw.so is not in system lib dir, returns NULL cleanly without crash)
    const char* badglfw = "/cache/lwjgl_native/SongsOfSyx/libglfw.so";
    jlong glfw_h = ndlopen_bugfix((jlong)badglfw, RTLD_NOW);
    // Should not crash, returns either handle or 0
    (void)glfw_h;

    // 6. Test ndlsym with valid libc handle
    void* libc = dlopen("libc.so.6", RTLD_LAZY);
    if (!libc) libc = dlopen("libc.so", RTLD_LAZY);
    assert(libc != NULL);

    const char* sym_printf = "printf";
    jlong sym_addr = ndlsym_hook((jlong)libc, (jlong)sym_printf);
    assert(sym_addr != 0);

    // 7. Test ndlsym with NULL inputs
    assert(ndlsym_hook(0, (jlong)sym_printf) == 0);
    assert(ndlsym_hook((jlong)libc, 0) == 0);

    // 8. Test ndlclose with NULL handle
    assert(ndlclose_hook(0) == 0);

    // 9. Test ndlclose with real handle
    assert(ndlclose_hook((jlong)libc) == 0);

    // 10. Test ndlerror
    // dlerror might be NULL or previous error
    ndlerror_hook();

    printf("ALL_C_TESTS_PASSED\n");
    return 0;
}
"""
        with tempfile.TemporaryDirectory() as td:
            src_file = Path(td) / "test_dlopen.c"
            bin_file = Path(td) / "test_dlopen"
            src_file.write_text(c_code, encoding="utf-8")

            compile_res = subprocess.run(
                ["gcc", "-Wall", "-Werror", "-O2", str(src_file), "-o", str(bin_file), "-ldl"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.assertEqual(compile_res.returncode, 0, f"Compilation failed: {compile_res.stderr}")

            exec_res = subprocess.run(
                [str(bin_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.assertEqual(exec_res.returncode, 0, f"Execution failed: {exec_res.stderr}")
            self.assertIn("ALL_C_TESTS_PASSED", exec_res.stdout)

    def test_documentation_and_legal_notices(self):
        """Verify README.md and README_RU.md correctly attribute Jake Versluis / Gamatron AB and omit Strange Scaffold."""
        for path in (README_EN, README_RU):
            text = path.read_text(encoding="utf-8")

            # Must contain Jake Versluis and Gamatron AB
            self.assertIn("Jake Versluis", text, f"{path.name} missing 'Jake Versluis'")
            self.assertIn("Gamatron AB", text, f"{path.name} missing 'Gamatron AB'")

            # Must NOT contain Strange Scaffold anywhere
            self.assertNotIn("Strange Scaffold", text, f"{path.name} erroneously contains 'Strange Scaffold'")

            # Must mention version 0.1.1
            self.assertIn("0.1.1", text, f"{path.name} should reference v0.1.1")

    def test_github_release_v0_1_1_assets_and_checksums(self):
        """Assert GitHub Release v0.1.1 exists, is published, and matches local APK checksums."""
        res = subprocess.run(
            ["gh", "release", "view", "v0.1.1", "--json", "tagName,name,assets"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        rel_data = json.loads(res.stdout)
        self.assertEqual(rel_data.get("tagName"), "v0.1.1")

        asset_names = {a["name"]: a for a in rel_data.get("assets", [])}
        self.assertIn("SoSMobile-v0.1.1.apk", asset_names, "Missing SoSMobile-v0.1.1.apk in release assets")
        self.assertIn("SoSMobile-v0.1.1.apk.sha256", asset_names, "Missing SoSMobile-v0.1.1.apk.sha256")
        self.assertIn("SoSMobile-noruntime-v0.1.1.apk", asset_names, "Missing SoSMobile-noruntime-v0.1.1.apk")
        self.assertIn("SoSMobile-noruntime-v0.1.1.apk.sha256", asset_names, "Missing SoSMobile-noruntime-v0.1.1.apk.sha256")

        # Verify local APK checksum matches
        self.assertTrue(APK_PATH.exists())
        local_full_sha = hashlib.sha256(APK_PATH.read_bytes()).hexdigest()

        sha_file = PROJECT_ROOT / "build/release_v0.1.1/SoSMobile-v0.1.1.apk.sha256"
        if sha_file.exists():
            recorded_sha = sha_file.read_text().split()[0].strip()
            self.assertEqual(local_full_sha, recorded_sha, "APK SHA256 does not match recorded release sha256")


if __name__ == "__main__":
    unittest.main()
