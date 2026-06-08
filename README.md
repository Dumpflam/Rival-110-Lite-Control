# Rival Lite Control

A lightweight, open-source control panel for SteelSeries Rival mice on Windows. Built with Python and PyQt6, using the [rivalcfg](https://github.com/flozz/rivalcfg) library for direct HID communication — no SteelSeries GG required.

> 🇵🇱 [Polska wersja README](README-pl.md)

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.4%2B-green)
![Windows](https://img.shields.io/badge/platform-Windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-orange)

---

## Features

- **16 RGB lighting effects** — Static, Two-color, Off, Rainbow, Breathing, Two-color Pulse, Custom Gradient, Sunrise, Comet, Lightning, Color Wave, Fire, Ocean, Starry Night, CPU Monitor, Custom Sequence
- **Custom effect editor** — timeline with keyframes, drag & drop, per-zone color control
- **Profile system** — create, save, load, delete, export and import profiles (`.rivalprofile`)
- **Random effect** — randomizes effect and colors with one click
- **Mouse preview** — live SVG preview of all three LED zones in the sidebar
- **System tray** — minimizes to tray, runs in background
- **Autostart** — optional launch with Windows via registry
- **Eclipse mode** — RGB flash on left mouse button click
- **CPU Monitor** — LED color reacts to CPU usage in real time
- **Multilingual** — auto-detects system language, changeable in Settings
- **Community translations** — add your language by dropping a JSON file in `locales/`

---

## Screenshots

> *<img width="818" height="658" alt="{3FF67E7F-24D8-4E81-8E85-90A6030BE310}" src="https://github.com/user-attachments/assets/4ec9db66-33a7-4503-92d5-d22fd54e46f0" />
* <img width="787" height="504" alt="{D06F5993-6904-4492-A7F4-DADBA732C436}" src="https://github.com/user-attachments/assets/2264aea1-0b46-4371-8b86-54d4013c495c" />


---

## Requirements

- Windows 10 / 11
- Python 3.10+
- A supported SteelSeries Rival mouse (see [rivalcfg supported devices](https://github.com/flozz/rivalcfg#supported-mice))

---

## Installation

```bash
git clone https://github.com/AnonBOTpl/rival-lite-control.git
cd rival-lite-control
pip install -r requirements.txt
python main.py
```

### Build standalone `.exe`

```bash
pip install pyinstaller
python scripts/generate_icon.py   # generate assets/icon.ico first
pyinstaller rival_gui.spec
```

The executable will be in `dist/RivalLiteControl.exe`.

---

## Project structure

```
rival_gui/
├── main.py                        # entry point
├── requirements.txt
├── rival_gui.spec                 # PyInstaller spec
├── assets/
│   └── icon.ico
├── locales/
│   ├── en.json                    # English (default)
│   ├── pl.json                    # Polish
│   └── README.md                  # translation guide
├── core/
│   ├── config.py                  # constants, paths, effect list
│   ├── hid_manager.py             # HID communication (rivalcfg)
│   ├── effect_engine.py           # animation engine, all effects
│   ├── profile_manager.py         # profile CRUD, config load/save
│   ├── custom_effect.py           # keyframe data model
│   ├── custom_effect_manager.py   # custom effect persistence
│   └── i18n.py                    # internationalization
├── ui/
│   ├── main_window.py             # main window, signal wiring
│   ├── effect_grid.py             # effect tile grid
│   ├── effect_panel.py            # per-effect settings panel
│   ├── sidebar.py                 # mouse preview + profile panel
│   ├── bottom_bar.py              # brightness, speed, apply button
│   ├── settings_dialog.py         # settings window
│   ├── keyframe_editor.py         # custom effect editor
│   └── mouse_svg.py               # SVG mouse preview template
└── scripts/
    └── generate_icon.py           # generates assets/icon.ico
```

---

## Adding a translation

1. Copy `locales/en.json` to `locales/xx.json` (e.g. `de.json` for German)
2. Translate all **values** — do not change the **keys**
3. Keep `{placeholders}` exactly as they are
4. Drop the file in the `locales/` folder — the app detects it automatically
5. Submit a pull request 🎉

See `locales/README.md` for full details.

---

## How it works

Rival Lite Control communicates directly with the mouse over USB HID using [rivalcfg](https://github.com/flozz/rivalcfg). All RGB effects are computed in software and pushed to the mouse at up to 30 FPS. Hardware effects (Rainbow) use the mouse's onboard chip for smoother animation.

---

## License

MIT — free to use, modify and distribute.

---

## Credits

- [rivalcfg](https://github.com/flozz/rivalcfg) by flozz — the backbone of HID communication
- Built with [PyQt6](https://pypi.org/project/PyQt6/)
