# SoSMobile: Songs of Syx ARM64 Android Launcher

[![Status: Active Development / Beta](https://img.shields.io/badge/Status-Beta%20%2F%20Active%20Development-orange.svg)](https://github.com/radfed6-bit/SoSMobile)
[![Android CI](https://github.com/radfed6-bit/SoSMobile/actions/workflows/android.yml/badge.svg)](https://github.com/radfed6-bit/SoSMobile/actions)
[![Platform: ARM64](https://img.shields.io/badge/Platform-ARM64%20%2F%20aarch64-blue.svg)](https://github.com/radfed6-bit/SoSMobile)
[![Android API](https://img.shields.io/badge/Android-API%2021%2B%20(Target%2036)-green.svg)](https://developer.android.com)
[![JDK: OpenJDK 17](https://img.shields.io/badge/JDK-OpenJDK%2017-orange.svg)](https://adoptium.net)
[![License: LGPL v3](https://img.shields.io/badge/License-LGPLv3-brightgreen.svg)](https://www.gnu.org/licenses/lgpl-3.0)

> ### ⚠️ Work in Progress / Active Development Notice
> **SoSMobile is currently under active development (Beta).** This is a development preview build and not a final release. Features, touch ergonomics, and performance optimizations are being actively enhanced. Community feedback, issue reports, and contributions are welcome!

---

**SoSMobile** is a native ARM64 Android launcher application engineered to run the strategy and city-builder masterpiece **Songs of Syx** directly on modern Android smartphones and tablets.

Built on a repurposed, high-performance **MojoLauncher** runtime engine, SoSMobile delivers a native desktop gaming experience on mobile without modifying, repackaging, or redistributing the original game binaries.

---

## Table of Contents
- [Project Status & Notice](#project-status--notice)
- [Overview](#overview)
- [Requirements Fulfilled](#requirements-fulfilled)
- [Architecture](#architecture)
- [Hardware & Software Prerequisites](#hardware--software-prerequisites)
- [Build Instructions](#build-instructions)
- [User Guide](#user-guide)
  - [1. Game Files Preparation](#1-game-files-preparation)
  - [2. Storage Permissions](#2-storage-permissions)
  - [3. Selecting Game Directory](#3-selecting-game-directory)
  - [4. Launching the Game](#4-launching-the-game)
- [Touch Controls & Gestures](#touch-controls--gestures)
- [Floating Game HUD](#floating-game-hud)
- [Mod Management](#mod-management)
- [Continuous Integration (CI/CD)](#continuous-integration-cicd)
- [Troubleshooting & FAQ](#troubleshooting--faq)
- [Legal Notices & Credits](#legal-notices--credits)

---

## Project Status & Notice

SoSMobile is in **Active Development (Beta)**:
- **Core Engine**: Fully functional OpenJDK 17 ARM64 runtime with native OpenGL 3.3 Core profile and OpenAL audio.
- **Input System**: Multi-touch gesture processor and floating overlay HUD adapted specifically for city-building gameplay.
- **Current Milestone**: Milestone 5 completed — Clean architecture, standalone launcher repository, automated GitHub Actions CI/CD pipeline, and public repository release.
- **Release Status**: Development beta builds are automatically generated via GitHub Actions CI. This project does not distribute any proprietary game assets.

---

## Overview

*Songs of Syx* is a complex, large-scale city-builder and empire simulator developed by Jake Versluis. Running desktop Java/LWJGL applications on mobile devices typically presents severe challenges: architecture mismatches, missing desktop native libraries, and desktop-centric mouse/keyboard input schemes.

**SoSMobile** solves these challenges by providing:
1. **Desktop-Grade ARM64 Java Runtime**: Fully featured OpenJDK 17 runtime running directly on Android (`aarch64`).
2. **Native Graphics & Audio Translation**: Seamless hardware-accelerated OpenGL 3.3 Core profile rendering via LTW/Zink/Mesa drivers and low-latency audio via OpenAL Soft with Google Oboe backend.
3. **Ergonomic Multi-Touch Controls**: Natural multi-touch gesture processing that converts taps, drags, and pinches into intuitive mouse and camera interactions.
4. **Convenient Floating HUD**: Quick access overlay for game speed, pause, rotation, in-game menu, and soft keyboard input.
5. **Integrated Mod Manager**: In-app management, safe ZIP installation, and automated classpath injection for player mods.

---

## Requirements Fulfilled

The project fulfills all architectural and functional requirements across Milestones 1 through 5:

| Requirement | Title | Description & Implementation |
|---|---|---|
| **R1** | **MojoLauncher Cleanup & Rebranding** | Completely purged Minecraft-specific logic, authentication services (`authenticator/`), skin renderer, Mojang version downloaders (`mojson/`), and Minecraft configs (`MCOptionUtils`). Rebranded package name and app UI to SoSMobile (`git.artdeell.sosmobile`). Preserved core runtime (`JavaRunner`, `libmojort`, OpenJDK, GLFW, OpenAL, OpenGL). Authentic game distribution remains 100% untouched. |
| **R2** | **Game Folder Selection & ARM64 Launch** | Implemented modern Android storage permissions (`MANAGE_EXTERNAL_STORAGE` / SAF), directory picker with strict validation (`SongsOfSyx.jar` and `base/data.zip`), JVM classpath builder, dynamic RAM tuning, and direct in-process invocation of `init.MainProcess.main()` via JNI. |
| **R3** | **Mod Manager** | In-app Mod Manager that automatically scans `<game_dir>/mods/` and user storage (`~/.local/share/songsofsyx/mods`), parses `_Info.txt` metadata, performs safe ZIP extraction protected against Zip-Slip, and synchronizes active mods to `LauncherSettings.txt` (`"MODS"`) and the runtime classpath. |
| **R4** | **Touch Controls & Gesture System** | Completely eliminated Minecraft virtual buttons and joysticks. Integrated `SyxGestureEventProcessor` supporting single-finger tap (left-click), drag (box selection), two-finger tap / long-press (right-click), two-finger pan (middle-click camera move), and pinch (scroll wheel zoom). Added collapsible `FloatingHUDView` overlay. |
| **R5** | **GitHub Repository & CI/CD** | Clean Git repository structure strictly excluding proprietary game binaries via comprehensive `.gitignore`. Automated GitHub Actions CI workflow (`.github/workflows/android.yml`) compiling full debug APKs with Gradle and generating releases. |

---

## Architecture

SoSMobile operates as a multi-tier bridge connecting the Android OS lifecycle to the desktop Java runtime:

```
+-------------------------------------------------------------------------+
|                               SoSMobile UI                              |
|   [Game Folder Selector]     [Mod Manager Fragment]     [Launcher UI]   |
+-------------------------------------------------------------------------+
                                     │
                                     ▼
+-------------------------------------------------------------------------+
|                            SoSMobile Runtime                            |
|   - Storage & Permission Engine (MANAGE_EXTERNAL_STORAGE / SAF)          |
|   - Path & Asset Integrity Validator (GamePathValidator)                |
|   - Classpath & JVM Parameter Assembly (SyxLaunchConfig)                |
|   - Mod Configuration Synchronizer (SyxModManager & SyxModSettings)     |
+-------------------------------------------------------------------------+
                                     │
                                     ▼
+-------------------------------------------------------------------------+
|                   MojoLauncher Core Engine (Preserved)                  |
|   - JavaRunner: JNI CreateJavaVM invocation & in-process launch         |
|   - OpenJDK 17 ARM64 (aarch64) Multi-Arch Runtime                       |
|   - Native Graphics: libglfw.so, OpenGL 3.3 Core Profile (LTW/Zink)     |
|   - Native Audio: libopenal.so (Google Oboe audio backend)              |
|   - Native Loader: substitutions.json (LWJGL 3.4.1 ARM64 bindings)      |
+-------------------------------------------------------------------------+
                                     │
                                     ▼
+-------------------------------------------------------------------------+
|                       Touch Control & Input Subsystem                   |
|   - SyxGestureEventProcessor: Tap, Drag, Two-Finger Tap/Pan, Pinch Zoom |
|   - FloatingHUDView: Speed (1x-4x), Pause (Space), Rotate (R), Menu(ESC)|
|   - TouchCharInput: Android Soft Keyboard (IME) Bridge                  |
+-------------------------------------------------------------------------+
                                     │
                                     ▼
+-------------------------------------------------------------------------+
|                    Songs of Syx (init.MainProcess)                      |
|                  Authentic Unmodified Game Distribution                 |
+-------------------------------------------------------------------------+
```

### System Components:
1. **`git.artdeell.mojo.launch.SyxLaunchConfig`**: Builds JVM startup parameters, heap allocation (`-Xms`, `-Xmx`), garbage collection (`-XX:+UseCompressedOops`), system properties (`-Duser.dir`, `-Duser.home`, `-Dos.name=Linux`), and the complete classpath array.
2. **`git.artdeell.mojo.launch.GamePathValidator`**: Verifies directory contents, validating `SongsOfSyx.jar` and `base/` directory integrity before launch.
3. **`git.artdeell.mojo.mods.SyxModManager`**: Manages mod discovery, metadata parsing, ZIP installation, safe deletion, and settings persistence.
4. **`git.artdeell.mojo.input.SyxGestureEventProcessor`**: Low-latency gesture recognizer mapping Android `MotionEvent` streams into desktop mouse clicks, movements, and scroll events.
5. **`git.artdeell.mojo.input.FloatingHUDView`**: Translucent overlay providing quick-access game simulation controls.

---

## Hardware & Software Prerequisites

### Device Requirements:
- **Architecture**: 64-bit ARM (`ARM64` / `aarch64`). 32-bit devices are not supported.
- **Operating System**: Android 5.0 (API 21) or higher (Android 11+ recommended).
- **RAM**: Minimum 2 GB (512 MB JVM heap). Recommended 4 GB to 8 GB+ RAM (2048 MB–4096 MB JVM heap).
- **Storage**: At least 2 GB free internal storage.
- **GPU**: OpenGL ES 3.0+ or Vulkan support (for hardware-accelerated Zink/LTW rasterization).

### Game Requirements:
- A legally purchased copy of **Songs of Syx** (available on [Steam](https://store.steampowered.com/app/1162750/Songs_of_Syx/), [GOG](https://www.gog.com/game/songs_of_syx), or [itch.io](https://jh-games.itch.io/songs-of-syx)).

### Build Host Prerequisites:
- **JDK**: OpenJDK 17 or Eclipse Temurin 17.
- **Android SDK**: Build Tools 34.0.0+, Android API Platform 36 (`compileSdk 36`).
- **Android NDK**: NDK version `29.0.14206865` (or compatible NDK 29+).
- **Git**: Version 2.25+ with submodules enabled.

---

## Build Instructions

### 1. Clone Repository
Clone the repository recursively to ensure all native submodule bindings (`glfw`, `sdl`, `mojoexec`) are populated:

```bash
git clone --recursive https://github.com/radfed6-bit/SoSMobile.git
cd SoSMobile
```

If you already cloned without submodules, initialize them manually:
```bash
git submodule update --init --recursive
```

### 2. Compile APK with Gradle
Build the full debug APK using the Gradle wrapper:

```bash
# Grant execution permissions
chmod +x gradlew

# Compile Full Debug APK
./gradlew :app_mojo:assembleFullDebug
```

On Windows (Command Prompt / PowerShell):
```cmd
gradlew.bat :app_mojo:assembleFullDebug
```

### 3. Build Artifact Output
Upon successful compilation, the output APK will be located at:
```
app_mojo/build/outputs/apk/full/debug/app_mojo-full-debug.apk
```

### Additional Build Targets:
- **Assemble Noruntime Variant**: `./gradlew :app_mojo:assembleNoruntimeDebug`
- **Assemble Release Variant**: `./gradlew :app_mojo:assembleFullRelease` (requires configured release keystore)
- **Run Unit Tests**: `./gradlew test`
- **Run E2E Python Test Suite**: `python3 tests/e2e/run_e2e_tests.py --verbose`

---

## User Guide

### 1. Game Files Preparation
1. On your desktop PC, navigate to your installed Songs of Syx game directory:
   - **Steam**: `steamapps/common/Songs of Syx/`
   - **GOG**: `GOG Games/Songs of Syx/`
2. Ensure the directory contains:
   - `SongsOfSyx.jar`
   - `base/` directory (containing `data.zip`)
3. Connect your Android device via USB (or use local network transfer) and copy the entire `Songs of Syx` folder into your device's internal storage, for example:
   ```
   /storage/emulated/0/SongsOfSyx/
   ```

### 2. Storage Permissions
1. Install and open **SoSMobile**.
2. When prompted on Android 11+ (API 30+), grant **All Files Access** (`MANAGE_EXTERNAL_STORAGE`). This permission is required to allow the launcher to read game assets, load mods, and write save games.

### 3. Selecting Game Directory
1. On the SoSMobile main screen, tap **Select Game Directory**.
2. Browse to the folder where you placed the game files (`/storage/emulated/0/SongsOfSyx/`).
3. Tap **Select Current Directory**. SoSMobile will validate the game files and display a confirmation status.

### 4. Launching the Game
1. (Optional) Adjust the allocated RAM slider to fit your device (e.g. 2048 MB or 4096 MB).
2. Tap **Launch Game**.
3. SoSMobile initializes the ARM64 JVM runtime, sets up graphics and audio drivers, and starts Songs of Syx!

---

## Touch Controls & Gestures

SoSMobile replaces complex keyboard/mouse controls with natural mobile multi-touch gestures designed specifically for grand strategy and city-building gameplay:

| Mobile Gesture | Action in Songs of Syx | Desktop Equivalent | Usage / Description |
|---|---|---|---|
| **Single Tap** | Left Click | Left Mouse Button (Button 0) | Select citizens, choose UI menus, click buttons, place single structures or road tiles. |
| **Single-Finger Drag** | Left Button Drag | Left Mouse Button Hold | Box-select military units/workers, designate construction zones, draw walls and crop fields. |
| **Two-Finger Tap** | Right Click | Right Mouse Button (Button 1) | Cancel current building order, deselect tool, close open dialogs and context windows. |
| **Long Press (>350ms)** | Right Click (Alternative) | Right Mouse Button (Button 1) | Quick one-handed alternative to right-click cancellation. |
| **Two-Finger Drag (Pan)** | Middle Click Drag | Middle Mouse Button (Button 2) | Smooth, responsive camera panning across your settlement and world map. |
| **Pinch In / Pinch Out** | Mouse Wheel Scroll | Mouse Scroll Wheel (Up/Down) | Smooth zooming into street level or zooming out to region overview. |

---

## Floating Game HUD

A sleek, translucent **Floating Action Bar** is rendered along the screen edge during gameplay, providing instant access to vital simulation commands without requiring a physical keyboard:

| Icon / Button | Desktop Shortcut | Command | Action Description |
|:---:|:---:|---|---|
| ⏸ / ▶ | `Space` | **Pause / Play** | Instantly freeze or resume the simulation to issue orders or review city alerts. |
| ⚡ **1x – 4x** | `1`, `2`, `3`, `4` | **Simulation Speed** | Cycle through game speeds: 1x (Normal), 2x (Fast), 3x (Very Fast), 4x (Maximum). |
| 🔄 **Rotate** | `R` | **Rotate Structure** | Rotate the orientation of buildings, furniture, and rooms prior to construction. |
| ☰ **Menu** | `Escape` | **Menu / Cancel** | Open the game settings menu, exit screens, or cancel pending placement. |
| ⌨ **Keyboard** | Soft Keyboard (IME) | **Text Input** | Toggle the native Android soft keyboard (`TouchCharInput`) to type city names, citizen titles, or search filters. |
| ↕ **Drag Handle** | — | **Reposition HUD** | Touch and drag vertically to reposition the floating toolbar anywhere along the screen margin. |

The floating bar can also be collapsed into a minimal icon to keep the viewport completely unobstructed.

---

## Mod Management

SoSMobile features a built-in Mod Manager that enables players to customize their gameplay experience:

### Mod Locations:
- Game Mods: `<game_dir>/mods/`
- User Mods: `/sdcard/.local/share/songsofsyx/mods/`

### Features:
1. **Automatic Discovery & Parsing**: Scans installed mods and parses `_Info.txt` to display the mod name, version, author, and description.
2. **One-Tap Activation**: Check or uncheck mods in the Mod Manager list. Enabled mods are automatically updated in `LauncherSettings.txt` under the `"MODS"` array and injected into the JVM launch classpath.
3. **Safe ZIP Installation**: Tap **Install Mod (.zip)** to import downloaded mod archives. The installer checks archive paths to protect against directory traversal attacks (Zip-Slip) before extraction.
4. **Safe Uninstallation**: Easily remove obsolete or incompatible mods with a single tap.

---

## Continuous Integration (CI/CD)

SoSMobile utilizes **GitHub Actions** for automated build validation:
- **Workflow File**: `.github/workflows/android.yml`
- **Triggers**: Automatic execution on push to branches, release tags, pull requests, and manual triggers (`workflow_dispatch`).
- **Pipeline Steps**:
  1. Repository checkout with full recursive submodules (`submodules: recursive`).
  2. Eclipse Temurin OpenJDK 17 setup with Gradle build caching.
  3. Execution of `./gradlew :app_mojo:assembleFullDebug`.
  4. Packaging and uploading of the compiled APK artifact via `actions/upload-artifact@v4`.
  5. Automatic GitHub Release generation attaching the built APK (`softprops/action-gh-release@v2`).

---

## Troubleshooting & FAQ

#### Q: The launcher says "Invalid Game Directory".
Ensure you selected the root folder containing `SongsOfSyx.jar` and the `base/` subfolder (with `data.zip`). Do not select the `base/` folder directly.

#### Q: The game crashes during launch with an OutOfMemoryError.
Open SoSMobile settings and increase the allocated RAM slider. Songs of Syx requires at least 2048 MB on Android, with 3072 MB–4096 MB recommended for larger settlements.

#### Q: Black screen on startup.
Verify that your device runs a 64-bit ARM processor (`ARM64`). Ensure that "All Files Access" is granted in your Android system app permissions.

#### Q: How do I enter text for city names or citizen searches?
Tap the ⌨ (Keyboard) button on the Floating HUD overlay to bring up your Android soft keyboard.

---

## Legal Notices & Credits

### Disclaimer
- **Songs of Syx** is developed and copyrighted by **Jake Versluis / Strange Scaffold / Gamatron AB**. All rights reserved.
- **SoSMobile** is an independent, non-commercial open-source launcher developed by fans. It is **NOT** affiliated with, endorsed by, or sponsored by Jake Versluis or Gamatron AB.
- SoSMobile **DOES NOT** contain, distribute, or pirate any copyrighted game assets, data, sounds, graphics, or compiled binaries of Songs of Syx. Users must acquire a licensed copy of Songs of Syx independently.

### Licensing
- SoSMobile is licensed under the **GNU Lesser General Public License v3.0 (LGPLv3)**.
- See [LICENSE](LICENSE) for the full text of the license.

### Third-Party Components & Acknowledgments:
- [MojoLauncher](https://github.com/MojoLauncher/MojoLauncher) & [PojavLauncher](https://github.com/PojavLauncherTeam/PojavLauncher): LGPLv3 (ARM64 Android JVM runtime and platform bridges)
- [OpenJDK Multi-Arch](https://openjdk.org/): GNU GPLv2 with Classpath Exception
- [LWJGL 3](https://www.lwjgl.org/): BSD-3 License
- [GLFW](https://www.glfw.org/): zlib License
- [SDL](https://www.libsdl.org/): zlib License
- [OpenAL Soft](https://openal-soft.org/): LGPLv2+ License
- [Google Oboe](https://github.com/google/oboe): Apache License 2.0
- [Mesa 3D / Zink / LTW](https://gitlab.freedesktop.org/mesa/mesa): MIT License
- [Holy GL4ES](https://github.com/artdeell/gl4es_extra_extra): MIT License
