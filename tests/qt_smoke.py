"""Windows build-time Qt smoke test; exercises tray actions with mocked USB mouse."""
import os
import sys
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path
from unittest.mock import Mock

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor, QPalette
from state import Store
from device import Rival110
from interface import Window
from instance_guard import SingleInstanceGuard, notify_existing


def action(menu, submenu_title, action_label):
    group = next(a.menu() for a in menu.actions() if a.menu() and a.text() == submenu_title)
    return next(a for a in group.actions() if a.text().startswith(action_label))



def notify_from_other_process_thread(app, *, endpoint: str, show: bool = True) -> bool:
    """Simulate a second process without freezing the first instance's Qt loop.

    A synchronous call on this thread would block newConnection and readyRead,
    which is precisely what made the previous r7 smoke test fail.
    """
    received = []
    finished = threading.Event()

    def send():
        try:
            received.append(notify_existing(name=endpoint, show=show, timeout_ms=1500))
        finally:
            finished.set()

    thread = threading.Thread(target=send, name='second-instance-client', daemon=True)
    thread.start()
    deadline = time.monotonic() + 6.0
    while not finished.is_set() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert finished.is_set(), 'Second-instance sender timed out waiting for acknowledgement'
    thread.join(timeout=1)
    app.processEvents()
    assert len(received) == 1, 'Second-instance sender returned no result'
    return received[0]


def notify_from_child_process(app, *, endpoint: str, show: bool = True) -> None:
    """Actually spawn a second Windows process to test mutex + IPC together."""
    child = Path(__file__).with_name('ipc_client.py')
    command = [sys.executable, str(child), endpoint, 'SHOW' if show else 'PING']
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    deadline = time.monotonic() + 9.0
    while proc.poll() is None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    if proc.poll() is None:
        proc.kill()
    stdout, stderr = proc.communicate(timeout=3)
    assert proc.returncode == 0, (
        f'Real second process failed (exit {proc.returncode}): '
        f'{stderr.decode(errors="replace")} {stdout.decode(errors="replace")}')
    app.processEvents()

