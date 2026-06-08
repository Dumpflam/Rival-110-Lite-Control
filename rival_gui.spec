# rival_gui.spec
from PyInstaller.building.api import PYZ, EXE, COLLECT
from PyInstaller.building.build_main import Analysis

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("assets/icon.ico", "assets"),
        ("locales", "locales"),
    ],
    hiddenimports=["rivalcfg", "psutil", "PyQt6.QtSvgWidgets"],
    hookspath=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="RivalLiteControl",
    icon="assets/icon.ico",
    console=False,
    onefile=True,
)
