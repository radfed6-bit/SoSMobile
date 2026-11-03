# Project: SoSMobile Android Launcher Release

## Architecture
SoSMobile is an Android launcher tailored for the game Songs of Syx, built upon the MojoLauncher native/Java framework.
- **Java Runtime Layer**: Runs desktop OpenJDK (ARM64) inside Android process space using custom JVM launcher hooks, dynamic linker redirection, and POSIX emulation.
- **Native Graphics Layer**: Bridges LWJGL 3 desktop OpenGL/GLFW calls to mobile OpenGL ES 2.0/3.0 / Vulkan via GL4ES, SDL3, and specialized native libraries (`libgl4es_114.so`, `liblwjgl.so`, `libglfw.so`).
- **Configuration & Preferences**: `LauncherPreferences` backed by Android `SharedPreferences`, enhanced with `DeviceAutoConfig` for hardware detection (RAM, display, GPU) and optimal runtime parameter calculation.
- **UI & Lifecycle**: Multi-fragment Android UI (`MainMenuFragment`, `LauncherPreferenceFragment`, `GameActivity`) launching desktop game processes with custom file storage layout (`/storage/emulated/0/SoSMobile` and `$HOME/.local/share/songsofsyx`).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Java 17 Default Runtime | Bundle & select Java 17 by default in `build.gradle` and `AsyncAssetManager` without manual user install | M1 | R1, survey_1 |
| F2 | Runtime Binary Execution & Permissions | Restore mode 0755 in tar extraction, chmod +x in `postPrepare`, handle "java" in `java_exec_hooks.c` (error=13 fix) | M1 | R1, survey_1 |
| F3 | Native LWJGL 3 Linking | Bundle `liblwjgl.so` (LWJGL 3.4.1 ARM64) into `jniLibs/arm64-v8a/` and configure `-Dorg.lwjgl.librarypath` | M1 | R1, survey_1 |
| F4 | Default Game Config & Paths | Implement `AsyncAssetManager.extractDefaultSettings()` for `LauncherSettings.txt` and fix broken `"/SoSMobile"` root paths | M1 | R1, survey_1 |
| F5 | Device Auto-Config Coordinator | Implement `DeviceAutoConfig` coordinator with versioned persistence (`auto_config_version`), RAM/display/GPU detection | M2 | R2, survey_2 |
| F6 | SoS Hardware Heuristics | 7-tier RAM scaling (768MB-8192MB), display scale to avoid QHD+ throttling, opengles2 default, reset settings option | M2 | R2, survey_2 |
| F7 | Main Menu Rebranding & Residue | Replace `app_short_name` across 45+ locale `strings.xml`, remove Wiki/Discord buttons from `fragment_launcher.xml` | M3 | R3, survey_3 |
| F8 | Icon Assets Replacement | Replace legacy MJ/MOJO icons in `res/mipmap-*`, `res/drawable-*`, and assets with clean SoSMobile graphics | M3 | R3, survey_3 |
| F9 | Codebase Health & Crash Prevention | Null-guard `mServiceBinder` in `GameActivity:439`, null-guard `mSurface` in `GameView`, prune legacy Minecraft artifacts | M4 | R4, survey_3 |
| F10 | Documentation Cleanup | Clean up `README.md` and `README_RU.md`, removing dev kitchen details and providing clear user guide | M3 | User Follow-up 1 |
| F11 | Build System & Assembly | Init submodules, configure SDK/NDK in `local.properties`, align compileOptions, verify `./gradlew assembleDebug` | M4 | Acceptance, survey_3 |
| F12 | E2E Test Suite | Comprehensive opaque-box test suite (Tiers 1-4) verifying all requirements and publishing `TEST_READY.md` | M5 | Project Pattern |
| F13 | GitHub Release & Repository Push | Commit and push code to GitHub repository, create GitHub Release with assembled APK via `gh` CLI | M4 | User Follow-up 2 |
| F14 | LWJGL/GLFW Launch Args & Native Compatibility | JVM args `-Dorg.lwjgl.glfw.libname=libglfw.so`, library path, headless mode, LWJGL 3.3.x native symbol bridge | M6 | User Follow-up 4 |
| F15 | Authoritative Legal Notices Correction | Update Legal Notices in `README.md` and `README_RU.md` with Jake Versluis / Gamatron AB | M6 | User Follow-up 5 |
| F16 | Android 15 Bionic FORTIFY Mutex Protections | Fix `pthread_mutex_lock` on destroyed/uninitialized mutexes in GLFW and AWT (`posix_thread.c`, `init.c`, `android_window.c`, `awt.c`) | M6 | User Follow-up 6 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Runtime & Crash Remediation | F1, F2, F3, F4 | none | DONE |
| M2 | First-Launch Device Auto-Config | F5, F6 | none | DONE |
| M3 | Rebranding & Documentation | F7, F8, F10 | none | DONE |
| M4 | Code Health, Build Assembly & Release | F9, F11, F13 | M1, M2, M3 | DONE |
| M5 | E2E Testing Track | F12 | none (Parallel) | DONE |
| M6 | Final Verification & Release v0.1.1 | Tiers 1-4 pass + Tier 5 hardening + F14 + F15 + F16 + Forensic Audit | M4, M5 | DONE |

