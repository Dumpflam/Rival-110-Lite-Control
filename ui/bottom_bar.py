from PyQt6.QtWidgets import QWidget, QHBoxLayout, QSlider, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal

from core.i18n import t

EFFECTS_NO_SPEED = {"Statyczny", "Dwukolorowy", "Wygaszony", "Tęcza", "Monitor CPU"}


class BottomBar(QWidget):
    brightness_changed = pyqtSignal(int)
    speed_changed = pyqtSignal(int)
    apply_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    editor_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # Brightness slider
        self.lbl_brightness = QLabel(t("bottom.brightness"))
        layout.addWidget(self.lbl_brightness)

        self.slider_brightness = QSlider(Qt.Orientation.Horizontal)
        self.slider_brightness.setRange(0, 100)
        self.slider_brightness.setValue(80)
        self.slider_brightness.setFixedWidth(120)
        self.slider_brightness.valueChanged.connect(self.brightness_changed.emit)
        layout.addWidget(self.slider_brightness)

        self.lbl_brightness_val = QLabel("80%")
        self.lbl_brightness_val.setFixedWidth(35)
        self.slider_brightness.valueChanged.connect(
            lambda v: self.lbl_brightness_val.setText(f"{v}%")
        )
        layout.addWidget(self.lbl_brightness_val)

        layout.addSpacing(16)

        # Speed row (hidden by default)
        self.speed_row = QWidget()
        speed_layout = QHBoxLayout(self.speed_row)
        speed_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_speed = QLabel(t("bottom.speed"))
        speed_layout.addWidget(self.lbl_speed)

        self.slider_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed.setRange(1, 10)
        self.slider_speed.setValue(5)
        self.slider_speed.setFixedWidth(120)
        self.slider_speed.valueChanged.connect(self.speed_changed.emit)
        speed_layout.addWidget(self.slider_speed)

        self.lbl_speed_val = QLabel("5")
        self.lbl_speed_val.setFixedWidth(25)
        self.slider_speed.valueChanged.connect(
            lambda v: self.lbl_speed_val.setText(str(v))
        )
        speed_layout.addWidget(self.lbl_speed_val)

        self.speed_row.setVisible(False)
        layout.addWidget(self.speed_row)
        layout.addStretch()

        # Editor button
        self.btn_editor = QPushButton(t("bottom.editor"))
        self.btn_editor.clicked.connect(self.editor_requested.emit)
        layout.addWidget(self.btn_editor)

        # Settings button
        self.btn_settings = QPushButton(t("bottom.settings"))
        self.btn_settings.setObjectName("btn_settings")
        self.btn_settings.clicked.connect(self.settings_requested.emit)
        layout.addWidget(self.btn_settings)

        # Apply button
        self.btn_apply = QPushButton(t("bottom.apply"))
        self.btn_apply.setObjectName("btn_apply")
        self.btn_apply.clicked.connect(self.apply_requested.emit)
        layout.addWidget(self.btn_apply)

    def set_brightness(self, val: int) -> None:
        self.slider_brightness.setValue(val)

    def set_speed(self, val: int) -> None:
        self.slider_speed.setValue(val)

    def show_speed(self, visible: bool) -> None:
        self.speed_row.setVisible(visible)

    def brightness(self) -> int:
        return self.slider_brightness.value()

    def speed(self) -> int:
        return self.slider_speed.value()
