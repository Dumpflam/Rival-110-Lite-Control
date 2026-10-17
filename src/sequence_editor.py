"""Compact, classic Windows-style timeline for one-zone custom RGB sequences.

Time is stored as per-step durations, matching the existing animation engine.
Dragging a boundary redistributes duration between adjacent steps without
changing the total cycle time; selecting a band edits just that step.
"""
from __future__ import annotations
import copy

from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QPolygon
from PyQt6.QtWidgets import QWidget, QSizePolicy


class SequenceTimeline(QWidget):
    keyframe_selected = pyqtSignal(int)
    durations_changed = pyqtSignal(int, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.steps = []
        self.selected = 0
        self.theme = 'Dark'
        self.accent = '#4C90CE'
        self.dragging_boundary = None
        self.setFixedHeight(98)
        self.setMinimumWidth(280)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setToolTip('Click a colored segment to edit it. Drag a dividing diamond to adjust timing.')
        self.setMouseTracking(True)

    def set_steps(self, steps, selected=0):
        self.steps = copy.deepcopy(steps)
        self.selected = max(0, min(int(selected), len(self.steps)-1)) if self.steps else -1
        self.update()

    def set_theme(self, theme, accent):
        self.theme = theme
        self.accent = accent
        self.update()

    def _geometry(self):
        left, right = 15, max(16, self.width() - 15)
        usable = max(1, right - left)
        durations = [max(50, int(step['duration'])) for step in self.steps]
        total = max(1, sum(durations))
        bounds = [left]
        elapsed = 0
        for duration in durations:
            elapsed += duration
            bounds.append(left + round(usable * elapsed / total))
        return bounds, total

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        dark = self.theme == 'Dark'
        p.fillRect(self.rect(), QColor('#171D26' if dark else '#F1F4F8'))
        if not self.steps:
            return
        bounds, total = self._geometry()
        y, height = 25, 35
        for i, step in enumerate(self.steps):
            x1, x2 = bounds[i], bounds[i+1]
            color = QColor(step['color'])
            p.fillRect(x1, y, max(1, x2-x1), height, color)
            if i == self.selected:
                p.setPen(QPen(QColor(self.accent), 3))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRect(x1+1, y+1, max(1,x2-x1-2), height-2)
            if x2-x1 >= 46:
                luma = (color.red()*299 + color.green()*587 + color.blue()*114)//1000
                p.setPen(QColor('#161616' if luma > 145 else '#FFFFFF'))
                p.drawText(x1, y, max(1,x2-x1), height, Qt.AlignmentFlag.AlignCenter, str(i+1))
        p.setPen(QPen(QColor('#91A1B4' if dark else '#54677B'), 1))
        p.drawRect(bounds[0], y, max(1, bounds[-1]-bounds[0]), height)
        for i in range(1, len(bounds)-1):
            x = bounds[i]
            p.setPen(QPen(QColor('#111923' if dark else '#FFFFFF'), 1))
            p.setBrush(QBrush(QColor('#D6E5F4' if dark else '#33465A')))
            p.drawPolygon(QPolygon([QPoint(x, y-7), QPoint(x+6, y), QPoint(x, y+7), QPoint(x-6, y)]))
        p.setPen(QColor('#AAB8C9' if dark else '#33465A'))
        p.drawText(bounds[0], 66, 85, 20, Qt.AlignmentFlag.AlignLeft, '0 ms')
        p.drawText(max(bounds[0],bounds[-1]-140), 66, min(140, self.width()-bounds[0]), 20,
                   Qt.AlignmentFlag.AlignRight, f'{total:,} ms')
        p.end()

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self.steps:
            return
        bounds, _ = self._geometry()
        x, y = event.position().x(), event.position().y()
        if 14 <= y <= 62:
            if len(self.steps) <= 24:
                for i in range(1, len(bounds)-1):
                    if abs(x - bounds[i]) <= 7:
                        self.dragging_boundary = i
                        self.keyframe_selected.emit(i)
                        self.selected = i
                        self.update()
                        return
            for i in range(len(self.steps)):
                if bounds[i] <= x <= bounds[i+1]:
                    self.selected = i
                    self.keyframe_selected.emit(i)
                    self.update()
                    return

    def mouseMoveEvent(self, event):
        if self.dragging_boundary is None:
            return
        i = self.dragging_boundary
        if i < 1 or i >= len(self.steps):
            return
        bounds, total = self._geometry()
        width = max(1, bounds[-1] - bounds[0])
        target_ms = round((event.position().x() - bounds[0]) / width * total)
        before_ms = sum(int(s['duration']) for s in self.steps[:i-1])
        pair_total = self.steps[i-1]['duration'] + self.steps[i]['duration']
        low = max(50, pair_total - 60000)
        high = min(60000, pair_total - 50)
        new_left = max(low, min(high, target_ms-before_ms))
        new_right = pair_total - new_left
        if new_left != self.steps[i-1]['duration']:
            self.steps[i-1]['duration'] = new_left
            self.steps[i]['duration'] = new_right
            self.durations_changed.emit(i-1, new_left, new_right)
            self.update()

    def mouseReleaseEvent(self, event):
        self.dragging_boundary = None
