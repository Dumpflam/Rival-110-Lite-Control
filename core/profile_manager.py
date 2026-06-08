import json
import logging
import copy
from pathlib import Path

from core.config import CONFIG_FILE, PROFILES_FILE, DEFAULT_PROFILE, DEFAULT_PROFILES

logger = logging.getLogger(__name__)


class ProfileManager:
    def __init__(self):
        self._profiles = self._load_profiles()
        self._config = self.load_config()
        self._persist()
        self.save_config(self._config)

    @staticmethod
    def _backup(path: Path) -> None:
        if path.exists() and path.stat().st_size > 0:
            bak = path.with_suffix(".bak")
            bak.write_bytes(path.read_bytes())

    def _load_profiles(self) -> dict:
        for path in (PROFILES_FILE, PROFILES_FILE.with_suffix(".bak")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and data:
                    return data
            except FileNotFoundError:
                continue
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Could not load %s: %s", path.name, e)
        return copy.deepcopy(DEFAULT_PROFILES)

    def list_names(self) -> list[str]:
        return sorted(self._profiles.keys())

    def get(self, name: str) -> dict:
        profile = self._profiles.get(name)
        if profile is None:
            return copy.deepcopy(DEFAULT_PROFILE)
        return copy.deepcopy(profile)

    def set(self, name: str, data: dict) -> None:
        self._profiles[name] = data
        self._persist()

    def delete(self, name: str) -> None:
        if name not in self._profiles:
            return
        if len(self._profiles) <= 1:
            raise ValueError("Cannot delete the last profile")
        del self._profiles[name]
        self._persist()

    def export_profile(self, name: str, path: str) -> None:
        profile = self.get(name)
        data = {"rival_profile_version": 1, "name": name, "data": profile}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def import_profile(self, path: str) -> str:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("rival_profile_version") != 1 or "name" not in data or "data" not in data:
            raise ValueError("Nieprawidłowy format pliku profilu.")
        name = data["name"]
        base = name
        i = 2
        while name in self._profiles:
            name = f"{base} ({i})"
            i += 1
        self.set(name, data["data"])
        return name

    @property
    def active_name(self) -> str:
        name = self._config.get("active_profile")
        if name and name in self._profiles:
            return name
        names = self.list_names()
        return names[0] if names else "Default"

    @active_name.setter
    def active_name(self, name: str) -> None:
        self._config["active_profile"] = name
        self.save_config(self._config)

    def load_config(self) -> dict:
        for path in (CONFIG_FILE, CONFIG_FILE.with_suffix(".bak")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except FileNotFoundError:
                continue
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Could not load %s: %s", path.name, e)
        return {}

    def save_config(self, cfg: dict) -> None:
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            self._backup(CONFIG_FILE)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except IOError as e:
            logger.warning("Could not save config: %s", e)

    def _persist(self) -> None:
        try:
            PROFILES_FILE.parent.mkdir(parents=True, exist_ok=True)
            self._backup(PROFILES_FILE)
            with open(PROFILES_FILE, "w", encoding="utf-8") as f:
                json.dump(self._profiles, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.warning("Could not persist profiles: %s", e)
