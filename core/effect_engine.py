import math
import time
import random
import logging

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QColor

from core.hid_manager import hid

logger = logging.getLogger(__name__)


class EffectEngine(QObject):
    colors_changed = pyqtSignal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._effect = "Statyczny"
        self._colors = {"z1": "#ff0000", "z2": "#00ff00", "z3": "#0000ff"}
        self._color_b = "#ffffff"
        self._speed = 5
        self._brightness = 80
        self._frame = 0
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)

        self._cpu_last = None
        self._cpu_timer = QTimer()
        self._cpu_timer.timeout.connect(self._cpu_poll)

        self._lightning_zone = "z1"
        self._lightning_frames = 0
        self._star_state = {"z1": 0.0, "z2": 0.0, "z3": 0.0}
        self._custom_effect = None

    def set_color_b(self, color_b: str) -> None:
        self._color_b = color_b

    def set_custom_effect(self, effect) -> None:
        from core.custom_effect import CustomEffect
        self._custom_effect = effect
        self.set_effect("Własny Sekwencyjny")

    def set_effect(self, name: str) -> None:
        self._timer.stop()
        self._cpu_timer.stop()
        self._frame = 0
        self._effect = name
        if name == "Monitor CPU":
            self._cpu_timer.start(1000)
            self._tick()
            return
        if name != "Statyczny":
            interval = max(33, 100 - self._speed * 8)
            self._timer.start(interval)
        if name == "Statyczny":
            self._tick()

    def set_colors(self, colors: dict, color_b: str = None) -> None:
        self._colors = colors.copy()
        if color_b is not None:
            self._color_b = color_b

    def set_speed(self, speed: int) -> None:
        self._speed = speed
        if self._timer.isActive():
            interval = max(33, 100 - self._speed * 8)
            self._timer.setInterval(interval)

    def set_brightness(self, val: int) -> None:
        self._brightness = val
        hid.set_brightness(val)

    def stop(self) -> None:
        self._timer.stop()
        self._cpu_timer.stop()

    def _tick(self) -> None:
        method = getattr(self, f"_effect_{self._effect.lower().replace(' ', '_')}", None)
        if method:
            z1, z2, z3 = method()
        else:
            z1, z2, z3 = self._colors["z1"], self._colors["z2"], self._colors["z3"]

        hid.set_colors(z1, z2, z3)
        self.colors_changed.emit(z1, z2, z3)
        self._frame = (self._frame + 4) % 360

    def _cpu_poll(self) -> None:
        try:
            import psutil
            self._cpu_last = psutil.cpu_percent(interval=None)
        except Exception:
            self._cpu_last = 0
        self._tick()

    def _effect_statyczny(self):
        return self._colors["z1"], self._colors["z2"], self._colors["z3"]

    def _effect_dwukolorowy(self):
        offsets = [0, 40, 80]
        t = (math.sin(math.radians(self._frame)) + 1) / 2
        base = QColor(self._colors["z1"])
        base_b = QColor(self._color_b)
        cols = []
        for off in offsets:
            tt = (t + off / 360) % 1.0
            c = self._lerp_color(base.name(), base_b.name(), tt)
            cols.append(c)
        return cols[0], cols[1], cols[2]

    def _effect_wygaszony(self):
        return "#000000", "#000000", "#000000"

    def _effect_tęcza(self):
        c1 = QColor.fromHsv(self._frame, 255, 255)
        c2 = QColor.fromHsv((self._frame + 40) % 360, 255, 255)
        c3 = QColor.fromHsv((self._frame + 80) % 360, 255, 255)
        return c1.name(), c2.name(), c3.name()

    def _effect_oddychanie(self):
        bri = int((math.sin(math.radians(self._frame * 2)) + 1) * 127.5)
        col = QColor(self._colors["z1"])
        hsv = col.toHsv()
        out = QColor.fromHsv(hsv.hue(), hsv.saturation(), bri)
        return out.name(), out.name(), out.name()

    def _effect_puls_dwukolorowy(self):
        t = (math.sin(math.radians(self._frame * 2)) + 1) / 2
        col = self._lerp_color(self._colors["z1"], self._color_b, t)
        return col, col, col

    def _effect_własny_gradient(self):
        t = (self._frame / 360) * 3
        seg = int(t) % 3
        local_t = t - int(t)
        cols = [self._colors["z1"], self._colors["z2"], self._colors["z3"]]
        c = self._lerp_color(cols[seg], cols[(seg + 1) % 3], local_t)
        return c, c, c

    def _effect_wschód_słońca(self):
        phases = ["#000000", "#ff4400", "#ffaa00", "#ffffff"]
        t = self._frame / 360 * (len(phases) - 1)
        seg = min(int(t), len(phases) - 2)
        c = self._lerp_color(phases[seg], phases[seg + 1], t - seg)
        return c, c, c

    def _effect_kometa(self):
        step = (self._frame // 60) % 3
        bright = "#ffffff"
        dim = "#111111"
        cols = [dim, dim, dim]
        cols[step] = bright
        return cols[0], cols[1], cols[2]

    def _effect_błyskawica(self):
        if random.random() < 0.05:
            self._lightning_zone = random.choice(["z1", "z2", "z3"])
            self._lightning_frames = 4
        if self._lightning_frames > 0:
            cols = {"z1": "#111111", "z2": "#111111", "z3": "#111111"}
            cols[self._lightning_zone] = "#ffffff"
            self._lightning_frames -= 1
        else:
            cols = {"z1": "#111111", "z2": "#111111", "z3": "#111111"}
        return cols["z1"], cols["z2"], cols["z3"]

    def _effect_fala_kolorów(self):
        offsets = [0, 120, 240]
        cols = [QColor.fromHsv((self._frame + o) % 360, 255, 255) for o in offsets]
        return cols[0].name(), cols[1].name(), cols[2].name()

    def _effect_ogień(self):
        t = time.time()
        base_hues = [0, 15, 35]
        result = []
        for i, zone in enumerate(["z1", "z2", "z3"]):
            flicker = math.sin(t * 3.7 + i * 1.3) * 0.15 + random.uniform(-0.05, 0.05)
            bri = int(max(0, min(1, 0.8 + flicker)) * 255)
            col = QColor.fromHsv(base_hues[i], 255, bri)
            result.append(col.name())
        return result[0], result[1], result[2]

    def _effect_ocean(self):
        t = time.time()
        base_hues = [200, 190, 180]
        result = []
        for i, zone in enumerate(["z1", "z2", "z3"]):
            wave = math.sin(t * 1.5 + i * 0.8) * 0.2
            bri = int(max(0, min(1, 0.7 + wave)) * 255)
            col = QColor.fromHsv(base_hues[i], 220, bri)
            result.append(col.name())
        return result[0], result[1], result[2]

    def _effect_gwiezdna_noc(self):
        if random.random() < 0.08:
            z = random.choice(["z1", "z2", "z3"])
            self._star_state[z] = random.uniform(0.6, 1.0)
        result = []
        for z in ["z1", "z2", "z3"]:
            self._star_state[z] *= 0.92
            bri = int(self._star_state[z] * 255)
            col = QColor.fromHsv(220, 80, bri)
            result.append(col.name())
        return result[0], result[1], result[2]

    def _effect_monitor_cpu(self):
        if self._cpu_last is None:
            return "#000000", "#000000", "#000000"
        pct = self._cpu_last / 100.0
        hue = int(120 * (1 - pct))
        bri = int(100 + 155 * pct)
        col = QColor.fromHsv(hue, 255, bri)
        return col.name(), col.name(), col.name()

    def _effect_własny_sekwencyjny(self):
        if self._custom_effect is None:
            return self._colors["z1"], self._colors["z2"], self._colors["z3"]
        elapsed = time.time() * 1000
        if self._custom_effect.loop:
            elapsed %= self._custom_effect.duration_ms
        else:
            elapsed = min(elapsed, self._custom_effect.duration_ms)
        t = elapsed / self._custom_effect.duration_ms
        return self._custom_effect.get_colors_at(t)

    @staticmethod
    def _lerp_color(c1: str, c2: str, t: float) -> str:
        col1 = QColor(c1)
        col2 = QColor(c2)
        r = int(col1.red() + (col2.red() - col1.red()) * t)
        g = int(col1.green() + (col2.green() - col1.green()) * t)
        b = int(col1.blue() + (col2.blue() - col1.blue()) * t)
        return QColor(r, g, b).name()


engine = EffectEngine()
