from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QLineEdit, QWidget, QColorDialog, QMessageBox,
    QListWidget, QListWidgetItem, QSplitter,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QPolygon

from core.custom_effect import CustomEffect, Keyframe
from core.custom_effect_manager import custom_effect_manager
from core.effect_engine import engine
from core.i18n import t


class TimelineWidget(QWidget):
    keyframe_selected = pyqtSignal(int)
    keyframe_moved = pyqtSignal(int, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(60)
        self.setMinimumWidth(400)
        self._keyframes: list[Keyframe] = []
        self._selected: int | None = None
        self._dragging: int | None = None
        self.setCursor(Qt.CursorShape.CrossCursor)

    def set_keyframes(self, keyframes: list[Keyframe]) -> None:
        self._keyframes = keyframes
        self.update()

    def select(self, index: int | None) -> None:
        self._selected = index
        self.update()

    def _pos_to_t(self, x: int) -> float:
        margin = 20
        w = self.width() - 2 * margin
        return max(0.0, min(1.0, (x - margin) / w))

    def _t_to_x(self, t: float) -> int:
        margin = 20
        w = self.width() - 2 * margin
        return int(margin + t * w)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        p.fillRect(self.rect(), QColor("#1a1a1a"))

        y = self.height() // 2
        p.setPen(QPen(QColor("#3a3a3a"), 2))
        p.drawLine(20, y, self.width() - 20, y)

        p.setPen(QPen(QColor("#2a2a2a"), 1))
        for i in range(11):
            x = self._t_to_x(i / 10)
            p.drawLine(x, y - 4, x, y + 4)

        for i, kf in enumerate(self._keyframes):
            x = self._t_to_x(kf.position)
            color = QColor(kf.z2)
            selected = (i == self._selected)

            p.setPen(QPen(QColor("#ffffff") if selected else QColor("#888888"), 1.5))
            p.setBrush(QBrush(color))

            size = 10 if not selected else 13
            points = [
                (x, y - size), (x + size, y),
                (x, y + size), (x - size, y),
            ]
            poly = QPolygon([QPoint(px, py) for px, py in points])
            p.drawPolygon(poly)

    def mousePressEvent(self, event):
        x = event.pos().x()
        y = self.height() // 2
        for i, kf in enumerate(self._keyframes):
            kx = self._t_to_x(kf.position)
            if abs(x - kx) < 14:
                self._selected = i
                self._dragging = i
                self.keyframe_selected.emit(i)
                self.update()
                return
        self._selected = None
        self.update()

    def mouseMoveEvent(self, event):
        if self._dragging is not None:
            t = self._pos_to_t(event.pos().x())
            self._keyframes[self._dragging].position = t
            self.keyframe_moved.emit(self._dragging, t)
            self.update()

    def mouseReleaseEvent(self, event):
        self._dragging = None


class KeyframeEditor(QDialog):
    effect_applied = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("editor.title"))
        self.setMinimumSize(640, 480)
        self.setModal(False)

        self._effect = CustomEffect(
            name=t("editor.title"),
            duration_ms=2000,
            keyframes=[
                Keyframe(0.0, "#ff0000", "#ff0000", "#ff0000"),
                Keyframe(0.5, "#0000ff", "#0000ff", "#0000ff"),
                Keyframe(1.0, "#ff0000", "#ff0000", "#ff0000"),
            ],
        )
        self._selected_idx: int | None = None

        self._build_ui()
        self._refresh_list()

    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)

        # Left column — saved effects list
        left = QVBoxLayout()
        left.addWidget(QLabel(t("editor.saved_effects")))
        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_list_select)
        left.addWidget(self._list)

        btn_new = QPushButton(t("editor.new"))
        btn_new.clicked.connect(self._on_new)
        btn_del = QPushButton(t("editor.delete"))
        btn_del.clicked.connect(self._on_delete)
        row = QHBoxLayout()
        row.addWidget(btn_new)
        row.addWidget(btn_del)
        left.addLayout(row)

        left_w = QWidget()
        left_w.setLayout(left)
        left_w.setFixedWidth(160)
        outer.addWidget(left_w)

        # Right column — editor
        right = QVBoxLayout()

        meta_row = QHBoxLayout()
        meta_row.addWidget(QLabel(t("editor.name")))
        self._edit_name = QLineEdit(self._effect.name)
        self._edit_name.textChanged.connect(lambda t: setattr(self._effect, "name", t))
        meta_row.addWidget(self._edit_name)
        meta_row.addWidget(QLabel(t("editor.duration")))
        self._spin_duration = QSpinBox()
        self._spin_duration.setRange(500, 10000)
        self._spin_duration.setSingleStep(100)
        self._spin_duration.setValue(self._effect.duration_ms)
        self._spin_duration.valueChanged.connect(
            lambda v: setattr(self._effect, "duration_ms", v)
        )
        meta_row.addWidget(self._spin_duration)
        right.addLayout(meta_row)

        right.addWidget(QLabel(t("editor.timeline_hint")))
        self._timeline = TimelineWidget()
        self._timeline.set_keyframes(self._effect.keyframes)
        self._timeline.keyframe_selected.connect(self._on_kf_selected)
        self._timeline.keyframe_moved.connect(self._on_kf_moved)
        right.addWidget(self._timeline)

        # Keyframe panel
        self._kf_panel = QWidget()
        kf_layout = QHBoxLayout(self._kf_panel)

        kf_layout.addWidget(QLabel(t("editor.position")))
        self._spin_pos = QSpinBox()
        self._spin_pos.setRange(0, 100)
        self._spin_pos.setSuffix("%")
        self._spin_pos.setToolTip(t("editor.position"))
        self._spin_pos.valueChanged.connect(self._on_pos_changed)
        kf_layout.addWidget(self._spin_pos)

        self._btn_z1 = QPushButton("Z1")
        self._btn_z2 = QPushButton("Z2")
        self._btn_z3 = QPushButton("Z3")
        self._btn_z1.clicked.connect(lambda: self._pick_color("z1", self._btn_z1))
        self._btn_z2.clicked.connect(lambda: self._pick_color("z2", self._btn_z2))
        self._btn_z3.clicked.connect(lambda: self._pick_color("z3", self._btn_z3))
        for btn in (self._btn_z1, self._btn_z2, self._btn_z3):
            btn.setFixedWidth(60)
            kf_layout.addWidget(btn)

        btn_add_kf = QPushButton(t("editor.add_keyframe"))
        btn_add_kf.clicked.connect(self._on_add_keyframe)
        kf_layout.addWidget(btn_add_kf)

        self._btn_del_kf = QPushButton(t("editor.del_keyframe"))
        self._btn_del_kf.clicked.connect(self._on_del_keyframe)
        self._btn_del_kf.setEnabled(False)
        kf_layout.addWidget(self._btn_del_kf)

        self._kf_panel.setEnabled(False)
        right.addWidget(self._kf_panel)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_preview = QPushButton(t("editor.preview"))
        btn_preview.clicked.connect(self._on_preview)
        btn_stop = QPushButton(t("editor.stop"))
        btn_stop.clicked.connect(self._stop_preview)
        btn_save = QPushButton(t("editor.save"))
        btn_save.clicked.connect(self._on_save)
        btn_apply = QPushButton(t("editor.apply"))
        btn_apply.clicked.connect(self._on_apply)
        for btn in (btn_preview, btn_stop, btn_save, btn_apply):
            btn_row.addWidget(btn)
        right.addLayout(btn_row)

        right.addStretch()
        outer.addLayout(right)

    # --- Logic ---

    def _refresh_list(self) -> None:
        self._list.clear()
        for e in custom_effect_manager.list():
            self._list.addItem(QListWidgetItem(e.name))

    def _on_list_select(self, row: int) -> None:
        effects = custom_effect_manager.list()
        if 0 <= row < len(effects):
            self._effect = effects[row]
            self._edit_name.setText(self._effect.name)
            self._spin_duration.setValue(self._effect.duration_ms)
            self._timeline.set_keyframes(self._effect.keyframes)
            self._timeline.update()

    def _on_new(self) -> None:
        self._selected_idx = None
        self._kf_panel.setEnabled(False)
        self._btn_del_kf.setEnabled(False)
        self._effect = CustomEffect(
            name=t("editor.title"),
            duration_ms=2000,
            keyframes=[
                Keyframe(0.0, "#ff0000", "#ff0000", "#ff0000"),
                Keyframe(1.0, "#0000ff", "#0000ff", "#0000ff"),
            ],
        )
        self._edit_name.setText(self._effect.name)
        self._spin_duration.setValue(self._effect.duration_ms)
        self._timeline.set_keyframes(self._effect.keyframes)
        self._timeline.update()

    def _on_delete(self) -> None:
        row = self._list.currentRow()
        effects = custom_effect_manager.list()
        if 0 <= row < len(effects):
            custom_effect_manager.delete(effects[row].name)
            self._refresh_list()

    def _on_kf_selected(self, idx: int) -> None:
        self._selected_idx = idx
        kf = self._effect.keyframes[idx]
        self._spin_pos.blockSignals(True)
        self._spin_pos.setValue(int(kf.position * 100))
        self._spin_pos.blockSignals(False)
        self._tint(self._btn_z1, kf.z1)
        self._tint(self._btn_z2, kf.z2)
        self._tint(self._btn_z3, kf.z3)
        self._kf_panel.setEnabled(True)
        self._btn_del_kf.setEnabled(len(self._effect.keyframes) > 2)

    def _on_kf_moved(self, idx: int, t: float) -> None:
        if 0 <= idx < len(self._effect.keyframes):
            self._effect.keyframes[idx].position = t
            if self._selected_idx == idx:
                self._spin_pos.blockSignals(True)
                self._spin_pos.setValue(int(t * 100))
                self._spin_pos.blockSignals(False)

    def _on_pos_changed(self, val: int) -> None:
        if self._selected_idx is not None:
            self._effect.keyframes[self._selected_idx].position = val / 100
            self._timeline.update()

    def _pick_color(self, zone: str, btn: QPushButton) -> None:
        if self._selected_idx is None:
            return
        kf = self._effect.keyframes[self._selected_idx]
        current = getattr(kf, zone)
        col = QColorDialog.getColor(QColor(current), self)
        if col.isValid():
            setattr(kf, zone, col.name())
            self._tint(btn, col.name())
            self._timeline.update()

    def _on_add_keyframe(self) -> None:
        self._effect.keyframes.append(Keyframe(0.5))
        self._timeline.set_keyframes(self._effect.keyframes)
        self._timeline.update()

    def _on_del_keyframe(self) -> None:
        if self._selected_idx is not None and len(self._effect.keyframes) > 2:
            self._effect.keyframes.pop(self._selected_idx)
            self._selected_idx = None
            self._kf_panel.setEnabled(False)
            self._btn_del_kf.setEnabled(False)
            self._timeline.set_keyframes(self._effect.keyframes)
            self._timeline.update()

    def _on_preview(self) -> None:
        engine.set_custom_effect(self._effect)

    def _stop_preview(self) -> None:
        engine.stop()

    def _on_save(self) -> None:
        self._effect.name = self._edit_name.text().strip() or t("editor.title")
        custom_effect_manager.save(self._effect)
        self._refresh_list()

    def _on_apply(self) -> None:
        self._on_save()
        engine.set_custom_effect(self._effect)
        self.effect_applied.emit(self._effect)

    @staticmethod
    def _tint(btn: QPushButton, hex_color: str) -> None:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        fg = "#000" if (0.299 * r + 0.587 * g + 0.114 * b) > 128 else "#fff"
        btn.setStyleSheet(
            f"background-color:{hex_color};color:{fg};padding:4px;border-radius:4px;"
        )
