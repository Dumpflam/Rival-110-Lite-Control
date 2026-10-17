"""Rival 110 hardware controller using Rivalcfg's PUBLIC Python API.

No guessed packets and no writes to undocumented settings. Save to onboard
memory is limited to explicit user actions, never to animation frames.
"""
from __future__ import annotations
import logging

log = logging.getLogger(__name__)
VENDOR_ID = 0x1038
PRODUCT_ID = 0x1729


class DeviceError(RuntimeError):
    pass


class Rival110:
    def __init__(self, mouse_factory=None):
        self.mouse_factory = mouse_factory
        self.mouse = None
        self.last_color = None
        self.last_effect = None
        self.last_error = ''

    @property
    def connected(self):
        return self.mouse is not None

    def connect(self):
        if self.mouse is not None:
            return True
        try:
            if self.mouse_factory is None:
                from rivalcfg.mouse import get_mouse
                self.mouse_factory = get_mouse
            self.mouse = self.mouse_factory(vendor_id=VENDOR_ID, product_id=PRODUCT_ID)
            self.last_error = ''
            self.last_color = None
            self.last_effect = None
            return True
        except Exception as exc:
            self.last_error = str(exc)
            log.warning('Rival 110 not available: %s', exc)
            return False

    def disconnect(self):
        mouse, self.mouse = self.mouse, None
        self.last_color = None
        self.last_effect = None
        if mouse:
            try:
                mouse.close()
            except Exception as exc:
                log.warning('Close failed: %s', exc)

    def _execute(self, operation):
        if self.mouse is None:
            raise DeviceError('Rival 110 not connected. Connect the mouse and close SteelSeries GG/Engine.')
        try:
            return operation(self.mouse)
        except Exception as exc:
            self.last_error = str(exc)
            log.exception('USB operation failed')
            self.disconnect()
            raise DeviceError(f'Mouse communication failed: {exc}') from exc

    def apply_dpi(self, profile, persist=True):
        # Call the public generated methods and save ONCE after all four writes.
        from state import validate_dpi
        p = validate_dpi(profile)
        def update(m):
            m.set_sensitivity1(p['dpi1'])
            m.set_sensitivity2(p['dpi2'])
            m.set_polling_rate(p['polling'])
            m.set_btn6_mode(p['button6'])
            if persist:
                m.save()
        self._execute(update)

    def set_led(self, color, effect='steady', persist=False):
        if effect not in ('steady', 'breath', 2, 4):
            raise ValueError('Unsupported lighting mode')
        if not isinstance(color, str) or len(color) != 7 or not color.startswith('#'):
            raise ValueError('Invalid hex color')
        color = color.upper()
        if not persist and self.last_color == color and self.last_effect == effect:
            return
        def update(m):
            if self.last_effect != effect or persist:
                m.set_light_effect(effect)
            if self.last_color != color or persist:
                m.set_color(color)
            if persist:
                m.save()
        self._execute(update)
        self.last_color, self.last_effect = color, effect

    def reset_factory(self):
        def update(m):
            m.reset_settings()
            m.save()
        self._execute(update)
        self.last_effect = self.last_color = None
