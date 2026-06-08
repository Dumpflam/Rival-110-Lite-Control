from dataclasses import dataclass, field
from PyQt6.QtGui import QColor


@dataclass
class Keyframe:
    position: float
    z1: str = "#ff0000"
    z2: str = "#00ff00"
    z3: str = "#0000ff"

    def to_dict(self) -> dict:
        return {"position": self.position, "z1": self.z1, "z2": self.z2, "z3": self.z3}

    @classmethod
    def from_dict(cls, d: dict) -> "Keyframe":
        return cls(d["position"], d["z1"], d["z2"], d["z3"])


@dataclass
class CustomEffect:
    name: str = "Mój Efekt"
    duration_ms: int = 2000
    loop: bool = True
    keyframes: list[Keyframe] = field(default_factory=list)

    def get_colors_at(self, t: float) -> tuple[str, str, str]:
        kfs = sorted(self.keyframes, key=lambda k: k.position)
        if not kfs:
            return "#000000", "#000000", "#000000"
        if t <= kfs[0].position:
            k = kfs[0]
            return k.z1, k.z2, k.z3
        if t >= kfs[-1].position:
            k = kfs[-1]
            return k.z1, k.z2, k.z3
        for i in range(len(kfs) - 1):
            a, b = kfs[i], kfs[i + 1]
            if a.position <= t <= b.position:
                local = (t - a.position) / (b.position - a.position)
                return (
                    _lerp(a.z1, b.z1, local),
                    _lerp(a.z2, b.z2, local),
                    _lerp(a.z3, b.z3, local),
                )
        return "#000000", "#000000", "#000000"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "duration_ms": self.duration_ms,
            "loop": self.loop,
            "keyframes": [k.to_dict() for k in self.keyframes],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CustomEffect":
        effect = cls(
            name=d.get("name", "Mój Efekt"),
            duration_ms=d.get("duration_ms", 2000),
            loop=d.get("loop", True),
        )
        effect.keyframes = [Keyframe.from_dict(k) for k in d.get("keyframes", [])]
        return effect


def _lerp(c1: str, c2: str, t: float) -> str:
    col1 = QColor(c1)
    col2 = QColor(c2)
    r = int(col1.red() + (col2.red() - col1.red()) * t)
    g = int(col1.green() + (col2.green() - col1.green()) * t)
    b = int(col1.blue() + (col2.blue() - col1.blue()) * t)
    return QColor(r, g, b).name()
