# Rival 110 Lite Control

A lightweight, open-source Windows application for configuring the **SteelSeries Rival 110** without SteelSeries GG. Adjust DPI and polling rate, create RGB animations, save profiles, and switch settings from the system tray.

> **AI use and attribution:** This rebuild was created using ChatGPT. I do not claim credit for the original [Rival Lite Control](https://github.com/AnonBOTpl/Rival-Lite-Control) project by AnonBOTpl or for [Rivalcfg](https://github.com/flozz/rivalcfg), which provides the mouse-control functionality. This is an unofficial community project, not affiliated with SteelSeries.

## Compatibility

- **Mouse:** SteelSeries Rival 110 (USB vendor/product ID `1038:1729`)
- **Operating system:** Windows 10 or 11
- **For building:** Python 3.10+ and an internet connection
- **For running the built EXE:** No Python installation or SteelSeries GG required

The software is designed specifically for the Rival 110. Other SteelSeries models are not supported by this interface.

## Features

### Mouse settings

- Two onboard DPI stages, each adjustable from **200 to 7,200 DPI** in steps of 100
- Polling rates of **125, 250, 500, and 1,000 Hz**
- DPI button mode: switch between DPI stages or use OS-defined button input
- Named DPI profiles (for example, `800 / 1600` and `800 / 3200`)
- Save settings to the mouse, import/export profiles, and reset device settings with confirmation

### Single-zone RGB lighting

The Rival 110 uses **one controllable lighting zone**. Animations generate one color at a time, rather than pretending the mouse has multiple independent RGB zones.

The software includes **16 lighting effects**: Static, Two-color, Off, Rainbow, Breathing, Two-color Pulse, Custom Gradient, Sunrise, Comet, Lightning, Color Wave, Fire, Ocean, Starry Night, CPU Monitor, and Custom Sequence.

Effects have brightness and saturation controls, speed where applicable, and their own additional settings. For example, Lightning supports strike frequency, flash length, double-strike probability, and background glow.

**Custom Sequence** uses a visual, color-coded timeline:

1. Click a colored segment to select a keyframe.
2. Choose its color, duration, and **Smooth fade** or **Hold color** transition.
3. Drag the diamond between segments to redistribute duration between neighboring steps.
4. Add, duplicate, delete, or move steps left/right. Adjust looping and transition softness in the effect options.

Sequences support up to **100 steps**, with durations from **50 ms to 60,000 ms** per step.

**Software animations need the application running** (it can stay in the tray). Static colors and the supported onboard hardware modes can be saved to the mouse. The app also exposes Hardware Breath and firmware effect IDs 2 and 4, whose exact visual behavior is not documented by the project.

### Live mouse visualization

- Large Rival 110 preview on the right; compact preview when the window is too narrow
- LED colors visualized using pixel-aligned masks derived from the actual illuminated wheel and logo in the reference mouse photo
- Separate dark and light appearances, with a natural mouse-body reflection
- Preview follows the current animation

### Windows interface and tray

- Classic Windows-inspired, square-edged interface with **dark theme by default**, optional light theme, and selectable accent colors
- Save, select, import, and export lighting profiles
- Switch DPI profiles, saved lighting profiles, and effects from the **system tray** without opening the window
- Optional **Start with Windows** (enabled by default); automatic launches start in the tray
- Closing the window minimizes to the tray by default; use **Exit** in the tray menu to quit
- Single-instance protection: launching the app again opens the existing instance instead of starting another
- Automatic USB reconnect attempts when the mouse is disconnected

## Build a Windows executable

This repository contains the **source code and EXE builder**, not a precompiled executable.

### Build locally

1. Clone this repository or choose **Code → Download ZIP** on GitHub, then extract it.
2. Install [Python 3.10 or newer](https://www.python.org/downloads/) if necessary. Ensure `py` or `python` is available on your PATH.
3. In the repository's root folder, double-click **`BUILD_EXE.bat`**.
4. Wait for the dependency installation, Python tests, Qt GUI/tray integration test, and PyInstaller build.
5. When the build succeeds, run **`Rival110LiteControl.exe`** from the same folder.

The builder uses an isolated `_build/venv` and bundles the required dependencies and mouse-preview assets into a single Windows executable. You do not need Python on the machine where you run the finished EXE.

## Using the application

**Mouse / DPI:** Enter the two DPI stages, select polling rate and button behavior, then choose **Apply & Save to Mouse**. Save named profiles if you want to switch among configurations quickly.

**Lighting:** Choose an effect, edit its colors and parameters, then save it as a lighting profile. For continuous animation, leave the app running in the system tray.

**Device / Diagnostics:** Reconnect the mouse, save supported onboard lighting, or inspect connection information.

**Appearance / Startup:** Switch themes, choose an accent color, and control startup and tray behavior.

If your Rival 110 cannot be opened, exit **SteelSeries GG / Engine** or any other program that may be accessing the same device, then use **Reconnect Rival 110**.

## Profiles and settings

Settings and profiles are saved separately from the EXE, so replacing the application does not normally remove them:

```text
%APPDATA%\Rival110Lite\settings.json
%APPDATA%\Rival110Lite\rival110.log
```

Profiles are stored as JSON and can be imported or exported. The application also attempts to import older `.rivalprofile` files, translating recognized legacy effect names and using the old first lighting zone's color. A backup of the previous settings file is kept automatically.

If you move the EXE after enabling Windows autostart, disable and re-enable **Start with Windows** to update the stored path.

## Limitations and testing

- The current **r17** source passed **32 offline Python tests** covering effects, settings, device commands using mock hardware, and regression checks.
- The Windows builder also runs a Qt GUI/tray integration test before packaging. These tests cannot replace testing on a physical mouse.
- Real-world USB behavior depends on the Rival 110, its firmware, Rivalcfg, and other software accessing the device. Hardware and Windows configurations have not been exhaustively validated.
- Lift-off distance, sensor calibration, macros, and other features not provided through Rivalcfg's Rival 110 API are not implemented. The app does not send speculative HID commands.
- The generated EXE is unsigned; Windows SmartScreen may warn when you run it.
- This is a **PyInstaller one-file application**, so its first launch can take longer while bundled files are extracted.

## Credits and license

- **[Rival Lite Control](https://github.com/AnonBOTpl/Rival-Lite-Control)** by AnonBOTpl — original project and inspiration (MIT)
- **[Rivalcfg](https://github.com/flozz/rivalcfg)** by flozz and contributors — SteelSeries device-control library; [Rival 110 device reference](https://flozz.github.io/rivalcfg/devices/rival110.html)
- **ChatGPT** — used to create the source code, UI, assets processing, tests, and documentation for this rebuild

This rebuild is provided under the **MIT License**; see [LICENSE](LICENSE). Dependencies and upstream projects retain their respective licenses and attribution requirements.
