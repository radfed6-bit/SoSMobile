# E2E Test Infrastructure Specification: SoSMobile

## 1. Overview & Architectural Principles

SoSMobile is an Android launcher providing a mobile runtime environment for the desktop Java strategy/simulation game *Songs of Syx*. Because the launcher orchestrates multiple interconnected subsystems—including OpenJDK 17 execution inside Android process space, dynamic linking of LWJGL 3 native libraries (`liblwjgl.so`), hardware detection with heuristic configuration, multi-locale UI localization, and customized POSIX/file system layout—the test infrastructure must validate both functional and non-functional requirements without requiring physical hardware deployment for every build verification.

This document formalizes the End-to-End (E2E) Test Infrastructure for SoSMobile, following an **opaque-box, requirement-driven, 4-tier test architecture**.

### 1.1 Core Principles

1. **Opaque-Box & Requirement-Driven**:
   Tests are derived strictly from user requirements (R1–R4 in `ORIGINAL_REQUEST.md`) and feature specifications (F1–F11 in `PROJECT.md`). Tests assert expected inputs, contracts, and outputs rather than internal transient private variables.
2. **Deterministic & Self-Contained**:
   Every test creates its own sandboxed environment, avoids reliance on execution order, handles file I/O safely, and cleans up artifacts upon completion.
3. **Multi-Layered Verification**:
   The suite spans source-level contract verification, compiled artifact & ELF binary validation, simulated Android lifecycle & preferences persistence, and process fork/exec mechanics.
4. **Zero-Dependency Execution**:
   The test runner and harness rely strictly on standard Linux/POSIX tools and Python 3 standard library modules (`unittest`, `subprocess`, `xml.etree`, `json`, `zipfile`, `struct`, `re`, `pathlib`, `os`, `sys`). This guarantees execution reliability inside any standard CI/CD container or development Codespace without external package bloat.

---

## 2. Four-Tier Test Architecture

The testing methodology organizes all test cases into four distinct tiers:

