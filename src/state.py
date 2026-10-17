"""Persistent settings and user profiles for Rival 110 Lite Control.

All data lives in the user profile rather than beside the executable so a
single-file PyInstaller build does not lose preferences between launches.
"""
from __future__ import annotations
import copy
import json
import os
import re
import tempfile
from pathlib import Path

APP_NAME = 'Rival110Lite'


def data_dir() -> Path:
    root = os.environ.get('APPDATA') or str(Path.home() / '.config')
    return Path(root) / APP_NAME


DEFAULT_LIGHTING = {
    'effect': 'Rainbow', 'primary': '#357CC8', 'secondary': '#F6F8FF',
    'brightness': 80, 'speed': 45, 'saturation': 90,
    'parameters': {}, 'effect_parameters': {},
    'sequence': [
        {'color': '#ff3838', 'duration': 400, 'transition': 'smooth'},
        {'color': '#49de84', 'duration': 400, 'transition': 'smooth'},
        {'color': '#587eea', 'duration': 400, 'transition': 'smooth'},
    ],
}
DEFAULT_DPI = {'dpi1': 800, 'dpi2': 1600, 'polling': 1000, 'button6': 'dpi'}
DEFAULT_CONFIG = {
    'schema_version': 2,
    'theme': 'Dark', 'accent': '#4C90CE',
    'autostart': True, 'close_to_tray': True, 'start_minimized': False,
    'last_lighting': 'Rainbow', 'last_dpi': '800 / 1600',
    'working_lighting': None,
    'lighting_profiles': {
        'Rainbow': copy.deepcopy(DEFAULT_LIGHTING),
        'Warm Static': {**copy.deepcopy(DEFAULT_LIGHTING), 'effect': 'Static', 'primary': '#FF7D30'},
        'Storm': {**copy.deepcopy(DEFAULT_LIGHTING), 'effect': 'Lightning', 'primary': '#B5DFFF',
                  'parameters': {'frequency': 24, 'flash_ms': 90, 'double_chance': 60, 'background': 4}},
    },
    'dpi_profiles': {
        '800 / 1600': copy.deepcopy(DEFAULT_DPI),
        '800 / 3200': {'dpi1': 800, 'dpi2': 3200, 'polling': 1000, 'button6': 'dpi'},
        '400 / 800': {'dpi1': 400, 'dpi2': 800, 'polling': 1000, 'button6': 'dpi'},
    },
}


