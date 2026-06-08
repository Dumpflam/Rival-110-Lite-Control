# Changelog

## [4.1.0] — 2026-06-08

### Added
- Option to restore factory mouse animation on exit (enabled by default) —
  Settings → "Restore factory animation on exit"
- Linux compatibility guard for `winreg` — autostart and Eclipse mode
  gracefully disabled on non-Windows platforms
- Platform support table in README

### Fixed
- `PyQt6-Qt6Svg` package name corrected in `requirements.txt`
- `__pycache__` pattern cleaned up in `.gitignore`

### Notes
- Thanks to [ehiggs](https://www.reddit.com/user/ehiggs/) on Reddit for
  the Linux feedback, winreg bug report, and the ProfileManager
  constructor tip. Great catch!
