# Rival Lite Control

Lekki, otwartoźródłowy panel sterowania dla myszy SteelSeries Rival na Windows. Zbudowany w Pythonie i PyQt6, komunikuje się z myszką bezpośrednio przez HID przy użyciu biblioteki [rivalcfg](https://github.com/flozz/rivalcfg) — bez SteelSeries GG.

> 🇬🇧 [English README](README.md)

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.4%2B-green)
![Windows](https://img.shields.io/badge/platforma-Windows-lightgrey)
![License](https://img.shields.io/badge/licencja-MIT-orange)

---

## Funkcje

- **16 efektów RGB** — Statyczny, Dwukolorowy, Wygaszony, Tęcza, Oddychanie, Puls Dwukolorowy, Własny Gradient, Wschód Słońca, Kometa, Błyskawica, Fala Kolorów, Ogień, Ocean, Gwiezdna Noc, Monitor CPU, Własny Sekwencyjny
- **Edytor własnych efektów** — timeline z keyframe'ami, przeciąganie myszą, kontrola kolorów per strefa
- **System profili** — tworzenie, zapis, ładowanie, usuwanie, eksport i import profili (`.rivalprofile`)
- **Losowy efekt** — losuje efekt i kolory jednym kliknięciem
- **Podgląd myszki** — żywy podgląd SVG trzech stref LED w sidebarze
- **Zasobnik systemowy** — minimalizacja do traya, działa w tle
- **Autostart** — opcjonalne uruchamianie z Windows przez rejestr
- **Tryb Zaćmienia** — błysk RGB na kliknięcie lewym przyciskiem myszy
- **Monitor CPU** — kolor LED reaguje na obciążenie procesora w czasie rzeczywistym
- **Wielojęzyczność** — automatyczne wykrywanie języka systemu, zmiana w Ustawieniach
- **Tłumaczenia społeczności** — dodaj swój język wrzucając plik JSON do `locales/`

---

## Zrzuty ekranu

> *(Dodaj zrzuty ekranu tutaj)*

---

## Wymagania

- Windows 10 / 11
- Python 3.10+
- Obsługiwana mysz SteelSeries Rival (lista: [rivalcfg supported devices](https://github.com/flozz/rivalcfg#supported-mice))

---

## Instalacja

```bash
git clone https://github.com/AnonBOTpl/rival-lite-control.git
cd rival-lite-control
pip install -r requirements.txt
python main.py
```

### Build do pliku `.exe`

```bash
pip install pyinstaller
python scripts/generate_icon.py   # najpierw wygeneruj assets/icon.ico
pyinstaller rival_gui.spec
```

Plik wykonywalny znajdziesz w `dist/RivalLiteControl.exe`.

---

## Struktura projektu

```
rival_gui/
├── main.py                        # punkt wejścia
├── requirements.txt
├── rival_gui.spec                 # konfiguracja PyInstaller
├── assets/
│   └── icon.ico
├── locales/
│   ├── en.json                    # angielski (domyślny)
│   ├── pl.json                    # polski
│   └── README.md                  # przewodnik dla tłumaczy
├── core/
│   ├── config.py                  # stałe, ścieżki, lista efektów
│   ├── hid_manager.py             # komunikacja HID (rivalcfg)
│   ├── effect_engine.py           # silnik animacji, wszystkie efekty
│   ├── profile_manager.py         # CRUD profili, zapis/odczyt configu
│   ├── custom_effect.py           # model danych keyframe
│   ├── custom_effect_manager.py   # zapis własnych efektów
│   └── i18n.py                    # internacjonalizacja
├── ui/
│   ├── main_window.py             # główne okno, spięcie sygnałów
│   ├── effect_grid.py             # grid kafelków efektów
│   ├── effect_panel.py            # panel ustawień efektu
│   ├── sidebar.py                 # podgląd myszki + panel profili
│   ├── bottom_bar.py              # jasność, prędkość, przycisk zastosuj
│   ├── settings_dialog.py         # okno ustawień
│   ├── keyframe_editor.py         # edytor własnych efektów
│   └── mouse_svg.py               # szablon SVG podglądu myszki
└── scripts/
    └── generate_icon.py           # generuje assets/icon.ico
```

---

## Dodawanie tłumaczenia

1. Skopiuj `locales/en.json` do `locales/xx.json` (np. `de.json` dla niemieckiego)
2. Przetłumacz wszystkie **wartości** — nie zmieniaj **kluczy**
3. Zostaw `{placeholders}` bez zmian
4. Wrzuć plik do folderu `locales/` — aplikacja wykryje go automatycznie
5. Wyślij pull request 🎉

Szczegóły w `locales/README.md`.

---

## Jak to działa

Rival Lite Control komunikuje się z myszką bezpośrednio przez USB HID używając [rivalcfg](https://github.com/flozz/rivalcfg). Wszystkie efekty RGB są obliczane programowo i wysyłane do myszki z częstotliwością do 30 FPS. Efekty sprzętowe (Tęcza) używają wbudowanego chipa myszki dla płynniejszej animacji.

---

## Licencja

MIT — możesz używać, modyfikować i dystrybuować swobodnie.

---

## Podziękowania

- [rivalcfg](https://github.com/flozz/rivalcfg) autorstwa flozz — podstawa komunikacji HID
- Zbudowane z [PyQt6](https://pypi.org/project/PyQt6/)