def valid_color(value: str) -> bool:
    return isinstance(value, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', value) is not None


def validate_dpi(profile: dict) -> dict:
    if not isinstance(profile, dict):
        raise ValueError('DPI profile must be an object')
    data = {}
    for name in ('dpi1', 'dpi2'):
        value = int(profile[name])
        if value < 200 or value > 7200 or value % 100:
            raise ValueError(f'{name} must be 200-7200 in steps of 100')
        data[name] = value
    rate = int(profile['polling'])
    if rate not in (125, 250, 500, 1000):
        raise ValueError('Polling rate must be 125, 250, 500 or 1000 Hz')
    data['polling'] = rate
    button6 = str(profile.get('button6', 'dpi'))
    if button6 not in ('dpi', 'os'):
        raise ValueError('Button mode must be dpi or os')
    data['button6'] = button6
    return data


def validate_light(profile: dict) -> dict:
    if not isinstance(profile, dict):
        raise ValueError('Lighting profile must be an object')
    output = copy.deepcopy(DEFAULT_LIGHTING)
    effect = profile.get('effect', 'Static')
    if not isinstance(effect, str) or len(effect) > 80:
        raise ValueError('Invalid effect')
    output['effect'] = effect
    for c in ('primary', 'secondary'):
        color = profile.get(c, output[c])
        if not valid_color(color):
            raise ValueError(f'Invalid color: {c}')
        output[c] = color.upper()
    for k in ('brightness', 'speed', 'saturation'):
        value = int(profile.get(k, output[k]))
        if not 0 <= value <= 100:
            raise ValueError(f'{k} must be 0-100')
        output[k] = value
    params = profile.get('parameters', {})
    if not isinstance(params, dict) or len(params) > 100:
        raise ValueError('Invalid effect parameters')
    output['parameters'] = {str(k)[:60]: min(10000, max(0, int(v)))
                            for k, v in params.items()}
    by_effect = profile.get('effect_parameters', {})
    if not isinstance(by_effect, dict) or len(by_effect) > 100:
        raise ValueError('Invalid effect parameter presets')
    clean_effects = {}
    for effect_name, values in by_effect.items():
        if not isinstance(effect_name, str) or len(effect_name) > 80 or not isinstance(values, dict) or len(values) > 100:
            raise ValueError('Invalid effect parameter group')
        clean_effects[effect_name] = {str(k)[:60]: min(10000, max(0, int(v))) for k, v in values.items()}
    output['effect_parameters'] = clean_effects
    steps = profile.get('sequence', output['sequence'])
    if not isinstance(steps, list) or not (1 <= len(steps) <= 100):
        raise ValueError('Sequence must contain between 1 and 100 steps')
    clean = []
    for step in steps:
        color = step['color']
        if not valid_color(color):
            raise ValueError('Invalid sequence color')
        duration = int(step['duration'])
        if not (50 <= duration <= 60000):
            raise ValueError('Sequence duration must be 50-60000 ms')
        transition = step.get('transition', 'smooth')
        if transition not in ('smooth', 'hold'):
            raise ValueError('Invalid sequence transition')
        clean.append({'color': color.upper(), 'duration': duration, 'transition': transition})
    output['sequence'] = clean
    return output


class Store:
    def __init__(self, filename: Path | None = None):
        self.path = filename or (data_dir() / 'settings.json')
        self.data = copy.deepcopy(DEFAULT_CONFIG)
        self.load()

    def load(self):
        for path in (self.path, self.path.with_suffix('.json.bak')):
            if not path.exists():
                continue
            try:
                user = json.loads(path.read_text(encoding='utf-8'))
                if not isinstance(user, dict):
                    continue
                for key in ('theme', 'accent', 'autostart', 'close_to_tray',
                            'start_minimized', 'last_lighting', 'last_dpi'):
                    if key in user:
                        self.data[key] = user[key]
                if self.data['theme'] not in ('Dark', 'Light'):
                    self.data['theme'] = 'Dark'
                if not valid_color(self.data['accent']):
                    self.data['accent'] = '#4C90CE'
                try:
                    if user.get('working_lighting') is not None:
                        self.data['working_lighting'] = validate_light(user['working_lighting'])
                except (ValueError, TypeError, KeyError):
                    pass
                for kind, checker in (('dpi_profiles', validate_dpi),
                                      ('lighting_profiles', validate_light)):
                    valid = {}
                    for name, payload in user.get(kind, {}).items():
                        try:
                            if isinstance(name, str) and 0 < len(name) <= 80:
                                valid[name] = checker(payload)
                        except (ValueError, KeyError, TypeError):
                            continue
                    if valid:
                        self.data[kind] = valid
                for kind, active in (('dpi_profiles', 'last_dpi'),
                                     ('lighting_profiles', 'last_lighting')):
                    if self.data[active] not in self.data[kind]:
                        self.data[active] = next(iter(self.data[kind]))
                return
            except (OSError, json.JSONDecodeError):
                continue

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.data, ensure_ascii=False, indent=2)
        handle, tmp = tempfile.mkstemp(prefix='settings-', suffix='.tmp', dir=self.path.parent)
        try:
            with os.fdopen(handle, 'w', encoding='utf-8') as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            if self.path.exists():
                import shutil
                shutil.copy2(self.path, self.path.with_suffix('.json.bak'))
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def replace_profile(self, kind: str, name: str, profile: dict):
        if kind not in ('dpi_profiles', 'lighting_profiles'):
            raise ValueError('Unknown profile type')
        name = name.strip()
        if not name or len(name) > 80:
            raise ValueError('Name must be 1-80 characters')
        validator = validate_dpi if kind == 'dpi_profiles' else validate_light
        self.data[kind][name] = validator(profile)
        self.save()

    def delete_profile(self, kind: str, name: str):
        profiles = self.data[kind]
        if name not in profiles:
            return
        if len(profiles) == 1:
            raise ValueError('Keep at least one profile')
        del profiles[name]
        active = 'last_dpi' if kind == 'dpi_profiles' else 'last_lighting'
        if self.data[active] == name:
            self.data[active] = next(iter(profiles))
        self.save()
