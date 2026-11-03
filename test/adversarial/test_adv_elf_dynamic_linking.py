"""Tier 5 Adversarial Test: Native ELF Dynamic Linking & LWJGL 3 Resolution

Adversarially tests ELF dynamic linking structure, symbol resolution,
architecture constraints, and runtime library resolution for liblwjgl.so.
"""

import os
import struct
import subprocess
import unittest
import zipfile
from pathlib import Path

PROJECT_ROOT = Path("/workspaces/SoSMobile").resolve()
LIBLWJGL_PATH = PROJECT_ROOT / "app_mojo/src/main/jniLibs/arm64-v8a/liblwjgl.so"
APK_PATH = PROJECT_ROOT / "app_mojo/build/outputs/apk/full/debug/app_mojo-full-debug.apk"
SYX_LAUNCH_CONFIG = PROJECT_ROOT / "app_mojo/src/main/java/git/artdeell/mojo/launch/SyxLaunchConfig.java"
GAME_RUNNER = PROJECT_ROOT / "app_mojo/src/main/java/git/artdeell/mojo/utils/jre/GameRunner.java"


class TestAdvElfDynamicLinking(unittest.TestCase):
    """Adversarial validation of liblwjgl.so ELF binary and runtime linking."""

    def test_elf_header_structure_arm64(self):
        """Empirically inspect raw ELF64 header fields of liblwjgl.so."""
        self.assertTrue(LIBLWJGL_PATH.exists(), f"Missing binary at {LIBLWJGL_PATH}")
        data = LIBLWJGL_PATH.read_bytes()
        self.assertGreaterEqual(len(data), 64, "Binary too small for ELF64 header")

        # 0x00..0x03: e_ident[EI_MAG0..EI_MAG3]
        magic = data[0:4]
        self.assertEqual(magic, b"\x7fELF", "Invalid ELF magic")

        # 0x04: e_ident[EI_CLASS] (1=32bit, 2=64bit)
        ei_class = data[4]
        self.assertEqual(ei_class, 2, "liblwjgl.so must be ELFCLASS64")

        # 0x05: e_ident[EI_DATA] (1=little endian, 2=big endian)
        ei_data = data[5]
        self.assertEqual(ei_data, 1, "liblwjgl.so must be 2's complement, little endian (ELFDATA2LSB)")

        # 0x06: e_ident[EI_VERSION]
        ei_version = data[6]
        self.assertEqual(ei_version, 1, "ELF version must be 1")

        # 0x07: e_ident[EI_OSABI] (0=UNIX System V)
        ei_osabi = data[7]
        self.assertEqual(ei_osabi, 0, "ELF OS/ABI must be UNIX System V (0)")

        # 0x10..0x11: e_type (3=ET_DYN shared object)
        e_type = struct.unpack("<H", data[16:18])[0]
        self.assertEqual(e_type, 3, "ELF type must be ET_DYN (Shared object file)")

        # 0x12..0x13: e_machine (183 / 0xb7 = EM_AARCH64)
        e_machine = struct.unpack("<H", data[18:20])[0]
        self.assertEqual(e_machine, 183, "ELF machine must be EM_AARCH64 (183 / 0xb7)")

    def test_dynamic_dependencies_needed(self):
        """Verify dynamic section dependencies (DT_NEEDED) via readelf."""
        res = subprocess.run(
            ["readelf", "-d", str(LIBLWJGL_PATH)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        output = res.stdout

        # Extract all (NEEDED) lines
        needed_libs = []
        for line in output.splitlines():
            if "(NEEDED)" in line and "Shared library:" in line:
                start = line.find("[") + 1
                end = line.find("]")
                if start > 0 and end > start:
                    needed_libs.append(line[start:end])

        # Assert Android Bionic compatible dependencies
        self.assertIn("libc.so", needed_libs, "liblwjgl.so must depend on libc.so")
        self.assertIn("libdl.so", needed_libs, "liblwjgl.so must depend on libdl.so")

        # Assert no unexpected external shared libs (which would cause UnsatisfiedLinkError on mobile)
        allowed_libs = {"libc.so", "libdl.so", "libm.so"}
        unexpected = set(needed_libs) - allowed_libs
        self.assertEqual(len(unexpected), 0, f"Unexpected DT_NEEDED libraries in liblwjgl.so: {unexpected}")

    def test_exported_dynamic_symbols(self):
        """Assert required LWJGL 3 JNI symbols are exported in dynamic symbol table."""
        res = subprocess.run(
            ["nm", "-D", str(LIBLWJGL_PATH)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        symbols = res.stdout

        required_symbols = [
            "Java_org_lwjgl_system_linux_DynamicLinkLoader_ndlopen",
            "Java_org_lwjgl_system_linux_DynamicLinkLoader_ndlsym",
            "Java_org_lwjgl_system_linux_DynamicLinkLoader_ndlclose",
            "Java_org_lwjgl_system_linux_DynamicLinkLoader_ndlerror",
        ]

        for sym in required_symbols:
            self.assertIn(sym, symbols, f"Required dynamic symbol '{sym}' missing from liblwjgl.so")

    def test_apk_contains_bundled_arm64_library(self):
        """Verify the assembled debug APK bundles lib/arm64-v8a/liblwjgl.so."""
        self.assertTrue(APK_PATH.exists(), f"Missing APK at {APK_PATH}")
        with zipfile.ZipFile(APK_PATH, "r") as zf:
            namelist = zf.namelist()
            self.assertIn("lib/arm64-v8a/liblwjgl.so", namelist,
                          "APK must package lib/arm64-v8a/liblwjgl.so")
            info = zf.getinfo("lib/arm64-v8a/liblwjgl.so")
            self.assertEqual(info.file_size, LIBLWJGL_PATH.stat().st_size,
                             "Packaged liblwjgl.so size must match source file exactly")

            # Also verify gl4es is packaged
            self.assertIn("lib/arm64-v8a/libgl4es_114.so", namelist,
                          "APK must package lib/arm64-v8a/libgl4es_114.so")

    def test_jvm_launch_property_configuration(self):
        """Verify SyxLaunchConfig and GameRunner properly inject -Dorg.lwjgl.librarypath."""
        cfg_content = SYX_LAUNCH_CONFIG.read_text(encoding="utf-8")
        self.assertIn('sysProps.put("org.lwjgl.librarypath", appNativeDir)', cfg_content,
                      "SyxLaunchConfig must inject org.lwjgl.librarypath system property")
        self.assertIn('"-Dorg.lwjgl.librarypath=" + appNativeDir', cfg_content,
                      "SyxLaunchConfig must pass -Dorg.lwjgl.librarypath in JVM arguments")

        gr_content = GAME_RUNNER.read_text(encoding="utf-8")
        self.assertIn('"-Dorg.lwjgl.librarypath="', gr_content,
                      "GameRunner must configure -Dorg.lwjgl.librarypath")
        self.assertIn("Tools.NATIVE_LIB_DIR", gr_content,
                      "GameRunner must include Tools.NATIVE_LIB_DIR in org.lwjgl.librarypath")


if __name__ == "__main__":
    unittest.main()
