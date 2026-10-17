# I DO NOT TAKE CREDIT FOR THIS.
# CHATGPT HAS BEEN USED TO MAKE EVERY PART OF THIS.

# Rival 110 Lite Control — Full Rebuild

A compact, independent, open-source Windows application designed around the **SteelSeries Rival 110** (`USB 1038:1729`). Inspired by [Rival Lite Control](https://github.com/AnonBOTpl/Rival-Lite-Control) by AnonBOTpl, but rebuilt rather than applying brittle text patches to the older three-zone UI. Direct hardware control is provided by [Rivalcfg](https://github.com/flozz/rivalcfg).

**This archive includes complete application source and a Windows EXE builder; it does not contain a precompiled Windows executable.** A native Windows runner is required to package and validate a Windows executable. The EXE it produces does not require Python or SteelSeries GG.

## Build (Windows 10/11)

1. Extract this archive to a **fresh folder**. Do not merge with the old DPI patch / EXE builder.
2. Install Python 3.10 or newer if you do not already have it (from python.org). The installer must put `py` or `python` on PATH.
3. Double-click **`BUILD_EXE.bat`** while connected to the internet.
4. The script installs build dependencies in a *private* `_build/venv`, runs all tests, builds the standalone executable, then places **`Rival110LiteControl.exe`** in the folder beside the BAT file.
5. Copy just the EXE anywhere and launch. **Python is not required to run the EXE.**

The builder runs a **GUI/tray integration test on Windows before compiling**. The transparently cropped Rival 110 photo and separate, pixel-registered wheel/logo lighting sprites are bundled into the EXE. The renderer uses the real illuminated pixels from the source photo: no freehand LED circles, enlarged full-image masks, or manual position offsets. If an import or GUI control has a problem, it fails the build visibly rather than producing a silently broken EXE.

### Alternate build without installing Python locally

Upload the folder contents (including `.github/workflows/`) to a personal GitHub repository, then go to **Actions > Build Rival110LiteControl.exe > Run workflow**. Download the `Rival110LiteControl-Windows` artifact after the job succeeds. Do not redistribute an untested executable as if it were production verified.

## Controls and usage

### Mouse / DPI

- Two independent onboard DPI values **200–7200**, adjustable in **100 DPI** steps.
- Polling rate **125 / 250 / 500 / 1000 Hz**.
- Button behind the scroll wheel: **cycle DPI** or **OS-defined**.
- Named DPI profiles, such as **800 / 1600**, **800 / 3200**, **400 / 800**. Create, update, delete, import and export profiles.
- Selecting a profile from the **tray menu applies the settings immediately** and saves them to mouse memory. The physical DPI switch selects one of the two values.
- Profile restoration on startup/reconnect writes settings **without unnecessarily saving to internal flash memory repeatedly**.
- Optional device factory reset (with confirmation).

### Lighting — one real LED zone

The old app displayed three RGB zones. The Rival 110's documented LED control is **one color command**. Every effect here computes a **single color at each frame**. No nonexistent-zone widgets remain.

The 16 original effect categories are retained in English:

| Effect | New configurable settings / behavior |
|---|---|
| Static | Individual color; brightness level |
| Two-color | Color mix sharpness, pause at colors |
| Off | Switch LED off |
| Rainbow | Hue range, reverse direction |
| Breathing | Minimum glow, softness |
| Two-color Pulse | Minimum glow, transition width |
| Custom Gradient | Intermediate hue shift, dwell |
| Sunrise | Sunrise duration, daylight pause |
| Comet | Flash length, tail decay, secondary streaks |
| Lightning | Strikes/minute, flash length, double-strike chance, background glow; **all flashes use the only LED** |
| Color Wave | Hue span, waveform softness |
| Fire | Flicker intensity, warmth, ember frequency |
| Ocean | Wave depth, hue shift |
| Starry Night | Twinkles/minute, twinkle decay, ambient glow |
| CPU Monitor | Low-load hue, high-load hue, minimum output |
| Custom Sequence | Color-coded timeline; click to select steps, drag diamond separators to adjust neighboring durations, choose color/duration/transition, add/duplicate/delete/reorder; looping and softness |

All software animations also have general **brightness, speed (where meaningful), and saturation** controls. Effect-specific parameter values are remembered independently when you switch effects. Software animations currently use a roughly 40 ms frame timer, with actual USB update timing dependent on Rivalcfg/HID operations.

The app additionally exposes the **documented onboard lighting effect IDs**: Hardware Breath, Hardware Effect 2 and Hardware Effect 4. Hardware modes can run without a background software animation. Rivalcfg documents numeric IDs 2 and 4, but the firmware's appearance for these modes is not described; do not assume they match a specific animation.

Save Static, Off or an onboard effect to the mouse through **Device / Diagnostics > Save current static/breath color to mouse**. Other effects require the app in the tray. **No effect saves LED frames to flash memory.**

### Appearance / startup

- Dark theme by default, optional light theme.
- Square-edged beveled controls, flat rectangular cards, classic Windows-inspired Aero header. No emojis.
- Accent picker plus six quick accent choices for selected tabs, sliders and controls.
- Starts with Windows by default, using **HKCU Run**, and opens to the tray on automatic launches. Disable this in Appearance / Startup.
- Closing the window minimizes to tray by default; right-click the icon to **Exit**, **change DPI profile**, **choose saved lighting**, or **choose any effect preset**. All changes take effect with the app hidden.
- USB reconnects automatically and profiles remain available offline. If another driver/software locks the mouse, close it and use Device / Diagnostics > Reconnect.

### Saved files

Configuration, named DPI and lighting profiles, accent/theme preference, latest working lighting and logs are stored at:

```
%APPDATA%\Rival110Lite\settings.json
%APPDATA%\Rival110Lite\rival110.log
```

Profiles use plain JSON; previous config is backed up automatically. `.rivalprofile` import attempts to translate legacy Polish effect names and choose the old first-zone color (`z1`).

## Limitations / testing status

- This package has passed **31 pure-Python unit tests**, including all effect types, DPI validation, fake HID writes, storage/backup, legacy profile conversion and LED memory-save behavior.
- **The Windows Qt integration test has been written into the build process but cannot be run in the Linux environment used to prepare this package.** It covers startup, UI creation, sliders, sequence editor, theme and tray actions with a mocked Rivalcfg mouse.
- Windows EXE building has not been run here. You will receive a normal error if it fails on your Windows installation.
- **USB interaction on a real SteelSeries Rival 110 has not been hardware-tested.** Preset effects 2 and 4 in particular have vendor-undocumented visual behavior.
- Firmware-specific features not exposed in Rivalcfg's Rival 110 profile (e.g. lift-off distance adjustment, sensor calibration, macros) are **not offered**. No guessed HID packets are sent.
- A signed EXE is **not** provided; Windows SmartScreen may warn on a personally built PyInstaller executable.

## Sources / acknowledgments

- Rival Lite Control project (MIT): https://github.com/AnonBOTpl/Rival-Lite-Control
- Rivalcfg project and Rival 110 device definition: https://flozz.github.io/rivalcfg/devices/rival110.html
- Rivalcfg implements the device's two sensitivities, polling rate, color, light effect, button mode and onboard save command.

This independent rebuild is distributed under MIT. See `LICENSE`. The dependencies retain their own respective licenses.

## Revision r3 — October 16, 2026

Fixes for r2's Windows smoke-test failure:

- Escapes the Qt stylesheet braces correctly (previously caused `NameError: name 'background' is not defined`).
- Adds independent tests evaluating the theme stylesheet for **both Dark and Light**.
- Bundles `assets/rival110_mouse.png` into the PyInstaller EXE using `--add-data`; r2 omitted this and would have shown a missing mouse preview after packaging.
- Fixes the `QPainter.fillRect` radial-gradient call to pass a `QBrush` explicitly.
- Extends the Windows smoke test to verify both mouse-preview images load, render, and follow the Light theme.
- A `QFontDatabase: Cannot find font directory` warning in the headless/offscreen smoke test is non-fatal and is separate from the stylesheet error.

**Historical note:** r3 fixed the earlier stylesheet error. Use the newest r4 builder for the Qt paint crash fix described below.

## Revision r4 — October 16, 2026

This fixes the Windows Qt preview crash that occurred after r3 passed the core tests. Qt6 does not implicitly convert the `QPoint` returned by `QRect.center()` into the `QPointF` expected by `QRadialGradient(center, radius)`. The central background glow now uses the unambiguous three-floating-point-number constructor (`centerX, centerY, radius`). The other two radial gradients already used that overload.

The GUI smoke test has been expanded to **show the window**, force paint events for the **compact and full-size mouse previews** in **Dark and Light** themes, and verify that the large preview hides when the window is narrow. Those GUI tests run on the Windows machine that is building the EXE, before packaging; they have not been run in this Linux development environment. The 25 pure-Python offline tests pass here.

**Historical r4 note:** Extract each new revision into a fresh directory. The optional `QFontDatabase` warning from Qt's offscreen test is not the crash. The build script now points Qt at the system fonts folder during the test when available.

## Revision r7 — October 16, 2026

- Fixed the **r6 test failure**: `test_radial_gradient_center_uses_numeric_overload` now inspects every method of the preview widget, including `_draw_led_overlay`, rather than assuming all radial gradients are declared in `paintEvent`. All 27 offline tests pass.
- Added a **Windows named mutex** (held for the lifetime of the application) to block multiple copies even during initial launch, plus a per-user **Qt local IPC server** to ask an existing tray instance to open its window when the EXE is launched again. A `--tray` background launch will not raise the existing window.
- Applied explicit Qt `QMenu` **stylesheets and foreground palettes**, including every submenu, to correct gray-on-gray or dim tray-menu text. Dark theme uses light text, light theme uses dark text, and selection uses the accent color. Changing the theme refreshes the tray menu.
- Expanded the Windows Qt integration smoke test to check a second instance is rejected, an IPC `SHOW` request reaches the first instance, `PING` does not show it, the lock is released cleanly, and tray text colors follow both themes.

**Important when upgrading:** If you have an **older r6 or earlier EXE running**, first right-click its tray icon and select Exit. That version cannot be prevented by a mutex it was never built to acquire. After installing r7, new r7 launches will enforce single-instance behavior.

The Windows EXE and real USB mouse remain untested in the source author's Linux environment. `BUILD_EXE.bat` runs the Qt integration tests on Windows before freezing the EXE. A failed test stops the build rather than quietly shipping a nonfunctional executable.


## Revision r8 — October 16, 2026

Addresses the r7 Windows build failure `Existing instance did not receive the open command`:

- The previous Qt integration test called the local socket client **synchronously on the same thread** as the running `QLocalServer`. That blocked the Qt event loop, so the first instance couldn't process the request before the sender disconnected.
- The IPC client now waits for a positive `OK` acknowledgment from the running instance. It uses a **read/write socket**, retries during startup, and doesn't claim that a command was delivered just because the pipe connection was established.
- The IPC server buffers newline-terminated requests, dispatches `SHOW` to the existing window callback, and acknowledges handled `SHOW` or `PING` requests. Background `--tray` launches still do not show the window.
- The Windows Qt smoke test now runs the second-instance sender in a **separate thread**, allowing the first app's event loop to run. It additionally spawns a **real second Windows process** to verify cross-process mutex rejection and `SHOW`/`PING` delivery.
- **29 offline tests passed.** Qt's Windows integration tests are still run on your Windows machine by `BUILD_EXE.bat` before compilation; this Linux build environment cannot execute those tests because PyQt6 is not available here.

To upgrade, exit the current instance from its system tray, extract this release into a **fresh folder**, and run `BUILD_EXE.bat`. Existing profiles remain in `%APPDATA%\Rival110Lite`.
