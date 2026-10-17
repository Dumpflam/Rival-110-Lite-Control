"""Windows user autostart: user-scoped, no admin, no scheduled service."""
from __future__ import annotations
import os
import sys
from pathlib import Path

REG_PATH = r'Software\Microsoft\Windows\CurrentVersion\Run'
NAME = 'Rival110LiteControl'


def command_line():
    if getattr(sys, 'frozen', False):
        exe = sys.executable
        return f'"{exe}" --tray'
    entry = Path(__file__).parent / 'main.py'
    # Development startup is possible, but EXE build is the recommended target.
    return f'"{sys.executable}" "{entry}" --tray'


def get_enabled():
    if os.name != 'nt':
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
            value, _ = winreg.QueryValueEx(key, NAME)
            return value == command_line()
    except FileNotFoundError:
        return False


def set_enabled(enabled):
    if os.name != 'nt':
        raise RuntimeError('Start with Windows is only available on Windows')
    import winreg
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, NAME, 0, winreg.REG_SZ, command_line())
        else:
            try:
                winreg.DeleteValue(key, NAME)
            except FileNotFoundError:
                pass
