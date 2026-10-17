"""Offline tests for profile persistence, all 17 effects and Rivalcfg commands."""
import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from state import Store, validate_light, validate_dpi, DEFAULT_LIGHTING, DEFAULT_DPI
from device import Rival110, DeviceError
from effects import Animator, EFFECT_NAMES, PARAMETERS, fromhex
from legacy import convert_old_lighting


class DeviceTests(unittest.TestCase):
    def setUp(self):
        self.mouse = Mock()
        self.device = Rival110(lambda **kwargs: self.mouse)
        self.assertTrue(self.device.connect())

    def test_ids_and_connection(self):
        self.device.disconnect()
        f = Mock(return_value=self.mouse)
        d = Rival110(f)
        self.assertTrue(d.connect())
        f.assert_called_once_with(vendor_id=0x1038, product_id=0x1729)

    def test_all_mouse_settings_saved_once(self):
        self.device.apply_dpi({'dpi1':800, 'dpi2':3200, 'polling':500, 'button6':'dpi'})
        self.mouse.set_sensitivity1.assert_called_once_with(800)
        self.mouse.set_sensitivity2.assert_called_once_with(3200)
        self.mouse.set_polling_rate.assert_called_once_with(500)
        self.mouse.set_btn6_mode.assert_called_once_with('dpi')
        self.mouse.save.assert_called_once()

    def test_no_nonsense_three_zone_calls(self):
        self.device.set_led('#FEEACA')
        self.mouse.set_color.assert_called_once_with('#FEEACA')
        self.mouse.set_light_effect.assert_called_once_with('steady')
        self.assertFalse(hasattr(self.device, 'set_colors'))

    def test_animations_never_save_flash(self):
        self.device.set_led('#00ABCD')
        self.device.set_led('#00ABCD')
        self.device.set_led('#00ABCE')
        self.assertEqual(self.mouse.set_color.call_count, 2)
        self.mouse.save.assert_not_called()

    def test_hardware_breath_and_save(self):
        self.device.set_led('#235678', 'breath', persist=True)
        self.mouse.set_light_effect.assert_called_with('breath')
        self.mouse.save.assert_called_once()

    def test_native_effect_four(self):
        self.device.set_led('#FFFFFF', 4)
        self.mouse.set_light_effect.assert_called_once_with(4)

    def test_invalid_dpi_never_written(self):
        with self.assertRaises(ValueError):
            self.device.apply_dpi({'dpi1':750, 'dpi2':200, 'polling':1000, 'button6':'dpi'})
        self.mouse.set_sensitivity1.assert_not_called()

    def test_disconnect_on_failure(self):
        self.mouse.set_polling_rate.side_effect = OSError('HID lost')
        with self.assertRaises(DeviceError):
            self.device.apply_dpi(DEFAULT_DPI)
        self.assertFalse(self.device.connected)