def main():
    with tempfile.TemporaryDirectory() as scratch:
        app = QApplication([])
        mouse = Mock()
        dev = Rival110(lambda **kwargs: mouse)
        window = Window(store=Store(Path(scratch) / 'profile.json'), device=dev)
        assert window.device.connected
        assert window.animator.profile['effect'] in ('Rainbow', 'Static')
        assert window.effect_combo.count() >= 16
        assert not window.preview.pixmap.isNull(), 'Compact mouse preview asset missing'
        assert not window.side_preview.pixmap.isNull(), 'Large mouse preview asset missing'
        # Pixel-level regression: the dark shell must stay fully opaque against
        # both light and dark UI backgrounds. Older assets lost this silhouette,
        # making light mode turn half of the mouse white.
        photo = window.side_preview.pixmap.toImage()
        for sx, sy in ((156, 400), (226, 520), (276, 670), (356, 420)):
            assert photo.pixelColor(sx, sy).alpha() >= 245, (
                f'Mouse shell unexpectedly transparent at {(sx, sy)}')
        assert photo.pixelColor(5, 500).alpha() == 0, 'Reference background not transparent'
        assert photo.pixelColor(256, 920).red() < 120, 'Original logo has unremoved brightness'
        for preview in (window.preview, window.side_preview):
            for led in ('wheel', 'logo'):
                for kind in ('core', 'glow'):
                    assert not preview.led_sprites[led][kind].isNull(), f'{led} {kind} mask missing'
                    region = preview.regions[led]
                    asset = preview.led_sprites[led][kind]
                    assert (asset.width(), asset.height()) == (region['width'], region['height']), (
                        f'{led} {kind} sprite and coordinates disagree')
        assert 'QWidget#lightingContent' in window.styleSheet()
        window.set_effect('Lightning')
        assert len(window.param_sliders) >= 4
        window.param_sliders['frequency'].setValue(66)
        assert window.working['parameters']['frequency'] == 66
        window.set_effect('Custom Sequence')
        assert len(window.sequence_timeline.steps) == 3
        window.add_step()
        assert len(window.sequence_timeline.steps) == 4
        assert window.sequence_selected == 1
        window.sequence_duration.setValue(850)
        assert window.working['sequence'][1]['duration'] == 850
        window.sequence_transition.setCurrentIndex(window.sequence_transition.findData('hold'))
        assert window.working['sequence'][1]['transition'] == 'hold'
        before = [s['color'] for s in window.working['sequence']]
        window.move_sequence_step(1)
        assert window.working['sequence'][2]['color'] == before[1]
        window.sequence_durations_changed(1, 640, 210)
        assert window.working['sequence'][1]['duration'] == 640
        assert window.working['sequence'][2]['duration'] == 210
        window.duplicate_step()
        assert len(window.sequence_timeline.steps) == 5
        window.remove_step()
        assert len(window.sequence_timeline.steps) == 4
        window.set_accent('#4578AB')
        window.theme.setCurrentText('Light')
        assert window.store.data['theme'] == 'Light'
        assert '#172332' in window._tray_menu.styleSheet(), 'Light tray text must be dark'
        assert window._tray_menu.palette().color(QPalette.ColorRole.WindowText) == QColor('#172332')
        assert window.preview.theme == 'Light'
        assert window.side_preview.theme == 'Light'
        # Force both previews to receive real offscreen paint events at multiple
        # widths and themes. Exceptions in paintEvent can abort a Qt application.
        window.resize(1260, 820)
        window.show()
        app.processEvents()
        assert window.preview_panel.isVisible(), 'Wide layout should show the right-side mouse'
        for theme in ('Dark', 'Light'):
            window.theme.setCurrentText(theme)
            window.animation_tick()
            app.processEvents()
            assert not window.preview.grab().isNull(), f'Compact preview failed in {theme}'
            assert not window.side_preview.grab().isNull(), f'Large preview failed in {theme}'
        window.theme.setCurrentText('Dark')
        assert '#E7EFF9' in window._tray_menu.styleSheet(), 'Dark tray text must be light'
        assert window._tray_menu.palette().color(QPalette.ColorRole.WindowText) == QColor('#E7EFF9')
        for submenu in [a.menu() for a in window._tray_menu.actions() if a.menu()]:
            assert '#E7EFF9' in submenu.styleSheet(), 'Submenu colors must match theme'
        window.resize(900, 670)
        app.processEvents()
        assert not window.preview_panel.isVisible(), 'Narrow layout should hide large mouse'
        assert not window.preview.grab().isNull(), 'Compact preview missing in narrow layout'
        window.refresh_tray()
        action(window._tray_menu, 'DPI profiles', '800 / 3200').trigger()
        assert mouse.set_sensitivity2.call_args.args[0] == 3200
        assert window.store.data['last_dpi'] == '800 / 3200'
        action(window._tray_menu, 'Saved lighting profiles', 'Storm').trigger()
        assert window.working['effect'] == 'Lightning'
        action(window._tray_menu, 'Lighting presets', 'Fire').trigger()
        assert window.working['effect'] == 'Fire'
        # Each test uses an isolated endpoint so the normal installed
        # application can remain running while the user builds a new version.
        endpoint = f'Rival110LiteSmoke_{uuid.uuid4().hex}'
        first = SingleInstanceGuard(name=endpoint)
        assert first.acquire(), 'First instance must own its lock'
        second = SingleInstanceGuard(name=endpoint)
        assert not second.acquire(), 'Second instance must be refused'
        opens = []
        first.on_open(lambda: opens.append(True))
        assert notify_from_other_process_thread(app, endpoint=endpoint), (
            'Second instance did not receive ACK for the open-window command')
        assert opens, 'Existing instance did not execute the open-window command'
        assert notify_from_other_process_thread(app, endpoint=endpoint, show=False), (
            'Silent tray launch did not receive ACK')
        assert len(opens) == 1, 'A background startup attempt must not raise the window'
        if sys.platform == 'win32':
            # Native named mutexes and local pipe names must also work across
            # separate processes, not merely separate threads.
            notify_from_child_process(app, endpoint=endpoint, show=True)
            assert len(opens) == 2, 'Real second process did not raise existing window'
            notify_from_child_process(app, endpoint=endpoint, show=False)
            assert len(opens) == 2, 'Real background launch unexpectedly raised the window'
        first.close()
        third = SingleInstanceGuard(name=endpoint)
        assert third.acquire(), 'Lock must be released after exit'
        third.close()
        window.exit_app()
        app.processEvents()
        print('PASS: Windows UI/tray/profile and single-instance interactions')


if __name__ == '__main__':
    main()
