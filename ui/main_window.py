from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSystemTrayIcon, QMenu, QApplication,
)
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, QEvent
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor

from core.hid_manager import hid
from core.effect_engine import engine
from core.profile_manager import ProfileManager
from core.i18n import t
from ui.effect_grid import EffectGrid
from ui.effect_panel import EffectPanel
from ui.sidebar import Sidebar
from ui.bottom_bar import BottomBar, EFFECTS_NO_SPEED
from ui.settings_dialog import SettingsDialog
from ui.keyframe_editor import KeyframeEditor


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._pm = ProfileManager()
        self._settings_dialog = None
        self._editor_dialog = None
        self._eclipse = False
        self._eclipse_phase = 0
        self._eclipse_was_pressed = False

        self._eclipse_timer = QTimer(self)
        self._eclipse_timer.timeout.connect(self._eclipse_poll)

        self._build_ui()
        self._connect_signals()
        self._init_tray()
        self._init_reconnect_timer()
        self._load_initial_profile()

    def _build_ui(self) -> None:
        self.setWindowTitle(t("app.title"))
        self.setMinimumSize(820, 560)

        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)

        content = QHBoxLayout()
        self.sidebar = Sidebar(self._pm)
        self.grid = EffectGrid()
        self.panel = EffectPanel()

        right = QVBoxLayout()
        right.addWidget(self.grid)
        right.addWidget(self.panel)

        content.addWidget(self.sidebar, 1)
        content.addLayout(right, 2)

        self.bottom = BottomBar()
        outer.addLayout(content, 1)
        outer.addWidget(self.bottom)

    def _connect_signals(self) -> None:
        self.grid.effect_selected.connect(self.panel.show_effect)
        self.grid.effect_selected.connect(self._on_effect_selected)

        self.panel.colors_changed.connect(engine.set_colors)
        self.panel.color_b_changed.connect(engine.set_color_b)
        self.panel.speed_changed.connect(engine.set_speed)
        self.panel.speed_changed.connect(self.bottom.set_speed)

        engine.colors_changed.connect(self.sidebar.update_colors)

        self.bottom.brightness_changed.connect(engine.set_brightness)
        self.bottom.speed_changed.connect(engine.set_speed)
        self.bottom.apply_requested.connect(self._on_apply)
        self.bottom.settings_requested.connect(self._open_settings)

        self.sidebar.profile_loaded.connect(self._on_profile_loaded)
        self.sidebar.set_settings_provider(self._gather_settings)
        self.sidebar.random_requested.connect(self._on_random)
        self.sidebar.export_requested.connect(self._on_export)
        self.sidebar.import_requested.connect(self._on_import)
        self.bottom.editor_requested.connect(self._open_editor)

    def _on_effect_selected(self, name: str) -> None:
        engine.set_effect(name)
        self.bottom.show_speed(name not in EFFECTS_NO_SPEED)

    def _on_apply(self) -> None:
        if not hid.is_connected():
            self.sidebar.set_status(t("status.mouse_not_found"))
            return
        ok = hid.set_brightness(self.bottom.brightness())
        if ok and self.grid.current() == "Statyczny":
            c = engine._colors
            ok = hid.set_colors(c["z1"], c["z2"], c["z3"])
        self.sidebar.set_status(t("status.applied") if ok else t("status.hid_error"))

    def _on_random(self) -> None:
        import random
        from core.config import EFFECTS

        pool = [e for e in EFFECTS if e not in ("Wygaszony", "Monitor CPU")]
        effect = random.choice(pool)

        colors = {
            "z1": QColor.fromHsv(random.randint(0, 359), 255, 255).name(),
            "z2": QColor.fromHsv(random.randint(0, 359), 255, 255).name(),
            "z3": QColor.fromHsv(random.randint(0, 359), 255, 255).name(),
        }
        color_b = QColor.fromHsv(random.randint(0, 359), 255, 255).name()
        speed = random.randint(3, 8)

        self.grid.select(effect)
        self.panel.set_state(colors, color_b, speed)
        engine.set_colors(colors, color_b)
        engine.set_speed(speed)
        engine.set_effect(effect)
        self.bottom.set_speed(speed)
        self.bottom.show_speed(effect not in EFFECTS_NO_SPEED)
        self.sidebar.set_status(t("status.random").format(effect=effect))

    def _on_export(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        name = self.sidebar.cb_profile.currentText()
        path, _ = QFileDialog.getSaveFileName(
            self, t("dialog.export.title"), f"{name}.rivalprofile",
            "Rival Profile (*.rivalprofile);;JSON (*.json)"
        )
        if not path:
            return
        try:
            self._pm.export_profile(name, path)
            self.sidebar.set_status(t("status.exported").format(name=name))
        except Exception as e:
            self.sidebar.set_status(t("status.export_error").format(error=e))

    def _on_import(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, t("dialog.import.title"), "",
            "Rival Profile (*.rivalprofile);;JSON (*.json)"
        )
        if not path:
            return
        try:
            name = self._pm.import_profile(path)
            self.sidebar._refresh_list()
            self.sidebar.set_status(t("status.imported").format(name=name))
        except (ValueError, Exception) as e:
            self.sidebar.set_status(t("status.import_error").format(error=e))

    def _on_profile_loaded(self, profile: dict) -> None:
        self.grid.select(profile.get("effect", "Statyczny"))
        self.panel.set_state(
            profile.get("colors", {}),
            profile.get("color_b", "#ffffff"),
            profile.get("speed", 5),
        )
        self.bottom.set_brightness(profile.get("brightness", 80))
        self.bottom.set_speed(profile.get("speed", 5))
        engine.set_colors(profile.get("colors", {}))
        engine.set_speed(profile.get("speed", 5))

    def _gather_settings(self) -> dict:
        return {
            "effect": self.grid.current(),
            "brightness": self.bottom.brightness(),
            "speed": self.bottom.speed(),
            "colors": engine._colors,
            "color_b": engine._color_b,
        }

    def _load_initial_profile(self) -> None:
        name = self._pm.active_name
        self._on_profile_loaded(self._pm.get(name))
        self.sidebar.set_mouse_status(hid.is_connected())

    def _init_reconnect_timer(self) -> None:
        t = QTimer(self)
        t.timeout.connect(self._reconnect_poll)
        t.start(5000)

    def _reconnect_poll(self) -> None:
        if not hid.is_connected():
            if hid.reconnect():
                self.sidebar.set_mouse_status(True)
                self.sidebar.set_status(t("status.mouse_reconnected"))
        else:
            self.sidebar.set_mouse_status(True)

    def _init_tray(self) -> None:
        self.tray = QSystemTrayIcon(self._make_tray_icon(), self)
        menu = QMenu()
        menu.addAction(t("tray.show"), self._show_window)
        menu.addSeparator()
        menu.addAction(t("tray.quit"), self._quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda r: self._show_window()
            if r == QSystemTrayIcon.ActivationReason.DoubleClick else None
        )
        self.tray.show()

    def _make_tray_icon(self) -> QIcon:
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon.ico"
        if icon_path.exists():
            return QIcon(str(icon_path))
        pix = QPixmap(32, 32)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#0088cc"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(2, 2, 28, 28)
        p.end()
        return QIcon(pix)

    def _show_window(self) -> None:
        self.showNormal()
        self.activateWindow()

    def closeEvent(self, event) -> None:
        self._quit()

    def changeEvent(self, event) -> None:
        if (
            event.type() == QEvent.Type.WindowStateChange
            and self.windowState() & Qt.WindowState.WindowMinimized
        ):
            QTimer.singleShot(0, self._minimize_to_tray)
        super().changeEvent(event)

    def _minimize_to_tray(self) -> None:
        self.hide()
        self.tray.showMessage(
            t("app.title"), t("tray.minimized"),
            QSystemTrayIcon.MessageIcon.Information, 2000,
        )

    def _quit(self) -> None:
        engine.stop()
        cfg = self._pm.load_config()
        if cfg.get("reset_on_exit", True):
            hid.reset()
        else:
            hid.disconnect()
        self.tray.hide()
        QApplication.quit()

    def _open_settings(self) -> None:
        if self._settings_dialog is None:
            self._settings_dialog = SettingsDialog(self)
            self._settings_dialog.eclipse_changed.connect(
                self._on_eclipse_changed
            )
        self._settings_dialog.show()

    def _open_editor(self) -> None:
        if self._editor_dialog is None:
            self._editor_dialog = KeyframeEditor(self)
            self._editor_dialog.effect_applied.connect(
                self._on_custom_effect_applied
            )
        self._editor_dialog.show()
        self._editor_dialog.activateWindow()

    def _on_custom_effect_applied(self, effect) -> None:
        self.grid.select("Własny Sekwencyjny")
        self.bottom.show_speed(False)
        self.sidebar.set_status(t("status.custom_effect").format(name=effect.name))

    def _on_eclipse_changed(self, enabled: bool) -> None:
        self._eclipse = enabled
        if enabled:
            self._eclipse_timer.start(50)
        else:
            self._eclipse_timer.stop()

    def _eclipse_poll(self) -> None:
        import ctypes
        state = ctypes.windll.user32.GetAsyncKeyState(0x01)
        pressed = bool(state & 0x8000)
        if pressed and not self._eclipse_was_pressed:
            self._eclipse_was_pressed = True
            self._eclipse_phase = 6
        elif not pressed:
            self._eclipse_was_pressed = False
        if self._eclipse_phase > 0:
            hue = (self._eclipse_phase * 60) % 360
            col = QColor.fromHsv(hue, 255, 255).name()
            hid.set_colors(col, col, col)
            self._eclipse_phase -= 1
