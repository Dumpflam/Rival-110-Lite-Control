import sys
from pathlib import Path

APP_NAME = "RivalGUI"
AUTORUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG_FILE = BASE_DIR / "config.json"
PROFILES_FILE = BASE_DIR / "profiles.json"

DEFAULT_PROFILE = {
    "colors": {"z1": "#ff0000", "z2": "#00ff00", "z3": "#0000ff"},
    "brightness": 80,
    "effect": "Statyczny",
    "speed": 5,
}

DEFAULT_PROFILES = {"Default": DEFAULT_PROFILE.copy()}

EFFECTS = [
    "Statyczny", "Dwukolorowy", "Wygaszony",
    "Tęcza", "Oddychanie", "Puls Dwukolorowy", "Własny Gradient",
    "Wschód Słońca", "Kometa", "Błyskawica", "Fala Kolorów",
    "Ogień", "Ocean", "Gwiezdna Noc", "Monitor CPU",
    "Własny Sekwencyjny",
]
