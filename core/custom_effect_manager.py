import json
import logging
from pathlib import Path

from core.config import BASE_DIR
from core.custom_effect import CustomEffect

CUSTOM_EFFECTS_FILE = BASE_DIR / "custom_effects.json"
logger = logging.getLogger(__name__)


class CustomEffectManager:
    def __init__(self):
        self._effects: list[CustomEffect] = self._load()

    def _load(self) -> list[CustomEffect]:
        try:
            with open(CUSTOM_EFFECTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [CustomEffect.from_dict(d) for d in data]
        except FileNotFoundError:
            return []
        except Exception as e:
            logger.warning("Could not load custom effects: %s", e)
            return []

    def _persist(self) -> None:
        try:
            CUSTOM_EFFECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CUSTOM_EFFECTS_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    [e.to_dict() for e in self._effects],
                    f, indent=2, ensure_ascii=False,
                )
        except Exception as e:
            logger.warning("Could not save custom effects: %s", e)

    def list(self) -> list[CustomEffect]:
        return list(self._effects)

    def save(self, effect: CustomEffect) -> None:
        for i, e in enumerate(self._effects):
            if e.name == effect.name:
                self._effects[i] = effect
                self._persist()
                return
        self._effects.append(effect)
        self._persist()

    def delete(self, name: str) -> None:
        self._effects = [e for e in self._effects if e.name != name]
        self._persist()


custom_effect_manager = CustomEffectManager()