class EffectTests(unittest.TestCase):
    def setUp(self):
        self.engine = Animator()

    def test_every_effect_outputs_single_valid_color(self):
        self.assertGreaterEqual(len(EFFECT_NAMES), 16)
        for effect in EFFECT_NAMES:
            profile = copy.deepcopy(DEFAULT_LIGHTING)
            profile['effect'] = effect
            self.engine.configure(profile, now=0)
            for now in (0, .075, .15, .4, 1, 2, 6, 30):
                with self.subTest(effect=effect, time=now):
                    output = self.engine.sample(now)
                    self.assertRegex(output.color, r'^#[0-9A-F]{6}$')
                    self.assertIn(output.hardware, ('steady', 'breath', 2, 4))

    def test_lightning_strikes_on_single_led(self):
        rng = Mock()
        rng.expovariate.return_value = .05
        rng.random.return_value = 0.0
        self.engine = Animator(rng)
        p = copy.deepcopy(DEFAULT_LIGHTING)
        p['effect'] = 'Lightning'
        p['parameters'] = {'frequency':180, 'flash_ms':200, 'double_chance':100, 'background':2}
        self.engine.configure(p, now=0)
        idle = self.engine.sample(0).color
        strike = self.engine.sample(.1).color
        self.assertNotEqual(idle, strike)
        self.assertRegex(strike, r'^#[0-9A-F]{6}$')

    def test_rainbow_moves_over_time(self):
        p = copy.deepcopy(DEFAULT_LIGHTING)
        p['effect'] = 'Rainbow'
        self.engine.configure(p, now=0)
        first = self.engine.sample(0).color
        next_ = self.engine.sample(.5).color
        self.assertNotEqual(first, next_)

    def test_static_stays_static(self):
        p = copy.deepcopy(DEFAULT_LIGHTING)
        p['effect'] = 'Static'
        self.engine.configure(p, now=0)
        self.assertEqual(self.engine.sample(0).color, self.engine.sample(50).color)

    def test_sequence_hold(self):
        p = copy.deepcopy(DEFAULT_LIGHTING)
        p['effect'] = 'Custom Sequence'
        p['brightness'] = 100
        p['saturation'] = 100
        p['speed'] = 45
        p['parameters'] = {'loop': 1, 'softness': 100}
        p['sequence'] = [{'color':'#FF0000', 'duration':500,'transition':'hold'},
                         {'color':'#0000FF', 'duration':500,'transition':'hold'}]
        self.engine.configure(p, now=0)
        self.assertEqual(self.engine.sample(.1).color, '#FF0000')
        self.assertEqual(self.engine.sample(.75).color, '#0000FF')

    def test_custom_sequence_nonloop_keeps_last_color(self):
        p = copy.deepcopy(DEFAULT_LIGHTING)
        p.update(effect='Custom Sequence', speed=45, brightness=100, saturation=100,
                 parameters={'loop':0, 'softness':100},
                 sequence=[{'color':'#AA0000','duration':100,'transition':'smooth'},
                           {'color':'#0000AA','duration':100,'transition':'smooth'}])
        self.engine.configure(p, now=0)
        self.assertEqual(self.engine.sample(5).color, '#0000AA')

    def test_slider_schemas_valid(self):
        for name, fields in PARAMETERS.items():
            for _, key, lo, hi, default, suffix in fields:
                with self.subTest(effect=name, param=key):
                    self.assertLessEqual(lo, default)
                    self.assertLessEqual(default, hi)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'settings.json'

    def tearDown(self):
        self.temp.cleanup()

    def test_legacy_profile_import(self):
        old = {'effect': 'Błyskawica', 'colors': {'z1':'#ABABAB', 'z2':'#FFFFFF', 'z3':'#000000'},
               'brightness': 70, 'speed': 5}
        converted = convert_old_lighting(old)
        self.assertEqual(converted['effect'], 'Lightning')
        self.assertEqual(converted['primary'], '#ABABAB')
        self.assertEqual(converted['speed'], 50)

    def test_effect_settings_survive_validation(self):
        p = copy.deepcopy(DEFAULT_LIGHTING)
        p['parameters'] = {'frequency':60}
        p['effect_parameters'] = {'Lightning':{'frequency':60}, 'Starry Night':{'frequency':25}}
        q = validate_light(p)
        self.assertEqual(q['effect_parameters']['Starry Night']['frequency'], 25)

    def test_save_load_profiles_and_theme(self):
        store = Store(self.path)
        p = {'dpi1':800, 'dpi2':3200, 'polling':125, 'button6':'os'}
        store.replace_profile('dpi_profiles', 'My Gaming', p)
        store.data['last_dpi'] = 'My Gaming'
        store.data['theme'] = 'Light'
        store.data['accent'] = '#ABCDEF'
        store.data['working_lighting'] = copy.deepcopy(DEFAULT_LIGHTING)
        store.save()
        other = Store(self.path)
        self.assertEqual(other.data['dpi_profiles']['My Gaming'], p)
        self.assertEqual(other.data['theme'], 'Light')
        self.assertEqual(other.data['working_lighting']['effect'], 'Rainbow')

    def test_backup_fallback(self):
        store = Store(self.path)
        store.save()
        store.data['theme'] = 'Light'
        store.save()
        self.path.write_text('{malformed', encoding='utf-8')
        restored = Store(self.path)
        self.assertEqual(restored.data['theme'], 'Dark')

    def test_invalid_dpi_profile_rejected(self):
        with self.assertRaises(ValueError):
            validate_dpi({'dpi1':810, 'dpi2':1600,'polling':1000})

    def test_keep_one_profile(self):
        store = Store(self.path)
        store.data['dpi_profiles'] = {'only': DEFAULT_DPI}
        with self.assertRaises(ValueError):
            store.delete_profile('dpi_profiles', 'only')


if __name__ == '__main__':
    unittest.main(verbosity=2)

