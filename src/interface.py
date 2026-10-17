"""Square-edged Windows-classic PyQt6 interface for the Rival 110."""
from __future__ import annotations
import copy
import json
import logging
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QSize, QRectF
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QBrush, QPixmap, QLinearGradient, QRadialGradient, QImage, QPalette
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QColorDialog, QFileDialog, QFormLayout,
    QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMenu,
    QMessageBox, QPushButton, QScrollArea, QSlider, QSpinBox, QSystemTrayIcon,
    QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QInputDialog, QAbstractItemView, QHeaderView, QSizePolicy
)

from sequence_editor import SequenceTimeline
from device import Rival110, DeviceError
from effects import Animator, PARAMETERS, EFFECT_NAMES, HARDWARE_EFFECTS
from state import Store, DEFAULT_LIGHTING, data_dir, validate_light, validate_dpi, valid_color
import startup

log = logging.getLogger(__name__)


def app_icon(accent='#4C90CE'):
    image = QPixmap(48, 48)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    painter.setPen(QPen(QColor('#10131A'), 3))
    painter.setBrush(QBrush(QColor('#B5BCC4')))
    painter.drawRect(10, 5, 28, 38)
    painter.setPen(QPen(QColor('#10131A'), 2))
    painter.drawLine(24, 5, 24, 20)
    painter.fillRect(20, 13, 8, 10, QColor(accent))
    painter.end()
    return QIcon(image)




def asset_path(name: str) -> Path:
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
    return root / 'assets' / name


