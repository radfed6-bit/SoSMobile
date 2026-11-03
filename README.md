# SoSMobile

**Android Launcher for Songs of Syx**

[![Platform: ARM64](https://img.shields.io/badge/Platform-ARM64%20%2F%20aarch64-blue.svg)](https://github.com/radfed6-bit/SoSMobile)
[![Release: v0.1.1](https://img.shields.io/badge/Release-v0.1.1-brightgreen.svg)](https://github.com/radfed6-bit/SoSMobile/releases/tag/v0.1.1)
[![Android API](https://img.shields.io/badge/Android-API%2021%2B%20(Recommended%2026%2B)-green.svg)](https://developer.android.com)
[![JDK: OpenJDK 17](https://img.shields.io/badge/JDK-OpenJDK%2017-orange.svg)](https://adoptium.net)
[![License: LGPL v3](https://img.shields.io/badge/License-LGPLv3-brightgreen.svg)](https://www.gnu.org/licenses/lgpl-3.0)

---

## Overview

**SoSMobile** is an open-source Android launcher designed to run the grand strategy and city-builder game **Songs of Syx** natively on modern ARM64 Android devices. 

SoSMobile provides a complete desktop Java runtime environment and translation layer directly on mobile devices without modifying, repackaging, or redistributing the original game binaries.

---

## Key Features

- **Pre-configured Java 17 Runtime**: Uses an optimized OpenJDK 17 ARM64 environment out of the box — ready to play immediately without manual Java installation or downloading.
- **First-Launch Hardware Auto-Configuration**: Automatically analyzes device hardware (available RAM, display resolution, and GPU capabilities) on first launch to configure optimal JVM memory limits, screen scaling, and rendering settings.
- **Tailored Touch Controls**: Multi-touch gesture engine adapted specifically for city-building and strategy gameplay:
  - **Single Tap**: Select citizens, choose tools, place structures (Left Click)
  - **Single-Finger Drag**: Box-selection and zone designation
  - **Two-Finger Tap / Long Press**: Cancel action or open context menu (Right Click)
  - **Two-Finger Drag**: Smooth camera panning across your settlement (Middle Click)
  - **Pinch In / Out**: Smooth camera zoom (Mouse Wheel)
- **Floating In-Game HUD**: Sleek on-screen action bar providing quick access to essential game controls:
  - Pause / Play (`Space`)
  - Simulation Speed cycling (1x, 2x, 3x, 4x)
  - Rotate Structure (`R`)
  - Menu / Cancel (`Esc`)
  - Virtual Keyboard toggle for city and citizen naming
- **Built-in Mod Manager**: Discover, enable/disable, and safely install downloaded mod archives (`.zip`) with automatic classpath configuration.
- **Hardware-Accelerated Graphics & Audio**: Native translation for desktop LWJGL / OpenGL via GL4ES and low-latency audio through OpenAL Soft with the Google Oboe backend.

---

## System Requirements

### Android Device
- **CPU**: 64-bit ARM processor (`ARM64` / `aarch64`). 32-bit devices are not supported.
- **Operating System**: Android 8.0 (API 26) or newer recommended (minimum Android 5.0 / API 21).
- **RAM**: Minimum 3 GB (2048 MB JVM allocation); 4 GB–8 GB+ recommended for large colonies.
- **Storage**: At least 2 GB free internal storage for game data and runtime files.

### Game Files
- A legally purchased copy of **Songs of Syx** (available on [Steam](https://store.steampowered.com/app/1162750/Songs_of_Syx/), [GOG](https://www.gog.com/game/songs_of_syx), or [itch.io](https://jh-games.itch.io/songs-of-syx)).
- Ensure your game directory contains `SongsOfSyx.jar` and the `base/` directory (with `data.zip`).

---

## Quick Start Guide

### 1. Prepare Game Files
1. On your PC, locate your installed Songs of Syx folder:
   - **Steam**: `steamapps/common/Songs of Syx/`
   - **GOG**: `GOG Games/Songs of Syx/`
2. Connect your Android device to your computer via USB (or use wireless file transfer).
3. Copy the entire `Songs of Syx` folder to your device's internal storage (e.g. `/storage/emulated/0/SoSMobile/` or `/storage/emulated/0/SongsOfSyx/`).

### 2. Install & Configure SoSMobile
1. Download and install the latest **SoSMobile** APK (`v0.1.1`) from [GitHub Releases](https://github.com/radfed6-bit/SoSMobile/releases/tag/v0.1.1) on your device.
2. Launch SoSMobile. When prompted on Android 11+, grant **All Files Access** (`MANAGE_EXTERNAL_STORAGE`) so the launcher can read game assets and write save files.
3. On the main screen, tap **Select Game Directory** and navigate to the folder where you placed the game files.
4. Tap **Select Current Directory**. SoSMobile will validate `SongsOfSyx.jar` and `base/data.zip`.

### 3. Launch
1. (Optional) Adjust your allocated memory or resolution in Settings if desired.
2. Tap **Launch Game** to start Songs of Syx!

---

## Building from Source

### Prerequisites
- **JDK**: OpenJDK 17
- **Android SDK**: Build Tools 34.0.0+, Android Platform 36
- **Android NDK**: NDK version `29.0.14206865`
- **Git**: With submodule support

### Compilation Steps
1. Clone the repository recursively to fetch all native submodules:
   ```bash
   git clone --recursive https://github.com/radfed6-bit/SoSMobile.git
   cd SoSMobile
   ```
   *(If already cloned without submodules, run `git submodule update --init --recursive`)*

2. Build the APK using the Gradle wrapper:
   ```bash
   # Linux / macOS
   chmod +x gradlew
   ./gradlew assembleDebug

   # Windows
   gradlew.bat assembleDebug
   ```

3. The generated APK will be available in:
   ```
   app_mojo/build/outputs/apk/full/debug/app_mojo-full-debug.apk
   ```

---

## Troubleshooting & FAQ

#### Q: The launcher reports "Invalid Game Directory".
Ensure you selected the root folder containing `SongsOfSyx.jar` and the `base/` directory (which contains `data.zip`). Do not select the `base/` subfolder directly.

#### Q: The game crashes during startup with OutOfMemoryError.
Open SoSMobile Settings and increase the allocated RAM slider. Songs of Syx typically requires at least 2048 MB on mobile, with 3072 MB–4096 MB recommended for growing settlements.

#### Q: How do I enter text for city names or search bars?
Tap the ⌨ (Keyboard) icon on the Floating HUD overlay along the screen edge to open your Android on-screen keyboard.

#### Q: How do I install mods?
Open the **Mod Manager** from the launcher menu. You can view all installed mods, toggle them on or off, or tap **Install Mod (.zip)** to import downloaded mod archives.

---

## Legal Notices & Credits

### Disclaimer
- **Songs of Syx** is developed and copyrighted by **Jake Versluis / Strange Scaffold / Gamatron AB**. All rights reserved.
- **SoSMobile** is an independent, non-commercial open-source launcher developed by the community. It is **NOT** affiliated with, endorsed by, or sponsored by Jake Versluis or Gamatron AB.
- SoSMobile **DOES NOT** contain, distribute, or pirate any copyrighted game assets, data, sounds, graphics, or compiled binaries of Songs of Syx. Users must independently own a licensed copy of the game.

### License
- SoSMobile is licensed under the **GNU Lesser General Public License v3.0 (LGPLv3)**.
- See the [LICENSE](LICENSE) file for complete details.

### Acknowledgments & Third-Party Components
- [MojoLauncher](https://github.com/MojoLauncher/MojoLauncher) & [PojavLauncher](https://github.com/PojavLauncherTeam/PojavLauncher): LGPLv3 (Android JVM runtime framework and bridges)
- [OpenJDK Multi-Arch](https://openjdk.org/): GNU GPLv2 with Classpath Exception
- [LWJGL 3](https://www.lwjgl.org/): BSD-3 License
- [GLFW](https://www.glfw.org/): zlib License
- [SDL](https://www.libsdl.org/): zlib License
- [OpenAL Soft](https://openal-soft.org/): LGPLv2+ License
- [Google Oboe](https://github.com/google/oboe): Apache License 2.0
- [Holy GL4ES](https://github.com/artdeell/gl4es_extra_extra): MIT License
- [Mesa 3D](https://gitlab.freedesktop.org/mesa/mesa): MIT License
