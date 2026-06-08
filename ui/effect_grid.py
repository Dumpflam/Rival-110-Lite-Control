from PyQt6.QtWidgets import QWidget, QGridLayout, QPushButton
from PyQt6.QtCore import pyqtSignal

from core.config import EFFECTS
from core.i18n import t


class EffectTile(QPushButton):
    def __init__(self, key: str, display: str, parent=None):
        super().__init__(parent)
        self._key = key
        self.setText(display)
        self.setCheckable(True)
        self.setFixedSize(120, 60)
        self.setStyleSheet(
            "QPushButton {"
            "  background-color: #1e1e1e;"
            "  border: 2px solid #2a2a2a;"
            "  border-radius: 8px;"
            "  color: #c0c0c0;"
            "  font-size: 11px;"
            "}"
            "QPushButton:checked {"
            "  border: 2px solid #0088cc;"
            "  background-color: #0d2a3a;"
            "  color: #ffffff;"
            "}"
        )


class EffectGrid(QWidget):
    effect_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tiles: dict[str, EffectTile] = {}
        self._current: str | None = None

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        for i, name in enumerate(EFFECTS):
            display = t(f"effect.{name}")
            tile = EffectTile(name, display)
            tile.clicked.connect(lambda checked, n=name: self.select(n))
            self._tiles[name] = tile
            layout.addWidget(tile, i // 3, i % 3)

    def select(self, name: str) -> None:
        if self._current == name:
            return
        if self._current is not None and self._current in self._tiles:
            self._tiles[self._current].setChecked(False)
        self._current = name
        self._tiles[name].setChecked(True)
        self.effect_selected.emit(name)

    def current(self) -> str | None:
        return self._current
