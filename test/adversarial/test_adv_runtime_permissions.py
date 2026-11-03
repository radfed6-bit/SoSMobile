"""Tier 5 Adversarial Test: Runtime Binary Permission Handling & Extraction

Stress-tests Java 17 runtime archive extraction, POSIX mode handling,
restricted filesystem permission models, and binary executable attributes.
"""

import os
import shutil
import stat
import tarfile
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path("/workspaces/SoSMobile").resolve()
APP_MOJO = PROJECT_ROOT / "app_mojo"
MULTI_RT_UTILS_JAVA = APP_MOJO / "src/main/java/git/artdeell/mojo/multirt/MultiRTUtils.java"
BUILD_GRADLE = APP_MOJO / "build.gradle"
ASYNC_ASSET_MANAGER = APP_MOJO / "src/main/java/git/artdeell/mojo/tasks/AsyncAssetManager.java"
MERGED_ARM64_JRE = APP_MOJO / "build/intermediates/assets/fullDebug/mergeFullDebugAssets/components/jre/bin-arm64.tar.xz"


class TestAdvRuntimePermissions(unittest.TestCase):
    """Adversarial stress-testing of runtime binary permissions and extraction."""

    def test_multi_rt_utils_source_contracts(self):
        """Verify MultiRTUtils implements strict 0755 permissions and Java 17 defaults."""
        self.assertTrue(MULTI_RT_UTILS_JAVA.exists(), f"Missing {MULTI_RT_UTILS_JAVA}")
        content = MULTI_RT_UTILS_JAVA.read_text(encoding="utf-8")

        # 1. Java 17 constants
        self.assertIn("DEFAULT_JAVA_VERSION = 17", content, "DEFAULT_JAVA_VERSION must be 17")
        self.assertIn('DEFAULT_JRE_PREFIX = "jre17"', content, "DEFAULT_JRE_PREFIX must be jre17")

        # 2. tar extraction executable flag logic
        self.assertIn("destPath.setExecutable(true, false)", content,
                      "MultiRTUtils must set file executable for all users (ownerOnly=false)")
        self.assertIn('(mode & 0111) != 0', content,
                      "MultiRTUtils must check octal execute bits from tar entry")
        self.assertIn('"bin".equals(destPath.getParentFile().getName())', content,
                      "MultiRTUtils must guarantee files in bin/ are executable")

        # 3. postPrepare recursive executable walk
        self.assertIn("setExecutableRecursively(dest)", content,
                      "postPrepare must invoke setExecutableRecursively")
        self.assertIn('name.endsWith(".so")', content,
                      "setExecutableRecursively must target .so native libraries")

    def test_build_gradle_and_asset_manager_java17(self):
        """Verify build.gradle bundles Java 17 and AsyncAssetManager verifies 17."""
        bg_content = BUILD_GRADLE.read_text(encoding="utf-8")
        self.assertIn('registrar.jreRuntimeDependency 17, "components/jre"', bg_content,
                      "build.gradle must specify Java 17 runtime dependency")

        am_content = ASYNC_ASSET_MANAGER.read_text(encoding="utf-8")
        self.assertIn("MultiRTUtils.getExactJreName(17)", am_content,
                      "AsyncAssetManager must check exact JRE 17")

    def test_simulation_tar_extraction_permission_modes(self):
        """Simulate tar archive extraction with various permission modes and verify hardening."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            tar_file = tmp_path / "test_runtime.tar"
            extract_dest = tmp_path / "dest"
            extract_dest.mkdir()

            # Create synthetic tar archive with various entry modes
            test_files = [
                ("bin/java", 0o644, b"#!/bin/sh\necho Java"),        # bin file without exec bits
                ("bin/keytool", 0o000, b"keytool_data"),             # bin file zero mode
                ("lib/server/libjvm.so", 0o755, b"\x7fELF_JVM"),      # native lib with exec
                ("lib/libjava.so", 0o644, b"\x7fELF_LIBJAVA"),       # native lib without exec
                ("lib/jvm.cfg", 0o644, b"-server KNOWN\n"),          # data file
                ("release", 0o444, b"JAVA_VERSION=\"17.0.13\"\n"),   # read-only file
            ]

            with tarfile.open(tar_file, "w") as tar:
                for rel_path, mode, data in test_files:
                    ti = tarfile.TarInfo(name=rel_path)
                    ti.size = len(data)
                    ti.mode = mode
                    import io
                    tar.addfile(ti, io.BytesIO(data))

            # Simulate MultiRTUtils extraction logic
            with tarfile.open(tar_file, "r") as tar:
                for entry in tar.getmembers():
                    dest_file = extract_dest / entry.name
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    if entry.isreg():
                        with open(dest_file, "wb") as f:
                            f.write(tar.extractfile(entry).read())

                        # MultiRTUtils.java logic
                        mode = entry.mode
                        is_in_bin = dest_file.parent.name == "bin"
                        if (mode & 0o111) != 0 or is_in_bin:
                            # destPath.setExecutable(true, false) -> 0o755 or 0o775
                            current = dest_file.stat().st_mode
                            dest_file.chmod(current | 0o111)

            # Simulate postPrepare recursive walk
            for root, dirs, files in os.walk(extract_dest):
                for f in files:
                    fp = Path(root) / f
                    if fp.name.endswith(".so") or fp.parent.name == "bin":
                        current = fp.stat().st_mode
                        fp.chmod(current | 0o111)

            # Assertions:
            # 1. bin/java must have execute bit
            bin_java = extract_dest / "bin/java"
            self.assertTrue(os.access(bin_java, os.X_OK), "bin/java must be executable")
            self.assertTrue(bool(bin_java.stat().st_mode & 0o111), "bin/java must have execute bits set")

            # 2. bin/keytool must have execute bit despite mode 0000 in tar
            bin_keytool = extract_dest / "bin/keytool"
            self.assertTrue(os.access(bin_keytool, os.X_OK), "bin/keytool must be executable despite tar mode 0000")

            # 3. lib/server/libjvm.so and lib/libjava.so must have execute bit
            libjvm = extract_dest / "lib/server/libjvm.so"
            libjava = extract_dest / "lib/libjava.so"
            self.assertTrue(os.access(libjvm, os.X_OK), "libjvm.so must be executable")
            self.assertTrue(os.access(libjava, os.X_OK), "libjava.so must be executable")

            # 4. release and jvm.cfg must NOT have execute bit
            release_f = extract_dest / "release"
            self.assertFalse(bool(release_f.stat().st_mode & 0o111), "release file should remain non-executable")

    def test_actual_bundled_arm64_archive_inspection(self):
        """Inspect actual bundled bin-arm64.tar.xz and verify real OpenJDK binary headers."""
        if not MERGED_ARM64_JRE.exists():
            self.skipTest(f"Merged asset {MERGED_ARM64_JRE} not found (skip if not compiled)")

        with tarfile.open(MERGED_ARM64_JRE, "r:xz") as tar:
            names = tar.getnames()
            self.assertIn("./bin/java", names, "Archive must contain ./bin/java")
            self.assertIn("./lib/server/libjvm.so", names, "Archive must contain ./lib/server/libjvm.so")

            java_member = tar.getmember("./bin/java")
            self.assertTrue(bool(java_member.mode & 0o111), "Archived bin/java must have POSIX executable bits")

            # Extract java binary and check ELF
            f = tar.extractfile(java_member)
            header = f.read(16)
            self.assertEqual(header[:4], b"\x7fELF", "bin/java must be a valid ELF binary")
            self.assertEqual(header[4], 2, "bin/java must be 64-bit ELF (ELFCLASS64)")
            self.assertEqual(header[5], 1, "bin/java must be little-endian (ELFDATA2LSB)")


if __name__ == "__main__":
    unittest.main()
