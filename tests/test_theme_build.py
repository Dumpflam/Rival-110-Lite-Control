"""Regression tests for stylesheet generation and packaged preview asset.

Pure Python on purpose: runs before the Windows Qt integration smoke test.
"""
import ast
import json
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_stylesheet_function():
    source = (ROOT / 'src' / 'interface.py').read_text(encoding='utf-8')
    module = ast.parse(source)
    func = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'theme_css')
    namespace = {}
    exec(compile(ast.Module(body=[func], type_ignores=[]), '<theme-css-test>', 'exec'), namespace)
    return namespace['theme_css']


class ThemeBuildTests(unittest.TestCase):
    def test_css_generates_without_errors_in_both_themes(self):
        theme_css = load_stylesheet_function()
        for theme in ('Dark', 'Light'):
            with self.subTest(theme=theme):
                css = theme_css(theme, '#4C90CE')
                self.assertIn('QLineEdit, QSpinBox, QComboBox, QTableWidget {', css)
                self.assertIn('selection-background-color: #4C90CE;', css)
                self.assertIn('QWidget#lightingContent', css)
                self.assertEqual(css.count('{'), css.count('}'))
                self.assertNotIn('{{', css)
                self.assertNotIn('}}', css)
        self.assertIn('background-color: #141820;', theme_css('Dark', '#4C90CE'))
        self.assertIn('background-color: #FFFFFF;', theme_css('Light', '#4C90CE'))

    def test_mouse_image_exists_and_is_png(self):
        data = (ROOT / 'assets' / 'rival110_mouse.png').read_bytes()
        self.assertTrue(data.startswith(b'\x89PNG\r\n\x1a\n'))
        width, height = struct.unpack('>II', data[16:24])
        self.assertGreaterEqual(width, 480)
        self.assertLessEqual(width, 650)  # crop excess source transparency
        self.assertGreaterEqual(height, 900)



    def test_custom_sequence_uses_visual_timeline_not_table(self):
        interface = (ROOT / 'src' / 'interface.py').read_text(encoding='utf-8')
        timeline = (ROOT / 'src' / 'sequence_editor.py').read_text(encoding='utf-8')
        self.assertIn('self.sequence_timeline = SequenceTimeline()', interface)
        self.assertNotIn('self.sequence = QTableWidget(', interface)
        self.assertIn('def sequence_durations_changed(', interface)
        self.assertIn('def duplicate_step(', interface)
        self.assertIn('def move_sequence_step(', interface)
        self.assertIn('def paintEvent(', timeline)
        self.assertIn('durations_changed = pyqtSignal(', timeline)

    def test_registered_led_sprites_match_photo_coordinates(self):
        """Image, masks and Gaussian glow must occupy one coordinate system."""
        metadata = json.loads((ROOT / 'assets' / 'led_regions.json').read_text(encoding='utf-8'))
        base = (ROOT / 'assets' / 'rival110_mouse.png').read_bytes()
        width, height = struct.unpack('>II', base[16:24])
        self.assertEqual((width, height), (metadata['image_width'], metadata['image_height']))
        for name in ('wheel', 'logo'):
            roi = metadata['sprites'][name]
            self.assertGreaterEqual(roi['x'], 0)
            self.assertGreaterEqual(roi['y'], 0)
            self.assertLessEqual(roi['x'] + roi['width'], width)
            self.assertLessEqual(roi['y'] + roi['height'], height)
            for kind in ('core', 'glow'):
                raw = (ROOT / 'assets' / f'rival110_{name}_{kind}.png').read_bytes()
                self.assertTrue(raw.startswith(b'\x89PNG\r\n\x1a\n'))
                dimensions = struct.unpack('>II', raw[16:24])
                self.assertEqual(dimensions, (roi['width'], roi['height']))

    def test_mask_mapping_has_no_glow_stretch_or_manual_offsets(self):
        source = (ROOT / 'src' / 'interface.py').read_text(encoding='utf-8')
        preview = source.split('class MousePreviewWidget(QWidget):', 1)[1].split('def theme_css(', 1)[0]
        self.assertIn("mouse_rect.width() * (region['x'] / sw)", preview)
        self.assertIn("mouse_rect.height() * (region['y'] / sh)", preview)
        self.assertNotIn('offset_x=', preview)
        self.assertNotIn('offset_y=', preview)
        self.assertNotIn('glow_scale=', preview)
        self.assertNotIn('IgnoreAspectRatio', preview)

    def test_radial_gradient_center_uses_numeric_overload(self):
        # Qt6's QRadialGradient(center, radius) accepts QPointF, not QPoint.
        # The safe 3-number overload is explicit and independent of implicit conversions.
        tree = ast.parse((ROOT / 'src' / 'interface.py').read_text(encoding='utf-8'))
        preview = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'MousePreviewWidget')
        # The mask-based lighting no longer creates radial gradients for each LED.
        # Ambient lighting still uses a safe numeric overload.
        radial_calls = [n for n in ast.walk(preview) if isinstance(n, ast.Call)
                        and isinstance(n.func, ast.Name) and n.func.id == 'QRadialGradient']
        self.assertGreaterEqual(len(radial_calls), 1)
        for call in radial_calls:
            # Either three explicit floats (cx, cy, radius), or a QPointF/radius pair.
            safe_numeric = len(call.args) == 3  # positional (cx, cy, radius) overload
            safe_pointf = (len(call.args) == 2 and isinstance(call.args[0], ast.Call)
                           and isinstance(call.args[0].func, ast.Name)
                           and call.args[0].func.id == 'QPointF')
            self.assertTrue(safe_numeric or safe_pointf,
                            f'Unsafe QRadialGradient overload at line {call.lineno}')


    def test_tray_colors_and_submenus_are_explicitly_styled(self):
        source = (ROOT / 'src' / 'interface.py').read_text(encoding='utf-8')
        self.assertIn('def tray_menu_css(', source)
        self.assertIn('QMenu::item:selected', source)
        self.assertIn('for menu in (m, dpi_menu, light_menu, preset_menu):', source)
        self.assertIn('menu.setStyleSheet(style)', source)

    def test_single_instance_guards_app_startup(self):
        source = (ROOT / 'src' / 'main.py').read_text(encoding='utf-8')
        self.assertIn('guard = SingleInstanceGuard()', source)
        self.assertIn('if not guard.acquire():', source)
        self.assertIn('notify_existing(', source)
        self.assertIn('guard.on_open(window.show_window)', source)


    def test_ipc_acknowledgement_replaces_fire_and_forget(self):
        source = (ROOT / 'src' / 'instance_guard.py').read_text(encoding='utf-8')
        self.assertIn('QIODevice.OpenModeFlag.ReadWrite', source)
        self.assertIn('waitForReadyRead(', source)
        self.assertIn("sock.write(b'OK\\n')", source)
        self.assertIn("command == b'SHOW'", source)

    def test_second_instance_test_runs_sender_outside_gui_event_loop(self):
        source = (ROOT / 'tests' / 'qt_smoke.py').read_text(encoding='utf-8')
        self.assertIn('threading.Thread(', source)
        self.assertIn('app.processEvents()', source)
        self.assertIn('notify_from_child_process(', source)
        self.assertTrue((ROOT / 'tests' / 'ipc_client.py').exists())

    def test_windows_builder_bundles_preview_asset(self):
        build = (ROOT / 'build_windows.ps1').read_text(encoding='utf-8')
        self.assertIn('--add-data "$root\\assets;assets"', build)


if __name__ == '__main__':
    unittest.main()
