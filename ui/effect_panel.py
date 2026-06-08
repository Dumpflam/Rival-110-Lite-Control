from PyQt6.QtWidgets import (
    QStackedWidget, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QSlider, QPushButton, QColorDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from core.config import EFFECTS


class EffectPanel(QStackedWidget):
    colors_changed = pyqtSignal(dict)
    color_b_changed = pyqtSignal(str)
    speed_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._colors = {"z1": "#ff0000", "z2": "#00ff00", "z3": "#0000ff"}
        self._color_b = "#ffffff"
        self._speed = 5

        self._color_btns: dict[str, list[QPushButton]] = {"z1": [], "z2": [], "z3": []}
        self._color_b_btns: list[QPushButton] = []
        self._speed_sliders: list[QSlider] = []
        self._lbl_cpu: QLabel | None = None

        self._pages: dict[str, QWidget] = {}
        self._index: dict[str, int] = {}

        for name in EFFECTS:
            method = getattr(
                self, f"_build_page_{name.lower().replace(' ', '_')}"
            )
            page = method()
            self._pages[name] = page
            self._index[name] = self.addWidget(page)

    def show_effect(self, name: str) -> None:
        self.setCurrentIndex(self._index[name])

    def set_state(self, colors: dict, color_b: str, speed: int) -> None:
        self._colors = colors.copy()
        self._color_b = color_b
        self._speed = speed

        for zone, btns in self._color_btns.items():
            for btn in btns:
                self._tint(btn, self._colors.get(zone, "#ff0000"))
        for btn in self._color_b_btns:
            self._tint(btn, self._color_b)
        for slider in self._speed_sliders:
            slider.setValue(speed)

    def _color_btn(self, zone: str, colors: dict, label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.clicked.connect(lambda: self._pick_color(zone, btn, colors))
        self._tint(btn, colors[zone])
        self._color_btns[zone].append(btn)
        return btn

    def _color_b_btn(self, label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.clicked.connect(lambda: self._pick_color_b(btn))
        self._tint(btn, self._color_b)
        self._color_b_btns.append(btn)
        return btn

    def _pick_color(self, zone: str, btn: QPushButton, colors: dict) -> None:
        col = QColorDialog.getColor(QColor(colors[zone]))
        if col.isValid():
            colors[zone] = col.name()
            self._tint(btn, col.name())
            self.colors_changed.emit(colors)

    def _pick_color_b(self, btn: QPushButton) -> None:
        col = QColorDialog.getColor(QColor(self._color_b))
        if col.isValid():
            self._color_b = col.name()
            self._tint(btn, col.name())
            for b in self._color_b_btns:
                self._tint(b, self._color_b)
            self.color_b_changed.emit(self._color_b)

    @staticmethod
    def _tint(btn: QPushButton, hex_color: str) -> None:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        fg = "#000" if (0.299 * r + 0.587 * g + 0.114 * b) > 128 else "#fff"
        btn.setStyleSheet(
            f"background-color:{hex_color};color:{fg};padding:6px;border-radius:4px;"
        )

    def _speed_slider(self, speed: int) -> QSlider:
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(1, 10)
        s.setValue(speed)
        s.valueChanged.connect(self.speed_changed.emit)
        self._speed_sliders.append(s)
        return s

    def _build_page_statyczny(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(self._color_btn("z1", self._colors, "Kolor Z1"))
        layout.addWidget(self._color_btn("z2", self._colors, "Kolor Z2"))
        layout.addWidget(self._color_btn("z3", self._colors, "Kolor Z3"))
        layout.addStretch()
        return w

    def _build_page_dwukolorowy(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(self._color_btn("z1", self._colors, "Kolor A (Z1)"))
        layout.addWidget(self._color_b_btn("Kolor B"))
        layout.addStretch()
        return w

    def _build_page_wygaszony(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Wszystkie strefy wyłączone"))
        layout.addStretch()
        return w

    def _build_page_tęcza(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Brak ustawień — efekt sprzętowy"))
        layout.addStretch()
        return w

    def _build_page_oddychanie(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(self._color_btn("z1", self._colors, "Kolor"))
        layout.addWidget(QLabel("Prędkość"))
        layout.addWidget(self._speed_slider(self._speed))
        layout.addStretch()
        return w

    def _build_page_puls_dwukolorowy(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(self._color_btn("z1", self._colors, "Kolor A"))
        layout.addWidget(self._color_b_btn("Kolor B"))
        layout.addWidget(QLabel("Prędkość"))
        layout.addWidget(self._speed_slider(self._speed))
        layout.addStretch()
        return w

    def _build_page_własny_gradient(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(self._color_btn("z1", self._colors, "Kolor Z1"))
        layout.addWidget(self._color_btn("z2", self._colors, "Kolor Z2"))
        layout.addWidget(self._color_btn("z3", self._colors, "Kolor Z3"))
        layout.addWidget(QLabel("Prędkość"))
        layout.addWidget(self._speed_slider(self._speed))
        layout.addStretch()
        return w

    def _build_page_wschód_słońca(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Prędkość"))
        layout.addWidget(self._speed_slider(self._speed))
        layout.addStretch()
        return w

    def _build_page_kometa(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Prędkość"))
        layout.addWidget(self._speed_slider(self._speed))
        layout.addStretch()
        return w

    def _build_page_błyskawica(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Prędkość"))
        layout.addWidget(self._speed_slider(self._speed))
        layout.addStretch()
        return w

    def _build_page_fala_kolorów(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(self._color_btn("z1", self._colors, "Kolor bazowy"))
        layout.addWidget(QLabel("Prędkość"))
        layout.addWidget(self._speed_slider(self._speed))
        layout.addStretch()
        return w

    def _build_page_ogień(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Prędkość"))
        layout.addWidget(self._speed_slider(self._speed))
        layout.addStretch()
        return w

    def _build_page_ocean(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Prędkość"))
        layout.addWidget(self._speed_slider(self._speed))
        layout.addStretch()
        return w

    def _build_page_gwiezdna_noc(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Prędkość"))
        layout.addWidget(self._speed_slider(self._speed))
        layout.addStretch()
        return w

    def _build_page_własny_sekwencyjny(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Edytuj w kreatorze efektów (✏ Edytor)"))
        layout.addStretch()
        return w

    def _build_page_monitor_cpu(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self._lbl_cpu = QLabel("CPU: ---%")
        layout.addWidget(self._lbl_cpu)
        layout.addStretch()
        return w
