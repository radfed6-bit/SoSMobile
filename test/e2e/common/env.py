"""Environment definitions, paths, constants, and specifications for SoSMobile E2E tests."""

import os
from pathlib import Path

# Workspace Root
PROJECT_ROOT = Path("/workspaces/SoSMobile").resolve()
APP_MOJO_DIR = PROJECT_ROOT / "app_mojo"
RES_DIR = APP_MOJO_DIR / "src/main/res"

# Key Source File Paths
BUILD_GRADLE = APP_MOJO_DIR / "build.gradle"
ASYNC_ASSET_MANAGER = APP_MOJO_DIR / "src/main/java/git/artdeell/mojo/tasks/AsyncAssetManager.java"
MULTI_RT_UTILS = APP_MOJO_DIR / "src/main/java/git/artdeell/mojo/multirt/MultiRTUtils.java"
GAME_RUNNER = APP_MOJO_DIR / "src/main/java/git/artdeell/mojo/utils/jre/GameRunner.java"
SYX_LAUNCH_CONFIG = APP_MOJO_DIR / "src/main/java/git/artdeell/mojo/launch/SyxLaunchConfig.java"
JAVA_EXEC_HOOKS = APP_MOJO_DIR / "src/main/jni/jvm_hooks/java_exec_hooks.c"
LIBLWJGL_SO = APP_MOJO_DIR / "src/main/jniLibs/arm64-v8a/liblwjgl.so"
DEVICE_AUTO_CONFIG = APP_MOJO_DIR / "src/main/java/git/artdeell/mojo/prefs/DeviceAutoConfig.java"
LAUNCHER_PREFS = APP_MOJO_DIR / "src/main/java/git/artdeell/mojo/prefs/LauncherPreferences.java"
MOD_MANAGER_FRAGMENT = APP_MOJO_DIR / "src/main/java/git/artdeell/mojo/mods/ModManagerFragment.java"
MAIN_MENU_FRAGMENT = APP_MOJO_DIR / "src/main/java/git/artdeell/mojo/fragments/MainMenuFragment.java"
GAME_ACTIVITY = APP_MOJO_DIR / "src/main/java/git/artdeell/mojo/game/GameActivity.java"
GAME_VIEW = APP_MOJO_DIR / "src/main/java/git/artdeell/mojo/game/GameView.java"
FRAGMENT_LAUNCHER_XML = RES_DIR / "layout/fragment_launcher.xml"
FRAGMENT_LAUNCHER_LAND_XML = RES_DIR / "layout-land/fragment_launcher.xml"
README_EN = PROJECT_ROOT / "README.md"
README_RU = PROJECT_ROOT / "README_RU.md"

# Specification Constants: Hardware Heuristics
RAM_TIER_1_MAX = 2048       # < 2048 MB -> 768 MB
RAM_TIER_2_MAX = 3500       # 2048 - 3500 MB -> 1536 MB
RAM_TIER_3_MAX = 5000       # 3501 - 5000 MB -> 2048 MB
RAM_TIER_4_MAX = 7000       # 5001 - 7000 MB -> 3072 MB
RAM_TIER_5_MAX = 9500       # 7001 - 9500 MB -> 4608 MB
RAM_TIER_6_MAX = 13000      # 9501 - 13000 MB -> 6144 MB
# > 13000 MB -> 8192 MB

SEEKBAR_RAM_INCREMENT = 8
SEEKBAR_RESOLUTION_INCREMENT = 5
MIN_RAM_MB = 512

AUTO_CONFIG_VERSION_KEY = "auto_config_version"
CURRENT_AUTO_CONFIG_VERSION = 1
