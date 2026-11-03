"""Custom assertions and validation utilities for SoSMobile E2E testing."""

import json
import re
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern


def assert_file_exists(path: Path, msg: Optional[str] = None):
    assert path.exists(), msg or f"Expected file does not exist: {path}"


def assert_elf_arm64(path: Path):
    """Asserts that a given binary file is a valid 64-bit ARM (AArch64) ELF shared object or executable."""
    assert_file_exists(path, f"ELF file not found: {path}")
    data = path.read_bytes()
    assert len(data) >= 52, f"File too small for ELF header: {len(data)} bytes"

    # Magic: \x7fELF
    assert data[:4] == b"\x7fELF", f"Invalid ELF magic: {data[:4]}"
    # Class: 2 = 64-bit
    assert data[4] == 2, f"Expected 64-bit ELF (class 2), got: {data[4]}"
    # Endianness: 1 = Little Endian
    assert data[5] == 1, f"Expected Little-Endian ELF (data 1), got: {data[5]}"
    # Version: 1
    assert data[6] == 1, f"Expected ELF version 1, got: {data[6]}"
    # e_machine: bytes 18-19 in little-endian format. 183 = EM_AARCH64 (0xb7)
    e_machine = struct.unpack("<H", data[18:20])[0]
    assert e_machine == 183, f"Expected AArch64 e_machine (183), got: {e_machine}"


def assert_file_contains_regex(path: Path, pattern: str, flags: int = 0, msg: Optional[str] = None):
    assert_file_exists(path)
    content = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(pattern, content, flags)
    assert match is not None, msg or f"Expected pattern '{pattern}' not found in {path}"


def assert_file_not_contains_regex(path: Path, pattern: str, flags: int = 0, msg: Optional[str] = None):
    assert_file_exists(path)
    content = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(pattern, content, flags)
    assert match is None, msg or f"Forbidden pattern '{pattern}' was unexpectedly found in {path} at match '{match.group(0)}'"


def assert_valid_json_file(path: Path) -> Any:
    assert_file_exists(path)
    content = path.read_text(encoding="utf-8")
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise AssertionError(f"File {path} is not valid JSON: {e}")
