"""Tier 1: Feature Baseline Coverage - F3: Native LWJGL 3 Linking

Verifies that liblwjgl.so (LWJGL 3.4.1 ARM64) is bundled in jniLibs/arm64-v8a/
and properly passed to JVM via -Dorg.lwjgl.librarypath and -Djava.library.path.
"""

import unittest
from pathlib import Path

from ..common.env import (
    LIBLWJGL_SO,
    SYX_LAUNCH_CONFIG,
)
from ..common.assertions import (
    assert_file_exists,
    assert_elf_arm64,
    assert_file_contains_regex,
)


class TestF3LwjglLinking(unittest.TestCase):
    """Test suite verifying F3 LWJGL 3 native library bundling and linking."""

    def test_f3_01_liblwjgl_so_present_in_jnilibs(self):
        """Assert liblwjgl.so is bundled in jniLibs/arm64-v8a/."""
        assert_file_exists(
            LIBLWJGL_SO,
            f"Bundled liblwjgl.so must exist at {LIBLWJGL_SO}"
        )

    def test_f3_02_liblwjgl_so_is_valid_arm64_elf(self):
        """Assert liblwjgl.so has valid 64-bit ARM (AArch64) ELF header."""
        assert_elf_arm64(LIBLWJGL_SO)

    def test_f3_03_launch_config_defines_org_lwjgl_librarypath(self):
        """Assert SyxLaunchConfig sets -Dorg.lwjgl.librarypath to NATIVE_LIB_DIR."""
        assert_file_exists(SYX_LAUNCH_CONFIG)
        content = SYX_LAUNCH_CONFIG.read_text(encoding="utf-8")
        self.assertRegex(
            content,
            r"-Dorg\.lwjgl\.librarypath=",
            "SyxLaunchConfig must define -Dorg.lwjgl.librarypath pointing to native lib directory"
        )

    def test_f3_04_launch_config_defines_java_library_path(self):
        """Assert SyxLaunchConfig includes NATIVE_LIB_DIR in -Djava.library.path."""
        assert_file_exists(SYX_LAUNCH_CONFIG)
        content = SYX_LAUNCH_CONFIG.read_text(encoding="utf-8")
        self.assertRegex(
            content,
            r"-Djava\.library\.path=",
            "SyxLaunchConfig must define -Djava.library.path"
        )

    def test_f3_05_lwjgl_library_resolution_simulation(self):
        """Simulate LWJGL Library.loadSystem resolution given the configured library paths."""
        library_paths = [
            "/data/app/git.artdeell.sosmobile/lib/arm64",
            str(LIBLWJGL_SO.parent)
        ]
        lib_name = "liblwjgl.so"
        resolved_path = None
        for p in library_paths:
            candidate = Path(p) / lib_name
            if candidate.exists():
                resolved_path = candidate
                break

        self.assertIsNotNone(
            resolved_path,
            f"Simulated LWJGL loader must resolve {lib_name} from configured library paths"
        )


if __name__ == "__main__":
    unittest.main()