```
┌─────────────────────────────────────────────────────────────────┐
│                   Tier 4: Real-World Scenarios                  │
│       (End-to-end user workflows, cold start, process fork,      │
│         multi-locale, corrupted settings recovery, tablet)      │
├─────────────────────────────────────────────────────────────────┤
│               Tier 3: Cross-Feature Combinations                │
│    (Pairwise interactions: F1+F2, F3+F9, F5+F6, F4+F6, etc.)    │
├─────────────────────────────────────────────────────────────────┤
│           Tier 2: Boundary Value Analysis & Corner Cases        │
│   (Missing files, permission errors, extreme RAM, invalid JSON, │
│        unusual aspect ratios, W^X handling, empty locales)      │
├─────────────────────────────────────────────────────────────────┤
│              Tier 1: Feature Baseline Coverage (Happy Path)     │
│   (Category-Partition: F1-F11 standard behavior and contracts)  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.1 Tier 1: Feature Baseline Coverage (Category-Partition)
- **Objective**: Verify that each of the 11 features (F1–F11) behaves as expected under valid, standard operating conditions.
- **Coverage Requirement**: $\ge 5$ distinct test cases per feature ($11 \times 5 = 55$ test cases minimum).
- **Technique**: Category-Partition method dividing each feature's specification into equivalence classes and verifying nominal cases.

### 2.2 Tier 2: Boundary Value Analysis (BVA) & Corner Cases
- **Objective**: Stress-test error paths, boundary values, missing files, permission anomalies, non-standard screen dimensions, extreme memory values, and corrupt data.
- **Coverage Requirement**: $\ge 5$ distinct test cases per feature ($11 \times 5 = 55$ test cases minimum).
- **Technique**: Boundary Value Analysis, adversarial input injection, failure cascade detection, and defensive exception handling.

### 2.3 Tier 3: Cross-Feature Combinations (Pairwise Interactions)
- **Objective**: Validate the interaction between subsystems that depend on each other.
- **Coverage Requirement**: $\ge 11$ distinct cross-feature test cases covering key subsystem intersections.
- **Matrix Highlights**:
  - `F1` (Java 17) $\times$ `F2` (Binary Exec Permissions): Verifying tar extraction mode 0755 feeds into OpenJDK 17 execution.
  - `F1` (Java 17) $\times$ `F3` (LWJGL 3 Linking): Verifying JVM `-Dorg.lwjgl.librarypath` and `-Djava.library.path` correctly bind LWJGL 3 inside Java 17.
  - `F4` (Default Game Config) $\times$ `F6` (Hardware Heuristics): Ensuring generated config paths coexist with memory and scale parameters.
  - `F5` (Auto-Config Coordinator) $\times$ `F6` (Heuristics): Ensuring coordinator computes and persists the 7-tier RAM and resolution settings properly into `SharedPreferences`.
  - `F7` (Rebranding) $\times$ `F8` (Icon Assets): Ensuring UI manifests, drawables, strings, and layouts present a consistent, unbranded SoSMobile identity.
  - `F3` (LWJGL 3 Linking) $\times$ `F9` (Code Health): Ensuring native library directories and crash guards prevent JVM panic during early initialization.

### 2.4 Tier 4: Real-World Application Scenarios
- **Objective**: Emulate full end-to-end user lifecycles from fresh install to multiple gaming sessions.
- **Coverage Requirement**: $\ge 6$ multi-step integrated workflows.
- **Scenarios**:
  1. *Fresh Install Cold-Start*: Zero existing config, first launch triggers auto-configuration, unpacks default settings, generates active mod structure, selects Java 17 runtime, and constructs launch command line.
  2. *Subsequent Launch Idempotency*: User customizes RAM or renderer; launcher restarts; auto-config detects existing version flag and preserves custom user settings without overwriting.
  3. *Settings Reset Workflow*: User invokes "Reset to Recommended Settings"; coordinator re-evaluates hardware and safely resets parameters.
  4. *Low-Memory & 32-Bit System Graceful Degradation*: Device with < 2GB RAM is detected; launcher scales to 768MB JVM without violating the 512MB minimum limit or triggering Linux OOM.
  5. *High-Resolution Tablet & Notch Adaptation*: Device with 1600x2560 display and cutout; launcher clamps resolution ratio to prevent thermal throttling while preserving font legibility.
  6. *Corrupted Game Configuration Recovery*: `LauncherSettings.txt` is missing or empty; runtime repair regenerates valid default configuration and launches without crash.

---

## 3. Feature Coverage Matrix (F1–F11)

| Feature ID | Feature Name | Tier 1 (Baseline) | Tier 2 (BVA / Corner) | Tier 3 (Cross-Feature) | Tier 4 (Scenario) |
|---|---|---|---|---|---|
| **F1** | Java 17 Default Runtime | Bundle in `build.gradle`, select in `AsyncAssetManager`, default in `GameRunner`, runtime packaging, version verification | Missing runtime, incompatible version rejection, partial archive, non-standard JRE name, corrupt manifest | F1 $\times$ F2, F1 $\times$ F3 | Fresh Install, Process Spawning |
| **F2** | Runtime Binary Permissions (`error=13`) | Mode 0755 in tar extractor, chmod +x in `postPrepare`, execve hook interception in `java_exec_hooks.c`, AArch64 ELF magic check, process fork/exec simulation | Missing execute bits, non-executable filesystem, read-only file, corrupted ELF header, hook bypass | F2 $\times$ F1, F2 $\times$ F9 | Process Spawning, Low-RAM Exec |
| **F3** | Native LWJGL 3 Linking (`liblwjgl.so`) | Bundle `liblwjgl.so` ARM64, verify ELF soname & symbols, configure `-Dorg.lwjgl.librarypath`, verify `java.library.path`, dynamic loader simulation | Missing lib directory, 32-bit vs 64-bit mismatch, stripped symbols, conflicting library paths, corrupt `.so` | F3 $\times$ F1, F3 $\times$ F9 | Fresh Install, Launcher Restart |
| **F4** | Default Game Config & Paths | Extract `LauncherSettings.txt`, default active mods `{"MODS": []}`, replace `"/SoSMobile"` with external storage, directory hierarchy creation, path normalization | Missing parent dir, invalid JSON syntax, read-only storage, trailing slashes, empty path fallback | F4 $\times$ F5, F4 $\times$ F6 | Corrupted Settings Recovery, Custom Mod Dirs |
| **F5** | Device Auto-Config Coordinator | Coordinator existence, version persistence (`auto_config_version`), SharedPreferences persistence, first-run trigger, reset trigger | Stale config version, negative version, missing SharedPreferences, concurrent edit, read-only prefs | F5 $\times$ F6, F5 $\times$ F4 | Fresh Install, Subsequent Launch, Settings Reset |
| **F6** | SoS Hardware Heuristics | 7-tier RAM calculation, display scale calculation, default `opengles2`, `alternate_surface` = true, `force_vsync` = true | RAM < 512MB clamp, RAM > 16GB clamp, 1440p/4K resolution downscaling, 720p minimum scale, step alignment (8MB / 5%) | F6 $\times$ F5, F6 $\times$ F4 | Low-Memory Adaptation, Tablet Adaptation |
| **F7** | Main Menu Rebranding & Residue | `app_short_name` = "SoSMobile" across locales, removal of `news_button` (Wiki), removal of `social_media_button` (Discord), removal of `social_divider`, `MainMenuFragment` listeners removed | 45+ locale validation, strings with special chars, landscape layout matching, URL link purging, fallback strings | F7 $\times$ F8, F7 $\times$ F10 | Fresh Install, Multi-Locale Launch |
| **F8** | Icon Assets Replacement | Mipmap icons replaced, notification icon replaced, full launcher icon replaced, Play Store 512x512 replaced, asset `mojo.png` replaced | Dimension checks, transparency/alpha channel, non-zero file size, no residual "MJ"/"MOJO" pixels/hashes, invalid asset formats | F8 $\times$ F7, F8 $\times$ F10 | Fresh Install, UI Rendering |
| **F9** | Codebase Health & Crash Prevention | Null-guard `mServiceBinder` in `GameActivity:439`, null-guard `mSurface` in `GameView`, external storage path resolution, Minecraft artifact removal, exception handling | Null service binder during early failure, touch events before surface ready, invalid external storage state, missing assets, NPE prevention | F9 $\times$ F3, F9 $\times$ F2 | Process Spawning, Corrupted Settings Recovery |
| **F10** | Documentation Cleanup | Clean `README.md` structure, clean `README_RU.md` structure, removal of dev kitchen/chatter, accurate build steps, feature summary | Broken markdown formatting, missing sections, stale URLs, encoding validity, bilingual parity | F10 $\times$ F7, F10 $\times$ F11 | User Documentation Verification |
| **F11** | Build System & Assembly | Gradle build configuration, AGP compatibility, submodule registration, compileOptions consistency, JRE asset dependency | Missing submodules, invalid SDK path, corrupted local.properties, gradle wrapper execution, task dependency validation | F11 $\times$ F1, F11 $\times$ F3 | Fresh Clone Build Assembly |

---

## 4. Test Suite Directory Structure

```
/workspaces/SoSMobile/test/e2e/
├── run_tests.sh                      # Master executable runner (exit 0 on success)
├── test_runner.py                    # Core Python test execution & reporting engine
├── common/                           # Shared infrastructure, fixtures & simulators
│   ├── __init__.py
│   ├── env.py                        # Workspace paths, constants, mock environments
│   ├── assertions.py                 # Custom test assertions and validators
│   └── simulators.py                 # Android SharedPreferences & process simulators
├── tier1_features/                   # Tier 1: Feature Baseline Coverage (>= 55 tests)
│   ├── __init__.py
│   ├── test_f1_java17_default.py
│   ├── test_f2_runtime_permissions.py
│   ├── test_f3_lwjgl_linking.py
│   ├── test_f4_game_config_paths.py
│   ├── test_f5_autoconfig_coordinator.py
│   ├── test_f6_hardware_heuristics.py
│   ├── test_f7_rebranding_residue.py
│   ├── test_f8_icon_assets.py
│   ├── test_f9_codebase_health.py
│   ├── test_f10_documentation.py
│   └── test_f11_build_assembly.py
├── tier2_boundaries/                 # Tier 2: Boundary & Corner Cases (>= 55 tests)
│   ├── __init__.py
│   ├── test_f1_bva.py
│   ├── test_f2_bva.py
│   ├── test_f3_bva.py
│   ├── test_f4_bva.py
│   ├── test_f5_bva.py
│   ├── test_f6_bva.py
│   ├── test_f7_bva.py
│   ├── test_f8_bva.py
│   ├── test_f9_bva.py
│   ├── test_f10_bva.py
│   └── test_f11_bva.py
├── tier3_pairwise/                   # Tier 3: Cross-Feature Combinations (>= 11 tests)
│   ├── __init__.py
│   └── test_cross_feature_combinations.py
└── tier4_scenarios/                  # Tier 4: Real-World Scenarios (>= 6 tests)
    ├── __init__.py
    └── test_real_world_scenarios.py
