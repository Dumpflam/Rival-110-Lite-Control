"""Rival 110 Lite Control application entry point."""
import logging
import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
from state import Store, data_dir
from interface import Window
from instance_guard import SingleInstanceGuard, notify_existing
import startup


def main():
    folder = data_dir()
    folder.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=folder / 'rival110.log', level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(name)s %(message)s')
    app = QApplication(sys.argv)
    app.setApplicationName('Rival 110 Lite Control')
    app.setQuitOnLastWindowClosed(False)

    # The mutex prevents a race during application startup. The local socket
    # asks the existing copy to show its window instead of creating another.
    guard = SingleInstanceGuard()
    if not guard.acquire():
        acknowledged = notify_existing(show='--tray' not in sys.argv, timeout_ms=350, attempts=3)
        if not acknowledged:
            logging.warning('Existing Rival 110 instance did not acknowledge the open request.')
        return 0
    app.aboutToQuit.connect(guard.close)

    store = Store()
    if sys.platform == 'win32' and store.data['autostart']:
        try:
            startup.set_enabled(True)
        except OSError as exc:
            logging.warning('Windows autostart could not be enabled: %s', exc)
    window = Window(store=store)
    guard.on_open(window.show_window)
    # Tray launcher always hides; user-requested preference hides manual startup.
    tray_requested = '--tray' in sys.argv
    if not (QSystemTrayIcon.isSystemTrayAvailable() and
            (tray_requested or store.data['start_minimized'])):
        window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
