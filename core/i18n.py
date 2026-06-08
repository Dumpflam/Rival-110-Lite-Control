import json
import locale
import logging
from pathlib import Path

from core.config import BASE_DIR

LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"
logger = logging.getLogger(__name__)

_strings: dict = {}
_current_lang: str = "en"


def _load(lang: str) -> dict:
    path = LOCALES_DIR / f"{lang}.json"
    if not path.exists():
        logger.warning("Locale file not found: %s", path)
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Could not load locale %s: %s", lang, e)
        return {}


def detect_system_lang() -> str:
    try:
        tag = locale.getdefaultlocale()[0] or "en"
        return tag.split("_")[0].lower()
    except Exception:
        return "en"


def available_languages() -> list[str]:
    return sorted(p.stem for p in LOCALES_DIR.glob("*.json"))


def init(lang: str | None = None) -> None:
    global _strings, _current_lang
    target = lang or detect_system_lang()
    _strings = _load("en")
    if target != "en":
        overlay = _load(target)
        if overlay:
            _strings.update(overlay)
            _current_lang = target
        else:
            _current_lang = "en"
    else:
        _current_lang = "en"


def t(key: str) -> str:
    return _strings.get(key, key)


def current_lang() -> str:
    return _current_lang