## Interface Contracts
### `DeviceAutoConfig` ↔ `LauncherPreferences`
- `DeviceAutoConfig.runAutoConfigIfNeeded(Context context)`: Invoked at top of `LauncherPreferences.loadPreferences(ctx)`.
- Checks `DEFAULT_PREF.getInt("auto_config_version", 0) < 1`. If true, computes hardware metrics and writes keys:
  - `"allocation"` (int, MB)
  - `"resolutionRatio"` (int, percentage 50..100)
  - `"renderer"` (String, default "opengles2")
  - `"alternate_surface"` (boolean, true)
  - `"sustainedPerformance"` (boolean, false)
  - `"force_vsync"` (boolean, true)
  - `"auto_config_version"` (int, 1)
  using `SharedPreferences.Editor.apply()`.

### `AsyncAssetManager` ↔ `GameRunner`
- `AsyncAssetManager.unpackComponents(Context ctx)`: Extracts bundled Java 17 archive to `runtimes/Internal/` with executable permissions on all binaries.
- `AsyncAssetManager.extractDefaultSettings(Context ctx)`: Generates valid `$HOME/.local/share/songsofsyx/settings/LauncherSettings.txt` with default active mods (`{"MODS": []}`).
- `GameRunner.pickRuntime(instance, 17)`: Resolves Java 17 `"Internal"` runtime without prompt.

### `Native Libraries` ↔ `JVM Launch Config`
- `app_mojo/src/main/jniLibs/arm64-v8a/liblwjgl.so` packaged into APK native library directory (`Tools.NATIVE_LIB_DIR`).
- `SyxLaunchConfig.java` appends `-Dorg.lwjgl.librarypath=Tools.NATIVE_LIB_DIR` and ensures `java.library.path` includes the native lib directory.

## Code Layout
- `app_mojo/src/main/java/git/artdeell/mojo/prefs/`: Preferences & auto-configuration (`LauncherPreferences.java`, `DeviceAutoConfig.java`).
- `app_mojo/src/main/java/git/artdeell/mojo/launch/`: Game launch configuration & arguments (`SyxLaunchConfig.java`, `GameRunner.java`).
- `app_mojo/src/main/java/git/artdeell/mojo/ui/`: UI fragments and activities (`MainMenuFragment.java`, `LauncherActivity.java`, `GameActivity.java`, `GameView.java`).
- `app_mojo/src/main/java/net/kdt/pojavlaunch/`: Runtime management (`MultiRTUtils.java`, `AsyncAssetManager.java`).
- `app_mojo/src/main/jni/`: Native C/C++ bridges (`jvm_hooks/java_exec_hooks.c`, CMake build).
- `app_mojo/src/main/jniLibs/arm64-v8a/`: Bundled native shared objects (`liblwjgl.so`, `libgl4es_114.so`, etc.).
- `app_mojo/src/main/res/`: Resource XMLs (layouts, values, drawables, mipmaps).
- `test/e2e/`: E2E test scripts, verification harnesses, and assertions.
