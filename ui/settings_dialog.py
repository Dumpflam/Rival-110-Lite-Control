import sys

try:
    import winreg
except ImportError:
    winreg = None

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton,
    QLabel, QMessageBox, QComboBox,
)
from PyQt6.QtCore import pyqtSignal

from core.config import APP_NAME, AUTORUN_KEY
from core.i18n import t, available_languages, current_lang
from core.profile_manager import ProfileManager


def set_autostart(enable: bool, exe_path: str) -> None:
    if winreg is None:
        return
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, AUTORUN_KEY, 0,
            winreg.KEY_SET_VALUE,
        )
        if enable:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception:
        pass


def get_autostart_state() -> bool:
    if winreg is None:
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, AUTORUN_KEY, 0,
            winreg.KEY_READ,
        )
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


class SettingsDialog(QDialog):
    eclipse_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("settings.title"))
        self.setModal(False)
        self._pm = ProfileManager()

        layout = QVBoxLayout(self)

        # Behavior section
        layout.addWidget(QLabel(t("settings.section.behavior")))

        self.chk_eclipse = QCheckBox(t("settings.eclipse"))
        self.chk_eclipse.toggled.connect(self.eclipse_changed.emit)
        layout.addWidget(self.chk_eclipse)

        self.chk_autostart = QCheckBox(t("settings.autostart"))
        self.chk_autostart.setChecked(get_autostart_state())
        self.chk_autostart.toggled.connect(self._on_autostart_toggled)
        layout.addWidget(self.chk_autostart)

        self._chk_reset = QCheckBox(t("settings.reset_on_exit"))
        cfg = self._pm.load_config()
        self._chk_reset.setChecked(cfg.get("reset_on_exit", True))
        self._chk_reset.toggled.connect(self._on_reset_on_exit_changed)
        layout.addWidget(self._chk_reset)

        # Mouse section
        layout.addWidget(QLabel(t("settings.section.mouse")))

        self.btn_reset = QPushButton(t("settings.reset"))
        self.btn_reset.clicked.connect(self._on_reset)
        layout.addWidget(self.btn_reset)

        # Info section
        layout.addWidget(QLabel(t("settings.section.info")))
        layout.addWidget(QLabel(t("settings.version")))

        # Language section
        layout.addWidget(QLabel(t("settings.section.language")))

        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel(t("settings.language.label")))
        self._lang_combo = QComboBox()
        langs = available_languages()
        self._lang_combo.addItems(langs)
        idx = self._lang_combo.findText(current_lang())
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)
        self._lang_combo.currentTextChanged.connect(self._on_lang_changed)
        lang_row.addWidget(self._lang_combo)
        layout.addLayout(lang_row)

        self._lbl_lang_hint = QLabel(t("settings.language.restart"))
        self._lbl_lang_hint.setStyleSheet("color:#888;font-size:11px;")
        self._lbl_lang_hint.setVisible(False)
        layout.addWidget(self._lbl_lang_hint)

        layout.addStretch()

    def _on_autostart_toggled(self, checked: bool) -> None:
        exe_path = sys.executable if getattr(sys, "frozen", False) else sys.argv[0]
        set_autostart(checked, exe_path)

    def _on_lang_changed(self, lang: str) -> None:
        from core.profile_manager import ProfileManager
        pm = ProfileManager()
        cfg = pm.load_config()
        cfg["language"] = lang
        pm.save_config(cfg)
        self._lbl_lang_hint.setVisible(True)

    def _on_reset_on_exit_changed(self, enabled: bool) -> None:
        cfg = self._pm.load_config()
        cfg["reset_on_exit"] = enabled
        self._pm.save_config(cfg)

    def _on_reset(self) -> None:
        ans = QMessageBox.question(
            self, t("dialog.reset.title"),
            t("settings.reset.confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            from core.hid_manager import hid
            hid.reset()
