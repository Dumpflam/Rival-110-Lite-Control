"""Independent process used by qt_smoke.py to test real second launches."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from PyQt6.QtCore import QCoreApplication
from instance_guard import SingleInstanceGuard, notify_existing


def main():
    app = QCoreApplication([])
    endpoint = sys.argv[1]
    guard = SingleInstanceGuard(name=endpoint)
    if guard.acquire():
        guard.close()
        print('Unexpectedly obtained the existing instance lock', file=sys.stderr)
        return 2
    show = sys.argv[2] == 'SHOW'
    if not notify_existing(name=endpoint, show=show, timeout_ms=1500):
        print('Existing instance did not acknowledge request', file=sys.stderr)
        return 3
    return 0


if __name__ == '__main__':
    sys.exit(main())
