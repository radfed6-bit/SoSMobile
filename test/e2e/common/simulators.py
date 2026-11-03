"""Simulation models and verification engines for Android SharedPreferences, hardware heuristics, and process execution."""

import json
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from .env import (
    SEEKBAR_RAM_INCREMENT,
    SEEKBAR_RESOLUTION_INCREMENT,
    MIN_RAM_MB,
    AUTO_CONFIG_VERSION_KEY,
    CURRENT_AUTO_CONFIG_VERSION,
)


class MockSharedPreferencesEditor:
    def __init__(self, prefs: 'MockSharedPreferences'):
        self.prefs = prefs
        self.staged: Dict[str, Any] = {}
        self.removals = set()
        self.cleared = False

    def putInt(self, key: str, value: int):
        self.staged[key] = int(value)
        return self

    def putString(self, key: str, value: str):
        self.staged[key] = str(value)
        return self

    def putBoolean(self, key: str, value: bool):
        self.staged[key] = bool(value)
        return self

    def remove(self, key: str):
        self.removals.add(key)
        self.staged.pop(key, None)
        return self

    def clear(self):
        self.cleared = True
        self.staged.clear()
        return self

    def apply(self):
        self.commit()

    def commit(self) -> bool:
        if self.cleared:
            self.prefs._storage.clear()
        for k in self.removals:
            self.prefs._storage.pop(k, None)
        self.prefs._storage.update(self.staged)
        self.staged.clear()
        self.removals.clear()
        self.cleared = False
        return True


class MockSharedPreferences:
    def __init__(self, initial: Optional[Dict[str, Any]] = None):
        self._storage: Dict[str, Any] = dict(initial or {})

    def getInt(self, key: str, default: int = 0) -> int:
        val = self._storage.get(key, default)
        return int(val) if val is not None else default

    def getString(self, key: str, default: Optional[str] = None) -> Optional[str]:
        val = self._storage.get(key, default)
        return str(val) if val is not None else default

    def getBoolean(self, key: str, default: bool = False) -> bool:
        val = self._storage.get(key, default)
        return bool(val) if val is not None else default

    def contains(self, key: str) -> bool:
        return key in self._storage

    def getAll(self) -> Dict[str, Any]:
        return dict(self._storage)

    def edit(self) -> MockSharedPreferencesEditor:
        return MockSharedPreferencesEditor(self)


@dataclass
class DeviceHardware:
    total_ram_mb: int
    screen_width: int
    screen_height: int
    gpu_vendor: str = "ARM"
    gpu_renderer: str = "Mali-G57 MC2"
    is_32_bit: bool = False
    has_vulkan: bool = True
    sdk_int: int = 35

    @property
    def min_screen_side(self) -> int:
        return min(self.screen_width, self.screen_height)

    @property
    def max_screen_side(self) -> int:
        return max(self.screen_width, self.screen_height)

    @property
    def is_adreno(self) -> bool:
        return "Adreno" in self.gpu_renderer or "Qualcomm" in self.gpu_vendor


class HardwareHeuristicEngine:
    """Specification oracle for Songs of Syx device auto-configuration."""

    @staticmethod
    def compute_optimal_ram(total_ram_mb: int, is_32_bit: bool = False) -> int:
        if is_32_bit:
            val = min(800, max(512, total_ram_mb - 512))
        elif total_ram_mb < 1024:
            val = 512
        elif total_ram_mb <= 2048:
            val = 768
        elif total_ram_mb <= 3500:
            val = 1536
        elif total_ram_mb <= 5000:
            val = 2048
        elif total_ram_mb <= 7000:
            val = 3072
        elif total_ram_mb <= 9500:
            val = 4608
        elif total_ram_mb <= 13000:
            val = 6144
        else:
            val = 8192

        # Seekbar alignment requirement: multiple of 8 MB
        val = (val // SEEKBAR_RAM_INCREMENT) * SEEKBAR_RAM_INCREMENT
        return max(MIN_RAM_MB, val)

    @staticmethod
    def compute_optimal_resolution_ratio(min_side: int, total_ram_mb: int, is_adreno: bool = False) -> int:
        if min_side <= 720:
            ratio = 100
        elif min_side <= 1080:
            if total_ram_mb <= 4096 or not is_adreno:
                ratio = 85
            else:
                ratio = 100
        else:
            # Scale down high-res (QHD+ / Tablet) to ~1080p target to prevent GPU thermal throttling
            target = 1080.0
            raw_ratio = (target / float(min_side)) * 100.0
            increment = SEEKBAR_RESOLUTION_INCREMENT
            ratio = int(round(raw_ratio / increment) * increment)

        return max(25, min(100, ratio))

    @staticmethod
    def run_auto_config(hw: DeviceHardware, prefs: MockSharedPreferences, force: bool = False) -> bool:
        if not force and prefs.getInt(AUTO_CONFIG_VERSION_KEY, 0) >= CURRENT_AUTO_CONFIG_VERSION:
            return False  # Already configured

        ram = HardwareHeuristicEngine.compute_optimal_ram(hw.total_ram_mb, hw.is_32_bit)
        res_ratio = HardwareHeuristicEngine.compute_optimal_resolution_ratio(
            hw.min_screen_side, hw.total_ram_mb, hw.is_adreno
        )
        renderer = "opengles2"
        alternate_surface = hw.total_ram_mb >= 3000
        sustained_perf = (hw.sdk_int >= 24) and (hw.total_ram_mb >= 4000)
        force_vsync = True
        zink_prefer_sys = not hw.is_adreno

        prefs.edit() \
            .putInt("allocation", ram) \
            .putInt("resolutionRatio", res_ratio) \
            .putString("renderer", renderer) \
            .putBoolean("alternate_surface", alternate_surface) \
            .putBoolean("sustainedPerformance", sustained_perf) \
            .putBoolean("force_vsync", force_vsync) \
            .putBoolean("zinkPreferSystemDriver", zink_prefer_sys) \
            .putInt(AUTO_CONFIG_VERSION_KEY, CURRENT_AUTO_CONFIG_VERSION) \
            .apply()

        return True


class MockProcessExecution:
    """Simulates OpenJDK process fork & exec and permission verification."""

    @staticmethod
    def simulate_exec(binary_path: str, mode: int, is_hooked: bool = True) -> Dict[str, Any]:
        """
        Simulate forkAndExec:
        - Mode must have executable bit (0o111)
        - If mode lacks executable bit, return error=13 unless intercepted by java_exec_hooks
        """
        is_executable = bool(mode & 0o111)
        is_java = binary_path.endswith("/java") or binary_path == "java"

        if is_hooked and is_java:
            # Hook intercept: prevents error 13 on W^X / SELinux
            return {"exit_code": 0, "status": "SUCCESS_HOOKED", "error": None}

        if not is_executable:
            return {
                "exit_code": 13,
                "status": "EACCES",
                "error": f"Cannot run program \"{binary_path}\": error=13, Permission denied",
            }

        return {"exit_code": 0, "status": "SUCCESS_DIRECT", "error": None}