```

---

## 5. Execution & Verification Harness

### 5.1 Invocation Commands

```bash
# Execute full E2E test suite
bash /workspaces/SoSMobile/test/e2e/run_tests.sh

# Or invoke directly via Python 3
python3 /workspaces/SoSMobile/test/e2e/test_runner.py
```

### 5.2 Command Options & Filters
- `python3 /workspaces/SoSMobile/test/e2e/test_runner.py --tier 1`: Run only Tier 1 tests.
- `python3 /workspaces/SoSMobile/test/e2e/test_runner.py --tier 2`: Run only Tier 2 tests.
- `python3 /workspaces/SoSMobile/test/e2e/test_runner.py --tier 3`: Run only Tier 3 tests.
- `python3 /workspaces/SoSMobile/test/e2e/test_runner.py --tier 4`: Run only Tier 4 tests.
- `python3 /workspaces/SoSMobile/test/e2e/test_runner.py --verbose`: Run with detailed individual test diagnostics.

### 5.3 Exit Code Contract
- `0`: All test cases passed successfully.
- `1`: One or more test cases failed or encountered an uncaught error.

---

## 6. Authoritative Expected Output Derivation

All assertions are linked directly to authoritative project specifications:

1. **Java 17 Bundling & Picking**:
   - `ORIGINAL_REQUEST.md` R1: Launcher must use Java 17 by default without manual user install.
   - `PROJECT.md` F1: `registrar.jreRuntimeDependency 17`, `MultiRTUtils.getExactJreName(17)`.
2. **Permission Denied (`error=13`)**:
   - `latestlog.txt:86`: `Cannot run program ".../bin/java": error=13, Permission denied`.
   - `PROJECT.md` F2: Tar extraction mode 0755 restored; `chmod +x` on `bin/*`; `java_exec_hooks.c` interception.
3. **LWJGL 3 Linking (`UnsatisfiedLinkError`)**:
   - `latestlog.txt:138`: `UnsatisfiedLinkError: Failed to locate library: liblwjgl.so`.
   - `PROJECT.md` F3: `liblwjgl.so` present in `jniLibs/arm64-v8a/`; `-Dorg.lwjgl.librarypath` set to native lib dir.
4. **Configuration & Paths**:
   - `latestlog.txt:104`: `DataError: This resource could not be found: .../LauncherSettings.txt`.
   - `PROJECT.md` F4: `extractDefaultSettings()` writes `LauncherSettings.txt` with `{"MODS": []}`; root `"/SoSMobile"` replaced with external storage.
5. **Auto-Configuration & Hardware Heuristics**:
   - `ORIGINAL_REQUEST.md` R2: Auto-detect device specs on first launch and set optimal parameters.
   - `PROJECT.md` § Interface Contracts: `DeviceAutoConfig` persists `"allocation"`, `"resolutionRatio"`, `"renderer"`, `"alternate_surface"`, `"sustainedPerformance"`, `"force_vsync"`, and `"auto_config_version"` = 1.
   - 7-tier RAM mapping: 768MB (<2GB), 1536MB (3GB), 2048MB (4GB), 3072MB (6GB), 4608MB (8GB), 6144MB (12GB), 8192MB (16GB+).
   - Display downscaling: minSide > 1080px scaled to ~1080p target (75% on 1440p) to avoid thermal throttling.
6. **Rebranding**:
   - `ORIGINAL_REQUEST.md` R3: Remove MJLauncher / MojoLauncher branding, update app icon, remove Discord and Wiki links.
   - `PROJECT.md` F7, F8: `app_short_name` = "SoSMobile" across all 45+ locales; no Wiki/Discord buttons in `fragment_launcher.xml`; all icon assets replaced.
7. **Documentation**:
   - `ORIGINAL_REQUEST.md` Follow-up: Clean up `README.md` and `README_RU.md`, removing dev kitchen details and fluff.
