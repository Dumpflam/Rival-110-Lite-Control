import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt


def make_pixmap(size: int) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    margin = max(1, size // 16)
    p.setBrush(QColor("#0088cc"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(margin, margin, size - 2*margin, size - 2*margin)
    inner = size // 3
    offset = size // 2 - inner // 2
    p.setBrush(QColor("#ffffff"))
    p.setOpacity(0.15)
    p.drawEllipse(offset, offset, inner, inner)
    p.end()
    return pix


def main():
    app = QApplication(sys.argv)
    out = Path(__file__).resolve().parent.parent / "assets" / "icon.ico"
    out.parent.mkdir(exist_ok=True)

    sizes = [16, 24, 32, 48, 64, 128, 256]
    icon = QIcon()
    for s in sizes:
        icon.addPixmap(make_pixmap(s))

    pix = make_pixmap(256)
    pix.save(str(out), "ICO")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
