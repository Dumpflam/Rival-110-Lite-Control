# Adding a new language

1. Copy `en.json` to `xx.json` (ISO 639-1 code, e.g. `de.json`, `fr.json`)
2. Translate all values — do NOT change the keys
3. Keys with `{placeholders}` must keep the placeholder unchanged
4. Place the file in the `locales/` folder next to the app
5. The app will detect it automatically on next launch
