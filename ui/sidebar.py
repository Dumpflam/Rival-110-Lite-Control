from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QFrame, QSizePolicy, QInputDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QByteArray

from core.profile_manager import ProfileManager
from core.i18n import t

try:
    from PyQt6.QtSvgWidgets import QSvgWidget
    HAS_SVG = True
except ImportError:
    HAS_SVG = False

from ui.mouse_svg import MOUSE_SVG_TEMPLATE


class Sidebar(QWidget):
    profile_loaded = pyqtSignal(dict)
    profile_saved = pyqtSignal(str)
    random_requested = pyqtSignal()
    export_requested = pyqtSignal()
    import_requested = pyqtSignal()

    def __init__(self, pm: ProfileManager, parent=None):
        super().__init__(parent)
        self._pm = pm
        self._settings_provider: callable | None = None

        self.setFixedWidth(200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # --- Mouse preview ---
        self._current_colors = {"z1": "#ff0000", "z2": "#00ff00", "z3": "#0000ff"}
        if HAS_SVG:
            self._svg_widget = QSvgWidget()
            self._svg_widget.setFixedSize(130, 260)
            self._render_svg()
            layout.addWidget(self._svg_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        else:
            self.mouse_frame = QFrame()
            self.mouse_frame.setFixedSize(130, 240)
            self.mouse_frame.setStyleSheet(
                "background-color:#1a1a1a;border:2px solid #2a2a2a;border-radius:40px;"
            )
            mouse_layout = QVBoxLayout(self.mouse_frame)
            mouse_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            mouse_layout.setSpacing(10)

            self.zone_views = {}
            for zone in ("z1", "z2", "z3"):
                zf = QFrame()
                zf.setFixedSize(70, 40)
                zf.setStyleSheet(
                    "border-radius:10px;border:1px solid #555;"
                    f"background-color:{'#ff0000' if zone == 'z1' else '#00ff00' if zone == 'z2' else '#0000ff'};"
                )
                self.zone_views[zone] = zf
                mouse_layout.addWidget(zf)

            layout.addWidget(self.mouse_frame, alignment=Qt.AlignmentFlag.AlignCenter)

        # --- Mouse status ---
        self.connected_text = t("status.connected")
        self.disconnected_text = t("status.disconnected")
        self.lbl_mouse_status = QLabel()
        self.set_mouse_status(False)
        self.lbl_mouse_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_mouse_status)

        # --- Profile section ---
        layout.addWidget(QLabel(t("sidebar.profiles")))

        # Combobox row
        cb_row = QHBoxLayout()
        self.cb_profile = QComboBox()
        self._refresh_list()
        cb_row.addWidget(self.cb_profile, 1)

        self.btn_save = QPushButton(t("sidebar.save"))
        self.btn_save.clicked.connect(self._on_save)
        cb_row.addWidget(self.btn_save)
        layout.addLayout(cb_row)

        # Save As
        self.btn_save_as = QPushButton(t("sidebar.save_as"))
        self.btn_save_as.clicked.connect(self._on_save_as)
        layout.addWidget(self.btn_save_as)

        # Load / Delete row
        ld_row = QHBoxLayout()
        self.btn_load = QPushButton(t("sidebar.load"))
        self.btn_load.clicked.connect(self._on_load)
        ld_row.addWidget(self.btn_load)

        self.btn_delete = QPushButton(t("sidebar.delete"))
        self.btn_delete.clicked.connect(self._on_delete)
        ld_row.addWidget(self.btn_delete)
        layout.addLayout(ld_row)

        # Export / Import row
        ie_row = QHBoxLayout()
        btn_export = QPushButton(t("sidebar.export"))
        btn_export.clicked.connect(self.export_requested.emit)
        btn_import = QPushButton(t("sidebar.import"))
        btn_import.clicked.connect(self.import_requested.emit)
        ie_row.addWidget(btn_export)
        ie_row.addWidget(btn_import)
        layout.addLayout(ie_row)

        self.btn_random = QPushButton(t("sidebar.random"))
        self.btn_random.clicked.connect(self.random_requested.emit)
        layout.addWidget(self.btn_random)

        layout.addStretch()

        # --- Status ---
        self.lbl_status = QLabel(t("status.ready"))
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("color:#888;font-size:11px;")
        layout.addWidget(self.lbl_status)

    # --- Public API ---

    def _render_svg(self) -> None:
        svg = MOUSE_SVG_TEMPLATE.format(
            z1=self._current_colors["z1"],
            z2=self._current_colors["z2"],
            z3=self._current_colors["z3"],
        )
        self._svg_widget.load(QByteArray(svg.encode("utf-8")))

    def update_colors(self, z1: str, z2: str, z3: str) -> None:
        if HAS_SVG:
            if (z1, z2, z3) == (
                self._current_colors["z1"],
                self._current_colors["z2"],
                self._current_colors["z3"],
            ):
                return
            self._current_colors = {"z1": z1, "z2": z2, "z3": z3}
            self._render_svg()
        else:
            for zone, hex_color in (("z1", z1), ("z2", z2), ("z3", z3)):
                frame = self.zone_views[zone]
                ss = f"border-radius:10px;border:1px solid #555;background-color:{hex_color};"
                if frame.styleSheet() != ss:
                    frame.setStyleSheet(ss)

    def set_mouse_status(self, connected: bool) -> None:
        if connected:
            self.lbl_mouse_status.setText(self.connected_text)
            self.lbl_mouse_status.setStyleSheet("color:#00aa00;font-weight:bold;")
        else:
            self.lbl_mouse_status.setText(self.disconnected_text)
            self.lbl_mouse_status.setStyleSheet("color:#cc0000;font-weight:bold;")

    def set_settings_provider(self, fn: callable) -> None:
        self._settings_provider = fn

    def set_status(self, msg: str) -> None:
        self.lbl_status.setText(msg)

    # --- Internal ---

    def _refresh_list(self) -> None:
        self.cb_profile.blockSignals(True)
        self.cb_profile.clear()
        self.cb_profile.addItems(self._pm.list_names())
        active = self._pm.active_name
        idx = self.cb_profile.findText(active)
        if idx >= 0:
            self.cb_profile.setCurrentIndex(idx)
        self.cb_profile.blockSignals(False)

    def _on_save(self) -> None:
        name = self.cb_profile.currentText()
        if not name or self._settings_provider is None:
            return
        self._pm.set(name, self._settings_provider())
        self._pm.active_name = name
        self._refresh_list()
        self.profile_saved.emit(name)
        self.set_status(t("status.profile_saved").format(name=name))

    def _on_save_as(self) -> None:
        if self._settings_provider is None:
            return
        name, ok = QInputDialog.getText(self, t("dialog.save_as.title"), t("dialog.save_as.label"))
        if not ok or not name:
            return
        self._pm.set(name, self._settings_provider())
        self._pm.active_name = name
        self._refresh_list()
        self.profile_saved.emit(name)
        self.set_status(t("status.profile_saved_as").format(name=name))

    def _on_load(self) -> None:
        name = self.cb_profile.currentText()
        if not name:
            return
        profile = self._pm.get(name)
        self._pm.active_name = name
        self._refresh_list()
        self.profile_loaded.emit(profile)
        self.set_status(t("status.profile_loaded").format(name=name))

    def _on_delete(self) -> None:
        name = self.cb_profile.currentText()
        if not name:
            return
        reply = QMessageBox.question(
            self, t("dialog.delete_profile.title"),
            t("dialog.delete_profile.msg").format(name=name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self._pm.delete(name)
            self._refresh_list()
            self.set_status(t("status.profile_deleted").format(name=name))
        except ValueError as e:
            QMessageBox.warning(self, t("dialog.error"), str(e))