class MousePreviewWidget(QWidget):
    """Rival 110 preview using pixel-registered LED masks from the reference photo.

    The photographic base, core masks and Gaussian-blurred glow sprites all
    share the same 1000x1000 source coordinate system. Only the containing
    mouse image is scaled. We NEVER enlarge the entire mask to fake a glow:
    doing so displaced the logo by many source pixels in older builds.
    """

    def __init__(self, compact=False, parent=None):
        super().__init__(parent)
        self.compact = compact
        self.theme = 'Dark'
        self.led_color = '#4C90CE'
        self.pixmap = QPixmap(str(asset_path('rival110_mouse.png')))
        with asset_path('led_regions.json').open('r', encoding='utf-8') as stream:
            metadata = json.load(stream)
        self.source_size = (metadata['image_width'], metadata['image_height'])
        self.regions = metadata['sprites']
        self.led_sprites = {
            key: {
                kind: QPixmap(str(asset_path(f'rival110_{key}_{kind}.png')))
                for kind in ('core', 'glow')
            }
            for key in ('wheel', 'logo')
        }
        self._tinted = {}
        if compact:
            self.setMinimumSize(76, 58)
        else:
            self.setMinimumSize(320, 470)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_preview(self, color: str, theme: str | None = None):
        if theme is not None:
            self.theme = theme
        self.led_color = color
        self.update()

    def _tint_mask(self, mask: QPixmap, color: QColor, opacity: float) -> QPixmap:
        if mask.isNull():
            return mask
        opacity = max(0., min(1., opacity))
        key = (mask.cacheKey(), color.rgba(), round(opacity * 255))
        existing = self._tinted.get(key)
        if existing is not None:
            return existing
        pixmap = QPixmap(mask.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        p = QPainter(pixmap)
        p.drawPixmap(0, 0, mask)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        tint = QColor(color)
        tint.setAlpha(round(255 * opacity))
        p.fillRect(pixmap.rect(), tint)
        p.end()
        # A small bounded cache avoids redoing work on static/breathing effects
        # without retaining thousands of rainbow colors.
        if len(self._tinted) >= 24:
            self._tinted.clear()
        self._tinted[key] = pixmap
        return pixmap

    def _paint_led(self, painter: QPainter, mouse_rect: QRectF, name: str,
                   color: QColor, dark: bool):
        region = self.regions[name]
        sw, sh = self.source_size
        # Every sprite is drawn at EXACTLY the same native coordinates as its
        # photograph counterpart. Core and blur share this destination rectangle.
        dest = QRectF(
            mouse_rect.left() + mouse_rect.width() * (region['x'] / sw),
            mouse_rect.top() + mouse_rect.height() * (region['y'] / sh),
            mouse_rect.width() * (region['width'] / sw),
            mouse_rect.height() * (region['height'] / sh),
        )
        painter.save()
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        glow_opacity = (0.30 if dark else 0.20)
        if name == 'logo':
            glow_opacity += 0.02
        for kind, opacity in (
            ('glow', glow_opacity),
            ('core', 0.97 if dark else 0.91),
        ):
            mask = self.led_sprites[name][kind]
            if mask.isNull():
                continue
            tinted = self._tint_mask(mask, color, opacity)
            if kind == 'core':
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.drawPixmap(dest, tinted,
                               QRectF(0, 0, tinted.width(), tinted.height()))
        painter.restore()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        r = self.rect()
        dark = self.theme == 'Dark'
        painter.fillRect(r, QColor('#1A202A' if dark else '#F6F9FD'))

        color = QColor(self.led_color)
        # Ambient spill in the panel, faint enough not to look like an image frame.
        ambient = QRadialGradient(float(r.center().x()), float(r.center().y()),
                                  float(max(r.width(), r.height()) * 0.52))
        near = QColor(color); near.setAlpha(12 if dark else 8)
        distant = QColor(color); distant.setAlpha(0)
        ambient.setColorAt(0.0, near)
        ambient.setColorAt(1.0, distant)
        painter.fillRect(r, QBrush(ambient))

        if self.pixmap.isNull():
            painter.setPen(QPen(QColor('#FFFFFF' if dark else '#203040'), 1))
            painter.drawText(r, Qt.AlignmentFlag.AlignCenter, 'Rival 110 preview unavailable')
            return

        target_w = max(1, int(r.width() * (0.95 if self.compact else 0.995)))
        target_h = max(1, int(r.height() * (0.95 if self.compact else 0.995)))
        scaled = self.pixmap.scaled(target_w, target_h,
                                    Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)
        x = (r.width() - scaled.width()) // 2
        y = (r.height() - scaled.height()) // 2
        if not self.compact:
            y = max(0, y - int(r.height() * 0.01))
        target = QRectF(float(x), float(y), float(scaled.width()), float(scaled.height()))

        painter.setOpacity(0.94 if dark else 1.0)
        painter.drawPixmap(target, scaled,
                           QRectF(0, 0, scaled.width(), scaled.height()))
        painter.setOpacity(1.0)
        self._paint_led(painter, target, 'wheel', color, dark)
        self._paint_led(painter, target, 'logo', color, dark)

        # The original photo already contains natural directional reflections.
        # Adding a white shape here washed out the mouse in light theme.



def theme_css(theme, accent):
    dark = theme == 'Dark'
    canvas = '#171B22' if dark else '#C5CBD2'
    face = '#272E39' if dark else '#E4E7EB'
    field = '#141820' if dark else '#FFFFFF'
    text = '#DFE8F2' if dark else '#142033'
    subtle = '#A7B6C6' if dark else '#394960'
    edge = '#0C1017' if dark else '#69798C'
    high = '#56657A' if dark else '#FFFFFF'
    pressed = '#354255' if dark else '#CCD6E2'
    group = face
    tab_canvas = face
    return f'''
    QMainWindow, QDialog, QWidget#lightingRoot, QWidget#lightingOuter, QWidget#lightingContent,
    QWidget#appearanceTab, QWidget#deviceTab, QWidget#mouseTab {{ background-color: {canvas}; color: {text}; }}
    QMainWindow, QDialog {{ background-color: {canvas}; color: {text}; }}
    QFrame#headbar {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
      stop:0 {high}, stop:0.12 {face}, stop:1 {canvas});
      border: 1px solid {edge}; border-bottom: 3px solid {accent}; padding: 9px; }}
    QWidget {{ color: {text}; font-family: 'Tahoma', 'Segoe UI'; font-size: 10pt; }}
    QTabWidget::pane {{ border: 1px solid {edge}; background: {tab_canvas}; }}
    QTabBar::tab {{ background: {face}; border: 1px solid {edge}; border-bottom: 0;
                   padding: 9px 18px; margin-right: 2px; min-width: 82px; }}
    QTabBar::tab:selected {{ background: {accent}; color: #FFFFFF; border: 1px solid {edge}; }}
    QGroupBox {{ border: 1px solid {edge}; background: {group};
                 margin-top: 14px; padding: 13px 10px 9px 10px; font-weight: bold; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 1px 7px;
                        background: {group}; }}
    QPushButton {{ background-color: {face}; color: {text};
                   border-top: 2px solid {high}; border-left: 2px solid {high};
                   border-bottom: 2px solid {edge}; border-right: 2px solid {edge};
                   border-radius: 0px; padding: 5px 10px; min-height: 21px; }}
    QPushButton:hover {{ background-color: {pressed}; }}
    QPushButton:pressed {{ background-color: {pressed};
                           border-top: 2px solid {edge}; border-left: 2px solid {edge};
                           border-bottom: 2px solid {high}; border-right: 2px solid {high}; }}
    QPushButton:checked {{ background: {accent}; color: white; border: 1px solid {edge}; }}
    QPushButton:disabled {{ color: {subtle}; }}
    QLineEdit, QSpinBox, QComboBox, QTableWidget {{
        background-color: {field}; color: {text}; border: 1px solid {edge};
        border-top: 2px solid {edge}; border-left: 2px solid {edge};
        padding: 5px; border-radius: 0px; selection-background-color: {accent}; }}
    QComboBox::drop-down {{ border-left: 1px solid {edge}; width: 18px; }}
    QComboBox QAbstractItemView {{ background: {field}; color: {text};
        selection-background-color: {accent}; }}
    QSlider::groove:horizontal {{ height: 6px; background: {field};
                                  border: 1px solid {edge}; }}
    QSlider::handle:horizontal {{ background: {face}; border: 1px solid {edge};
                                  border-top: 2px solid {high}; width: 13px; margin: -6px 0; }}
    QSlider::sub-page:horizontal {{ background: {accent}; }}
    QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget, QAbstractScrollArea,
    QWidget#lightingContent, QWidget#lightingOuter, QWidget#lightingRoot {{
        border: none; background: {canvas}; }}
    QScrollBar:vertical, QScrollBar:horizontal {{ background: {face}; border: 1px solid {edge}; }}
    QLabel#status, QLabel#hint {{ color: {subtle}; background: transparent; }}
    QHeaderView::section {{ background: {face}; border: 1px solid {edge};
                            padding: 5px; color: {text}; }}
    QToolTip {{ background: {field}; color: {text}; border: 1px solid {edge}; }}
    '''


def tray_menu_css(theme: str, accent: str) -> str:
    """Readable taskbar notification-area menus independent of Windows theme."""
    dark = theme == 'Dark'
    bg = '#252C37' if dark else '#F5F6F8'
    fg = '#E7EFF9' if dark else '#172332'
    edge = '#0E1218' if dark else '#8D9CAD'
    muted = '#8290A2' if dark else '#8290A0'
    separator = '#536173' if dark else '#ACB6C2'
    return f'''
    QMenu {{ background-color: {bg}; color: {fg}; border: 1px solid {edge};
             font-family: "Segoe UI", Tahoma; font-size: 10pt; padding: 3px; }}
    QMenu::item {{ color: {fg}; background-color: transparent; padding: 6px 26px 6px 24px; }}
    QMenu::item:selected {{ background-color: {accent}; color: #FFFFFF; }}
    QMenu::item:disabled {{ color: {muted}; }}
    QMenu::separator {{ height: 1px; background: {separator}; margin: 4px 7px; }}
    QMenu::indicator:checked {{ background-color: {accent}; border: 1px solid {edge}; }}
    '''


def create_button(text, callback, width=None):
    b = QPushButton(text)
    if width:
        b.setMinimumWidth(width)
    b.clicked.connect(callback)
    return b


def add_row(layout, *widgets):
    row = QHBoxLayout()
    row.setSpacing(7)
    for widget in widgets:
        row.addWidget(widget)
    layout.addLayout(row)
    return row


class Window(QMainWindow):
    def __init__(self, store=None, device=None):
        super().__init__()
        self.store = store or Store()
        self.device = device or Rival110()
        self.animator = Animator()
        self.working = validate_light(self.store.data.get('working_lighting') or
                                      self.store.data['lighting_profiles'][self.store.data['last_lighting']])
        self.updating = False
        self.quit_requested = False
        self._last_effect_mode = ''
        self.setWindowTitle('Rival 110 Lite Control')
        self.resize(1320, 870)
        self.setMinimumSize(QSize(920, 650))
        self.setWindowIcon(app_icon(self.store.data['accent']))
        self._build()
        self.apply_theme()
        self.restore_fields()
        self.animator.configure(self.working)
        self.setup_tray()
        if self.device.connect():
            self._apply_dpi_profile(self.store.data['last_dpi'],
                                    self.store.data['dpi_profiles'][self.store.data['last_dpi']], persist=False)
        self._update_status()
        self.tick = QTimer(self)
        self.tick.setInterval(40)  # Faster preview updates for closer sync with the mouse.
        self.tick.timeout.connect(self.animation_tick)
        self.tick.start()
        self.reconnect = QTimer(self)
        self.reconnect.setInterval(3000)
        self.reconnect.timeout.connect(self.reconnect_mouse)
        self.reconnect.start()
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.setInterval(350)
        self.debounce.timeout.connect(self.persist_working)

    def _build(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        headbar = QFrame()
        headbar.setObjectName('headbar')
        header = QHBoxLayout(headbar)
        header.setContentsMargins(8, 7, 8, 7)
        title = QLabel('RIVAL 110 CONTROL')
        title.setStyleSheet('font-size: 15pt; font-weight: bold; letter-spacing: 2px;')
        header.addWidget(title)
        header.addStretch()
        self.status = QLabel('Connecting...')
        self.status.setObjectName('status')
        header.addWidget(self.status)
        self.preview = MousePreviewWidget(compact=True)
        self.preview.setFixedSize(92, 64)
        self.preview.setToolTip('Compact Rival 110 color preview')
        header.addWidget(self.preview)
        layout.addWidget(headbar)

        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self._tab_changed)
        layout.addWidget(self.tabs, 1)
        self._build_lighting()
        self._build_mouse()
        self._build_appearance()
        self._build_device_info()
        self._tab_changed(self.tabs.currentIndex())
        foot = QHBoxLayout()
        foot.addStretch()
        self.footer = QLabel('Software animations require the tray application to remain running.')
        self.footer.setObjectName('hint')
        foot.addWidget(self.footer)
        layout.addLayout(foot)

    def _tab_changed(self, index):
        if hasattr(self, 'preview_panel'):
            self.preview_panel.setVisible(index == 0 and self.width() >= 1060)

    def _build_lighting(self):
        tab = QWidget()
        tab.setObjectName('lightingRoot')
        outer_layout = QVBoxLayout(tab)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        split = QHBoxLayout()
        split.setContentsMargins(0, 0, 0, 0)
        split.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content.setObjectName('lightingContent')
        body = QVBoxLayout(content)
        body.setContentsMargins(12, 12, 12, 12)
        profiles = QGroupBox('LIGHTING PROFILES')
        p = QVBoxLayout(profiles)
        self.light_combo = QComboBox()
        self.light_combo.setMinimumWidth(170)
        self.light_combo.currentTextChanged.connect(self.select_light)
        add_row(p, QLabel('Saved:'), self.light_combo,
                create_button('Save', self.save_lighting),
                create_button('Save As...', self.save_lighting_as),
                create_button('Delete', self.delete_lighting))
        add_row(p, create_button('Import...', self.import_lighting),
                create_button('Export...', self.export_lighting))
        body.addWidget(profiles)
        options = QGroupBox('EFFECT')
        opt = QVBoxLayout(options)
        self.effect_combo = QComboBox()
        self.effect_combo.addItems(EFFECT_NAMES)
        self.effect_combo.currentTextChanged.connect(self.effect_changed)
        add_row(opt, QLabel('Animation:'), self.effect_combo)
        self.primary = create_button('Primary color...', lambda: self.change_color('primary'))
        self.secondary = create_button('Secondary color...', lambda: self.change_color('secondary'))
        add_row(opt, self.primary, self.secondary)
        self.common = {}
        for title, key in [('Brightness', 'brightness'), ('Speed', 'speed'), ('Saturation', 'saturation')]:
            slider, label, line = self.slider_row(title, 0, 100, lambda n, k=key: self.common_changed(k, n))
            self.common[key] = (slider, label)
            opt.addLayout(line)
        self.hardware_hint = QLabel('')
        self.hardware_hint.setWordWrap(True)
        self.hardware_hint.setObjectName('hint')
        opt.addWidget(self.hardware_hint)
        body.addWidget(options)

        self.effect_box = QGroupBox('EFFECT OPTIONS')
        self.effect_opts = QVBoxLayout(self.effect_box)
        self.params_widget = QWidget()
        self.params_layout = QVBoxLayout(self.params_widget)
        self.params_layout.setContentsMargins(0, 0, 0, 0)
        self.effect_opts.addWidget(self.params_widget)
        self.param_sliders = {}
        body.addWidget(self.effect_box)

        self.sequence_box = QGroupBox('CUSTOM SEQUENCE TIMELINE')
        sq = QVBoxLayout(self.sequence_box)
        sq.setSpacing(9)
        self.sequence_selected = 0
        self.sequence_timeline = SequenceTimeline()
        self.sequence_timeline.keyframe_selected.connect(self.select_sequence_step)
        self.sequence_timeline.durations_changed.connect(self.sequence_durations_changed)
        sq.addWidget(self.sequence_timeline)
        self.sequence_info = QLabel('')
        self.sequence_info.setObjectName('hint')
        sq.addWidget(self.sequence_info)
        editor = QHBoxLayout()
        editor.setSpacing(8)
        editor.addWidget(QLabel('Color:'))
        self.sequence_color_swatch = QLabel('')
        self.sequence_color_swatch.setFixedSize(28, 26)
        editor.addWidget(self.sequence_color_swatch)
        editor.addWidget(create_button('Choose...', self.edit_step_color))
        editor.addSpacing(9)
        editor.addWidget(QLabel('Duration:'))
        self.sequence_duration = QSpinBox()
        self.sequence_duration.setRange(50, 60000)
        self.sequence_duration.setSingleStep(50)
        self.sequence_duration.setSuffix(' ms')
        self.sequence_duration.setMinimumWidth(115)
        self.sequence_duration.valueChanged.connect(self.sequence_duration_changed)
        editor.addWidget(self.sequence_duration)
        editor.addSpacing(9)
        editor.addWidget(QLabel('Transition:'))
        self.sequence_transition = QComboBox()
        self.sequence_transition.addItem('Smooth fade', 'smooth')
        self.sequence_transition.addItem('Hold color', 'hold')
        self.sequence_transition.setMinimumWidth(115)
        self.sequence_transition.currentIndexChanged.connect(self.sequence_transition_changed)
        editor.addWidget(self.sequence_transition)
        editor.addStretch()
        sq.addLayout(editor)
        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        for label, handler in (
            ('Add', self.add_step),
            ('Duplicate', self.duplicate_step),
            ('Delete', self.remove_step),
            ('Move left', lambda: self.move_sequence_step(-1)),
            ('Move right', lambda: self.move_sequence_step(1)),
        ):
            buttons.addWidget(create_button(label, handler))
        sq.addLayout(buttons)
        hint = QLabel('Click a colored segment to select it. Drag a diamond to adjust neighboring durations.')
        hint.setObjectName('hint')
        hint.setWordWrap(True)
        sq.addWidget(hint)
        body.addWidget(self.sequence_box)
        body.addStretch(1)

        scroll.setWidget(content)
        split.addWidget(scroll, 1)

        preview_box = QGroupBox('RIVAL 110 VISUALIZATION')
        pv = QVBoxLayout(preview_box)
        self.side_preview = MousePreviewWidget(compact=False)
        self.side_preview.setToolTip('Single-zone Rival 110 preview with UI glow spill')
        pv.addWidget(self.side_preview, 1)
        preview_box.setMinimumWidth(390)
        self.preview_panel = preview_box
        split.addWidget(preview_box, 0)

        outer_layout.addLayout(split)
        self.tabs.addTab(tab, 'Lighting')


    def slider_row(self, title, minimum, maximum, callback, suffix=''):
        line = QHBoxLayout()
        text = QLabel(title)
        text.setMinimumWidth(160)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.valueChanged.connect(callback)
        value = QLabel(f'{minimum}{suffix}')
        value.setMinimumWidth(55)
        value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        slider.valueChanged.connect(lambda n, l=value, s=suffix: l.setText(f'{n}{s}'))
        line.addWidget(text)
        line.addWidget(slider, 1)
        line.addWidget(value)
        return slider, value, line

    def _build_mouse(self):
        tab = QWidget()
        tab.setObjectName('mouseTab')
        body = QVBoxLayout(tab)
        body.setContentsMargins(13, 13, 13, 13)
        gp = QGroupBox('DPI & POLLING PROFILES')
        v = QVBoxLayout(gp)
        self.dpi_combo = QComboBox()
        self.dpi_combo.currentTextChanged.connect(self.select_dpi)
        add_row(v, QLabel('Saved configuration:'), self.dpi_combo,
                create_button('Save', self.save_dpi),
                create_button('Save As...', self.save_dpi_as),
                create_button('Delete', self.delete_dpi))
        add_row(v, create_button('Import...', self.import_dpi),
                create_button('Export...', self.export_dpi),
                QLabel('Profiles appear in the tray menu.'))
        body.addWidget(gp)

        hardware = QGroupBox('SENSOR AND BUTTON SETTINGS')
        form = QFormLayout(hardware)
        form.setSpacing(15)
        self.dpi1 = QSpinBox()
        self.dpi2 = QSpinBox()
        for widget in (self.dpi1, self.dpi2):
            widget.setRange(200, 7200)
            widget.setSingleStep(100)
            widget.setSuffix(' DPI')
            widget.valueChanged.connect(self.dpi_fields_changed)
        self.polling = QComboBox()
        for hz in (125, 250, 500, 1000):
            self.polling.addItem(f'{hz} Hz', hz)
        self.polling.currentIndexChanged.connect(self.dpi_fields_changed)
        self.button6 = QComboBox()
        self.button6.addItem('Switch DPI presets (recommended)', 'dpi')
        self.button6.addItem('OS-defined button input', 'os')
        self.button6.currentIndexChanged.connect(self.dpi_fields_changed)
        form.addRow('DPI stage 1:', self.dpi1)
        form.addRow('DPI stage 2:', self.dpi2)
        form.addRow('USB polling rate:', self.polling)
        form.addRow('Button behind wheel:', self.button6)
        body.addWidget(hardware)
        add_row(body, create_button('APPLY & SAVE TO MOUSE', self.apply_dpi_clicked),
                create_button('Reset device to defaults...', self.factory_reset))
        info = QLabel('The mouse holds two DPI stages in onboard memory. Use the physical DPI button to switch between them.\n'
                      'Applying a profile also writes the polling rate and button mode, then saves once to the mouse.')
        info.setWordWrap(True)
        info.setObjectName('hint')
        body.addWidget(info)
        body.addStretch(1)
        self.tabs.addTab(tab, 'Mouse / DPI')

    def _build_appearance(self):
        tab = QWidget()
        tab.setObjectName('appearanceTab')
        body = QVBoxLayout(tab)
        body.setContentsMargins(13, 13, 13, 13)
        look = QGroupBox('CLASSIC WINDOWS APPEARANCE')
        form = QFormLayout(look)
        self.theme = QComboBox()
        self.theme.addItems(['Dark', 'Light'])
        self.theme.currentTextChanged.connect(self.change_theme)
        self.accent = create_button('Choose accent...', self.choose_accent)
        form.addRow('Theme:', self.theme)
        form.addRow('Selection accent:', self.accent)
        quick = QHBoxLayout()
        for hex_value in ('#4C90CE', '#609662', '#A775D3', '#CE844C', '#8B959F', '#C95B70'):
            button = QPushButton('  ')
            button.setFixedSize(36, 27)
            button.setToolTip(hex_value)
            button.clicked.connect(lambda _, color=hex_value: self.set_accent(color))
            button.setStyleSheet(f'background: {hex_value}; border: 2px outset #929BA6;')
            quick.addWidget(button)
        form.addRow('Quick accents:', quick)
        body.addWidget(look)

        behavior = QGroupBox('WINDOWS & BACKGROUND OPERATION')
        v = QVBoxLayout(behavior)
        self.autostart = QCheckBox('Start with Windows (current user; no administrator privileges)')
        self.autostart.stateChanged.connect(self.toggle_startup)
        self.close_tray = QCheckBox('Closing window minimizes to tray (Exit from tray to quit)')
        self.close_tray.stateChanged.connect(self.toggle_tray)
        self.start_hidden = QCheckBox('Launch minimized to tray when started manually')
        self.start_hidden.stateChanged.connect(self.toggle_start_hidden)
        v.addWidget(self.autostart)
        v.addWidget(self.close_tray)
        v.addWidget(self.start_hidden)
        body.addWidget(behavior)
        body.addStretch(1)
        self.tabs.addTab(tab, 'Appearance / Startup')

    def _build_device_info(self):
        tab = QWidget()
        tab.setObjectName('deviceTab')
        body = QVBoxLayout(tab)
        body.setContentsMargins(13, 13, 13, 13)
        group = QGroupBox('DEVICE AND LIGHTING MEMORY')
        v = QVBoxLayout(group)
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        v.addWidget(self.info_label)
        add_row(v, create_button('Reconnect Rival 110', self.manual_reconnect),
                create_button('Save current static/breath color to mouse', self.save_led_hardware))
        body.addWidget(group)
        hint = QLabel('The Rival 110 has one lighting zone, no per-zone brightness register and no hardware support for custom animations.\n'
                      'Custom animations run in the tray; Static and the device-defined hardware effects can be saved onboard.\n'
                      'There is no RGB reset on exit. DPI/polling settings remain saved unless you change them.')
        hint.setWordWrap(True)
        hint.setObjectName('hint')
        body.addWidget(hint)
        body.addStretch(1)
        self.tabs.addTab(tab, 'Device / Diagnostics')

    def restore_fields(self):
        self.updating = True
        try:
            self.light_combo.clear()
            self.light_combo.addItems(self.store.data['lighting_profiles'].keys())
            self.light_combo.setCurrentText(self.store.data['last_lighting'])
            self.dpi_combo.clear()
            self.dpi_combo.addItems(self.store.data['dpi_profiles'].keys())
            self.dpi_combo.setCurrentText(self.store.data['last_dpi'])
            self.theme.setCurrentText(self.store.data['theme'])
            self.autostart.setChecked(startup.get_enabled())
            self.close_tray.setChecked(bool(self.store.data['close_to_tray']))
            self.start_hidden.setChecked(bool(self.store.data['start_minimized']))
            self._restore_dpi(self.store.data['dpi_profiles'][self.store.data['last_dpi']])
            self.restore_lighting()
        finally:
            self.updating = False

    def restore_lighting(self):
        self.updating = True
        try:
            self.effect_combo.setCurrentText(self.working.get('effect', 'Static'))
            for key, (slider, label) in self.common.items():
                slider.setValue(self.working.get(key, 50))
            self.primary.setText('Primary: ' + self.working['primary'])
            self.secondary.setText('Secondary: ' + self.working['secondary'])
            self.build_params()
            self.load_steps()
            self.sequence_box.setVisible(self.working['effect'] == 'Custom Sequence')
        finally:
            self.updating = False
        self.refresh_mode_hint()

    def build_params(self):
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                layout = item.layout()
                while layout.count():
                    item2 = layout.takeAt(0)
                    if item2.widget():
                        item2.widget().deleteLater()
        self.param_sliders = {}
        specs = PARAMETERS.get(self.working['effect'], [])
        self.effect_box.setVisible(bool(specs))
        for title, key, lower, upper, initial, suffix in specs:
            widget = QWidget()
            row = QHBoxLayout(widget)
            row.setContentsMargins(0, 3, 0, 3)
            lbl = QLabel(title)
            lbl.setMinimumWidth(180)
            slid = QSlider(Qt.Orientation.Horizontal)
            slid.setRange(lower, upper)
            slid.setValue(self.working.get('parameters', {}).get(key, initial))
            counter = QLabel(f'{slid.value()}{suffix}')
            counter.setMinimumWidth(65)
            counter.setAlignment(Qt.AlignmentFlag.AlignRight)
            slid.valueChanged.connect(lambda value, l=counter, s=suffix: l.setText(f'{value}{s}'))
            slid.valueChanged.connect(lambda value, k=key: self.parameter_changed(k, value))
            row.addWidget(lbl)
            row.addWidget(slid, 1)
            row.addWidget(counter)
            self.params_layout.addWidget(widget)
            self.param_sliders[key] = slid

    def refresh_mode_hint(self):
        effect = self.working['effect']
        if effect in HARDWARE_EFFECTS:
            message = ('Runs on the mouse without software frame updates. Firmware controls its speed; '
                       'numeric modes 2 and 4 have undocumented visual behavior.')
        elif effect == 'Static' or effect == 'Off':
            message = 'Single hardware LED, one color. This can be saved to onboard memory.'
        else:
            message = 'Single-zone software animation. Keep this app running in the system tray.'
        self.hardware_hint.setText(message)
        speed_enabled = effect not in ('Static', 'Off', 'CPU Monitor') and effect not in HARDWARE_EFFECTS
        self.common['speed'][0].setEnabled(speed_enabled)
        self.common['saturation'][0].setEnabled(effect != 'Off')
        self.secondary.setEnabled(effect in ('Two-color', 'Two-color Pulse', 'Custom Gradient',
                                            'Comet', 'Lightning', 'Starry Night'))

    def set_effect(self, name):
        if name not in PARAMETERS:
            return
        previous = self.working.get('effect', 'Static')
        self.working.setdefault('effect_parameters', {})[previous] = copy.deepcopy(self.working.get('parameters', {}))
        self.working['effect'] = name
        self.working['parameters'] = copy.deepcopy(self.working['effect_parameters'].get(name, {}))
        self.animator.configure(self.working)
        self.restore_lighting()
        self.queue_persist()
        self.refresh_tray()

    def effect_changed(self, name):
        if not self.updating:
            self.set_effect(name)

    def common_changed(self, key, value):
        if self.updating:
            return
        self.working[key] = value
        self.animator.configure(self.working)
        self.queue_persist()

    def parameter_changed(self, key, value):
        if self.updating:
            return
        self.working.setdefault('parameters', {})[key] = value
        self.working.setdefault('effect_parameters', {})[self.working['effect']] = copy.deepcopy(self.working['parameters'])
        self.animator.configure(self.working)
        self.queue_persist()

    def change_color(self, key):
        chosen = QColorDialog.getColor(QColor(self.working[key]), self, 'Select ' + key + ' color')
        if chosen.isValid():
            self.working[key] = chosen.name().upper()
            self.animator.configure(self.working)
            self.restore_lighting()
            self.queue_persist()

    def load_steps(self):
        """Refresh the visual timeline and selected step editor without side effects."""
        steps = self.working.get('sequence', [])
        if not steps:
            return
        self.sequence_selected = max(0, min(self.sequence_selected, len(steps)-1))
        self.sequence_timeline.set_steps(steps, self.sequence_selected)
        selected = steps[self.sequence_selected]
        self.sequence_duration.blockSignals(True)
        self.sequence_duration.setValue(selected['duration'])
        self.sequence_duration.blockSignals(False)
        self.sequence_transition.blockSignals(True)
        self.sequence_transition.setCurrentIndex(self.sequence_transition.findData(selected['transition']))
        self.sequence_transition.blockSignals(False)
        color = QColor(selected['color'])
        self.sequence_color_swatch.setStyleSheet(
            f'background-color: {color.name()}; border: 1px solid #637389;')
        total = sum(step['duration'] for step in steps)
        self.sequence_info.setText(
            f'Step {self.sequence_selected+1} of {len(steps)}   |   Total cycle: {total:,} ms')

    def select_sequence_step(self, index):
        steps = self.working.get('sequence', [])
        if 0 <= index < len(steps):
            self.sequence_selected = index
            self.load_steps()

    def _sequence_updated(self):
        self.animator.configure(self.working)
        self.load_steps()
        self.queue_persist()

    def sequence_duration_changed(self, duration):
        if self.updating:
            return
        self.working['sequence'][self.sequence_selected]['duration'] = duration
        self._sequence_updated()

    def sequence_transition_changed(self, _index):
        if self.updating:
            return
        transition = self.sequence_transition.currentData()
        if transition in ('smooth', 'hold'):
            self.working['sequence'][self.sequence_selected]['transition'] = transition
            self._sequence_updated()

    def sequence_durations_changed(self, previous_index, first, second):
        if self.updating:
            return
        steps = self.working['sequence']
        if 0 <= previous_index < len(steps)-1:
            steps[previous_index]['duration'] = first
            steps[previous_index+1]['duration'] = second
            self._sequence_updated()

    def add_step(self):
        steps = self.working['sequence']
        if len(steps) >= 100:
            return
        i = self.sequence_selected
        previous = steps[i] if steps else {'color': '#FFFFFF'}
        self.sequence_selected = i + 1
        steps.insert(self.sequence_selected, {'color': previous['color'],
                      'duration': 500, 'transition': 'smooth'})
        self._sequence_updated()

    def duplicate_step(self):
        steps = self.working['sequence']
        if len(steps) >= 100 or not steps:
            return
        self.sequence_selected = max(0, min(self.sequence_selected, len(steps)-1))
        steps.insert(self.sequence_selected+1, copy.deepcopy(steps[self.sequence_selected]))
        self.sequence_selected += 1
        self._sequence_updated()

    def edit_step_color(self):
        steps = self.working.get('sequence', [])
        if not steps:
            return
        i = self.sequence_selected
        chosen = QColorDialog.getColor(QColor(steps[i]['color']), self, 'Choose keyframe color')
        if chosen.isValid():
            steps[i]['color'] = chosen.name().upper()
            self._sequence_updated()

    def remove_step(self):
        steps = self.working['sequence']
        if len(steps) <= 1:
            self.footer.setText('At least one keyframe is required.')
            return
        del steps[self.sequence_selected]
        self.sequence_selected = min(self.sequence_selected, len(steps)-1)
        self._sequence_updated()

    def move_sequence_step(self, direction):
        steps = self.working['sequence']
        i = self.sequence_selected
        target = i + direction
        if 0 <= target < len(steps):
            steps[i], steps[target] = steps[target], steps[i]
            self.sequence_selected = target
            self._sequence_updated()

    def queue_persist(self):
        if hasattr(self, 'debounce'):
            self.debounce.start()

    def persist_working(self):
        self.store.data['working_lighting'] = validate_light(self.working)
        self.store.save()

    def select_light(self, name):
        if self.updating or not name or name not in self.store.data['lighting_profiles']:
            return
        self.working = copy.deepcopy(self.store.data['lighting_profiles'][name])
        self.store.data['last_lighting'] = name
        self.animator.configure(self.working)
        self.restore_lighting()
        self.persist_working()
        self.refresh_tray()

    def activate_light(self, name):
        self.updating = True
        self.light_combo.setCurrentText(name)
        self.updating = False
        self.select_light(name)

    def save_lighting(self):
        if not self.light_combo.currentText():
            return
        self.store.replace_profile('lighting_profiles', self.light_combo.currentText(), self.working)
        self.persist_working()
        self.refresh_tray()
        self.footer.setText('Lighting profile saved.')

    def save_lighting_as(self):
        name, ok = QInputDialog.getText(self, 'Save lighting profile', 'Name:')
        if ok and name.strip():
            self.store.replace_profile('lighting_profiles', name, self.working)
            self.store.data['last_lighting'] = name.strip()
            self.store.save()
            self.restore_fields()
            self.refresh_tray()

    def delete_lighting(self):
        name = self.light_combo.currentText()
        try:
            self.store.delete_profile('lighting_profiles', name)
            self.working = copy.deepcopy(self.store.data['lighting_profiles'][self.store.data['last_lighting']])
            self.animator.configure(self.working)
            self.restore_fields()
            self.persist_working()
            self.refresh_tray()
        except ValueError as exc:
            QMessageBox.information(self, 'Cannot delete', str(exc))

    def import_lighting(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Import lighting', '', 'JSON profile (*.json *.rivalprofile)')
        if not filename:
            return
        try:
            blob = json.loads(Path(filename).read_text(encoding='utf-8'))
            # Support both this app's files and upstream's .rivalprofile wrapper.
            profile = blob.get('profile', blob.get('data', blob))
            if 'colors' in profile and isinstance(profile['colors'], dict):
                from legacy import convert_old_lighting
                profile = convert_old_lighting(profile)
            name = blob.get('name', Path(filename).stem)
            self.store.replace_profile('lighting_profiles', name, profile)
            self.store.data['last_lighting'] = name
            self.store.save()
            self.restore_fields()
            self.select_light(name)
            self.refresh_tray()
        except (ValueError, OSError, KeyError, TypeError) as exc:
            QMessageBox.warning(self, 'Import failed', str(exc))

    def export_lighting(self):
        name = self.light_combo.currentText()
        filename, _ = QFileDialog.getSaveFileName(self, 'Export lighting', name + '.json', 'JSON profile (*.json)')
        if filename:
            try:
                Path(filename).write_text(json.dumps({'name': name, 'profile': self.working}, indent=2), encoding='utf-8')
            except OSError as exc:
                QMessageBox.warning(self, 'Export failed', str(exc))

    def _restore_dpi(self, profile):
        previous = self.updating
        self.updating = True
        try:
            p = validate_dpi(profile)
            self.dpi1.setValue(p['dpi1'])
            self.dpi2.setValue(p['dpi2'])
            self.polling.setCurrentIndex(self.polling.findData(p['polling']))
            self.button6.setCurrentIndex(self.button6.findData(p['button6']))
        finally:
            self.updating = previous

    def fields_dpi(self):
        return validate_dpi({'dpi1': self.dpi1.value(), 'dpi2': self.dpi2.value(),
                             'polling': self.polling.currentData(), 'button6': self.button6.currentData()})

    def dpi_fields_changed(self, *args):
        if not self.updating:
            self.footer.setText('DPI settings changed. Click APPLY & SAVE TO MOUSE to activate them.')

    def select_dpi(self, name):
        if self.updating or not name or name not in self.store.data['dpi_profiles']:
            return
        profile = self.store.data['dpi_profiles'][name]
        self._restore_dpi(profile)
        self._apply_dpi_profile(name, profile)

    def _apply_dpi_profile(self, name, profile, persist=True):
        self.store.data['last_dpi'] = name
        self.store.save()
        try:
            self.device.apply_dpi(profile, persist=persist)
            self.footer.setText(f'DPI profile applied to mouse: {name}')
        except DeviceError as exc:
            self.footer.setText(str(exc))
        self._update_status()
        self.refresh_tray()

    def activate_dpi(self, name):
        if name in self.store.data['dpi_profiles']:
            self._restore_dpi(self.store.data['dpi_profiles'][name])
            self.updating = True
            self.dpi_combo.setCurrentText(name)
            self.updating = False
            self._apply_dpi_profile(name, self.store.data['dpi_profiles'][name])

    def apply_dpi_clicked(self):
        try:
            values = self.fields_dpi()
            self.device.apply_dpi(values)
            self.footer.setText('DPI stages, polling and button mode saved to mouse.')
        except (DeviceError, ValueError) as exc:
            QMessageBox.warning(self, 'Cannot apply mouse settings', str(exc))

    def save_dpi(self):
        if not self.dpi_combo.currentText():
            return
        self.store.replace_profile('dpi_profiles', self.dpi_combo.currentText(), self.fields_dpi())
        self._apply_dpi_profile(self.dpi_combo.currentText(), self.fields_dpi())

    def save_dpi_as(self):
        name, ok = QInputDialog.getText(self, 'Save DPI profile', 'Name (e.g. 800 / 3200):')
        if ok and name.strip():
            self.store.replace_profile('dpi_profiles', name, self.fields_dpi())
            self.store.data['last_dpi'] = name.strip()
            self.store.save()
            self.restore_fields()
            self.activate_dpi(name.strip())
            self.refresh_tray()

    def delete_dpi(self):
        name = self.dpi_combo.currentText()
        try:
            self.store.delete_profile('dpi_profiles', name)
            self.restore_fields()
            self.refresh_tray()
        except ValueError as exc:
            QMessageBox.warning(self, 'Cannot delete', str(exc))

    def import_dpi(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Import DPI profile', '', 'JSON profile (*.json)')
        if not filename:
            return
        try:
            blob = json.loads(Path(filename).read_text(encoding='utf-8'))
            profile = blob.get('profile', blob)
            name = blob.get('name', Path(filename).stem)
            self.store.replace_profile('dpi_profiles', name, validate_dpi(profile))
            self.restore_fields()
            self.activate_dpi(name)
            self.refresh_tray()
        except (ValueError, OSError, KeyError, TypeError) as exc:
            QMessageBox.warning(self, 'Import failed', str(exc))

    def export_dpi(self):
        name = self.dpi_combo.currentText()
        if not name:
            return
        filename, _ = QFileDialog.getSaveFileName(self, 'Export DPI profile', name + '.json', 'JSON profile (*.json)')
        if filename:
            try:
                profile = self.store.data['dpi_profiles'][name]
                Path(filename).write_text(json.dumps({'name': name, 'profile': profile}, indent=2), encoding='utf-8')
            except OSError as exc:
                QMessageBox.warning(self, 'Export failed', str(exc))

    def factory_reset(self):
        if QMessageBox.question(self, 'Factory reset Rival 110',
            'Reset the physical mouse to factory settings? Your saved profiles in the app are kept.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        try:
            self.device.reset_factory()
            self.footer.setText('Device reset. Select a profile to reapply your saved settings.')
        except DeviceError as exc:
            QMessageBox.warning(self, 'Reset failed', str(exc))

    def change_theme(self, theme):
        if self.updating:
            return
        self.store.data['theme'] = theme
        self.store.save()
        self.apply_theme()

    def choose_accent(self):
        c = QColorDialog.getColor(QColor(self.store.data['accent']), self, 'Choose UI accent')
        if c.isValid():
            self.set_accent(c.name().upper())

    def set_accent(self, color):
        if not valid_color(color):
            return
        self.store.data['accent'] = color
        self.store.save()
        self.apply_theme()

    def apply_theme(self):
        self.setStyleSheet(theme_css(self.store.data['theme'], self.store.data['accent']))
        self.setWindowIcon(app_icon(self.store.data['accent']))
        if hasattr(self, 'tray'):
            self.tray.setIcon(app_icon(self.store.data['accent']))
        self.accent.setText('Choose accent... ' + self.store.data['accent'])
        self.sequence_timeline.set_theme(self.store.data['theme'], self.store.data['accent'])
        sample = self.animator.sample().color if hasattr(self, 'animator') else self.store.data['accent']
        if hasattr(self, 'preview'):
            self.preview.set_preview(sample, self.store.data['theme'])
        if hasattr(self, 'side_preview'):
            self.side_preview.set_preview(sample, self.store.data['theme'])
        if hasattr(self, 'tray'):
            self.refresh_tray()

    def toggle_startup(self):
        if self.updating:
            return
        try:
            startup.set_enabled(self.autostart.isChecked())
            self.store.data['autostart'] = self.autostart.isChecked()
            self.store.save()
        except Exception as exc:
            QMessageBox.warning(self, 'Autostart failed', str(exc))
            self.autostart.blockSignals(True)
            self.autostart.setChecked(False)
            self.autostart.blockSignals(False)

    def toggle_tray(self):
        if not self.updating:
            self.store.data['close_to_tray'] = self.close_tray.isChecked()
            self.store.save()

    def toggle_start_hidden(self):
        if not self.updating:
            self.store.data['start_minimized'] = self.start_hidden.isChecked()
            self.store.save()

    def _update_status(self):
        connected = self.device.connected
        self.status.setText('RIVAL 110 CONNECTED' if connected else 'DISCONNECTED / RECONNECTING')
        if hasattr(self, 'info_label'):
            self.info_label.setText('Target: SteelSeries Rival 110  |  USB 1038:1729\n'
                                    f'Status: {"Connected" if connected else "Disconnected"}\n'
                                    f'Last device error: {self.device.last_error or "None"}\n'
                                    f'Config folder: {data_dir()}')

    def manual_reconnect(self):
        self.device.disconnect()
        self.reconnect_mouse()

    def reconnect_mouse(self):
        if not self.device.connected:
            connected = self.device.connect()
            self._update_status()
            if connected:
                self._apply_dpi_profile(self.store.data['last_dpi'],
                                        self.store.data['dpi_profiles'][self.store.data['last_dpi']], persist=False)
                self._last_effect_mode = ''

    def save_led_hardware(self):
        if self.working['effect'] not in ('Static', 'Off', 'Hardware Breath', 'Hardware Effect 2', 'Hardware Effect 4'):
            QMessageBox.information(self, 'Software effect',
                'Only Static, Off or the three hardware effects can be stored in the mouse.\n'
                'Other animations require the app running.')
            return
        result = self.animator.sample()
        try:
            self.device.set_led(result.color, result.hardware, persist=True)
            self.footer.setText('Color and on-device effect saved to Rival 110.')
        except DeviceError as exc:
            QMessageBox.warning(self, 'Could not save', str(exc))

    def animation_tick(self):
        try:
            # CPU polling is intentionally low-frequency.
            import time
            now = time.monotonic()
            if self.working['effect'] == 'CPU Monitor' and now - self.animator.last_cpu > 1:
                try:
                    import psutil
                    self.animator.cpu_load = psutil.cpu_percent(interval=None)
                except Exception:
                    self.animator.cpu_load = 0
                self.animator.last_cpu = now
            result = self.animator.sample(now)
            self.preview.set_preview(result.color, self.store.data['theme'])
            if hasattr(self, 'side_preview'):
                self.side_preview.set_preview(result.color, self.store.data['theme'])
            if self.device.connected:
                self.device.set_led(result.color, result.hardware)
        except DeviceError as exc:
            self.footer.setText(str(exc))
            self._update_status()
        except Exception:
            log.exception('Animation tick failed')

    def setup_tray(self):
        self.tray = QSystemTrayIcon(app_icon(self.store.data['accent']), self)
        self.tray.setToolTip('Rival 110 Lite Control')
        self.tray.activated.connect(self.tray_activated)
        self.refresh_tray()
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def refresh_tray(self):
        if not hasattr(self, 'tray'):
            return
        old_menu = getattr(self, '_tray_menu', None)
        m = QMenu(self)
        open_action = m.addAction('Open Rival 110 Control')
        open_action.triggered.connect(self.show_window)
        m.addSeparator()
        dpi_menu = m.addMenu('DPI profiles')
        for name, profile in self.store.data['dpi_profiles'].items():
            action = dpi_menu.addAction(f'{name}  ({profile["polling"]} Hz)')
            action.setCheckable(True)
            action.setChecked(name == self.store.data['last_dpi'])
            action.triggered.connect(lambda _=False, n=name: self.activate_dpi(n))
        light_menu = m.addMenu('Saved lighting profiles')
        for name in self.store.data['lighting_profiles']:
            action = light_menu.addAction(name)
            action.setCheckable(True)
            action.setChecked(name == self.store.data['last_lighting'] and
                              self.working == self.store.data['lighting_profiles'][name])
            action.triggered.connect(lambda _=False, n=name: self.activate_light(n))
        preset_menu = m.addMenu('Lighting presets')
        for name in EFFECT_NAMES:
            action = preset_menu.addAction(name)
            action.setCheckable(True)
            action.setChecked(name == self.working['effect'])
            action.triggered.connect(lambda _=False, n=name: self.set_effect(n))
        m.addSeparator()
        quit_action = m.addAction('Exit (stop animations)')
        quit_action.triggered.connect(self.exit_app)
        style = tray_menu_css(self.store.data['theme'], self.store.data['accent'])
        foreground = QColor('#E7EFF9' if self.store.data['theme'] == 'Dark' else '#172332')
        accent = QColor(self.store.data['accent'])
        for menu in (m, dpi_menu, light_menu, preset_menu):
            # Native Windows menu drawing can ignore inherited widget text colors.
            # Set the palette and stylesheet explicitly for every submenu.
            palette = menu.palette()
            palette.setColor(QPalette.ColorRole.WindowText, foreground)
            palette.setColor(QPalette.ColorRole.Text, foreground)
            palette.setColor(QPalette.ColorRole.ButtonText, foreground)
            palette.setColor(QPalette.ColorRole.Highlight, accent)
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor('#FFFFFF'))
            menu.setPalette(palette)
            menu.setStyleSheet(style)
        self.tray.setContextMenu(m)
        self._tray_menu = m  # keep Python wrapper alive
        if old_menu is not None:
            old_menu.deleteLater()

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window()

    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()


    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'preview_panel'):
            self.preview_panel.setVisible(self.width() >= 1060 and self.tabs.currentIndex() == 0)

    def exit_app(self):
        self.quit_requested = True
        self.tick.stop()
        self.reconnect.stop()
        self.persist_working()
        self.tray.hide()
        self.device.disconnect()
        QApplication.instance().quit()

    def closeEvent(self, event):
        if not self.quit_requested and self.store.data['close_to_tray'] and QSystemTrayIcon.isSystemTrayAvailable():
            self.hide()
            event.ignore()
        else:
            self.quit_requested = True
            if hasattr(self, 'tick'):
                self.tick.stop()
            if hasattr(self, 'reconnect'):
                self.reconnect.stop()
            self.persist_working()
            self.device.disconnect()
            if hasattr(self, 'tray'):
                self.tray.hide()
            event.accept()
            QTimer.singleShot(0, QApplication.instance().quit)
