import sys
import logging
import traceback
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from core.i18n import init as i18n_init
from core.profile_manager import ProfileManager
from ui.main_window import MainWindow

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("rival_gui.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

DARK_QSS = """
QMainWindow, QWidget {
    background-color: #121212;
    color: #e0e0e0;
}

QPushButton {
    background-color: #1e3a5f;
    color: #e0e0e0;
    border: 1px solid #2a5a8f;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 12px;
}
QPushButton:hover  { background-color: #2a5a8f; }
QPushButton:pressed { background-color: #0f2440; }

QPushButton#btn_apply {
    background-color: #0088cc;
    color: #ffffff;
    font-weight: bold;
    font-size: 14px;
    padding: 10px;
}
QPushButton#btn_apply:hover  { background-color: #0099dd; }
QPushButton#btn_apply:pressed { background-color: #006699; }

QPushButton#btn_settings {
    background-color: #2a2a2a;
    border: 1px solid #3a3a3a;
    font-size: 16px;
    padding: 6px 10px;
}
QPushButton#btn_settings:hover { background-color: #3a3a3a; }

QComboBox {
    background-color: #1e3a5f;
    color: #e0e0e0;
    border: 1px solid #2a5a8f;
    padding: 4px 8px;
    border-radius: 5px;
}
QComboBox:hover { border: 1px solid #3a7abf; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow {
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #e0e0e0;
    margin-right: 6px;
}
QComboBox QAbstractItemView {
    background-color: #1e1e1e;
    color: #e0e0e0;
    selection-background-color: #2a5a8f;
    border: 1px solid #2a5a8f;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #2a2a2a;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #0088cc;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QSlider::handle:horizontal:hover { background: #0099dd; }
QSlider::sub-page:horizontal {
    background: #0088cc;
    border-radius: 3px;
}

QPushButton[checkable="true"] {
    text-align: center;
    font-size: 11px;
}

QLabel { color: #c0c0c0; }

QCheckBox { color: #c0c0c0; spacing: 6px; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid #2a5a8f;
    border-radius: 3px;
    background-color: #1a1a1a;
}
QCheckBox::indicator:checked {
    background-color: #0088cc;
    border: 1px solid #0088cc;
}

QDialog {
    background-color: #1a1a1a;
}

QScrollBar:vertical {
    background: #1a1a1a;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #3a3a3a;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #0088cc; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


def _handle_exception(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logging.critical("Unhandled exception:\n%s", msg)
    QMessageBox.critical(
        None,
        "Nieoczekiwany błąd",
        f"Aplikacja napotkała błąd:\n\n{exc_value}\n\nSzczegóły zapisano w rival_gui.log",
    )


def main():
    sys.excepthook = _handle_exception

    app = QApplication(sys.argv)
    app.setApplicationName("RivalGUI")
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(DARK_QSS)

    icon_path = Path(__file__).resolve().parent / "assets" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    pm = ProfileManager()
    cfg = pm.load_config()
    i18n_init(cfg.get("language"))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
