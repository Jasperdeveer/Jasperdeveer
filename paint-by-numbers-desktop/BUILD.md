# JSPR Beamer Setup - Build Instructions

Dit document beschrijft hoe je JSPR Beamer Setup kunt bouwen als een standalone macOS applicatie (.app bundle).

## Vereisten

- macOS 10.14 of nieuwer
- Python 3.8 of nieuwer
- Xcode Command Line Tools (installeer met: `xcode-select --install`)

## Snelle Build (Aanbevolen)

De makkelijkste manier om de app te bouwen:

```bash
./build.sh
```

Dit script doet automatisch:
1. ✓ Controleert Python installatie
2. ✓ Maakt een virtual environment (indien nodig)
3. ✓ Installeert alle dependencies
4. ✓ Installeert py2app
5. ✓ Ruimt oude builds op
6. ✓ Bouwt de .app bundle
7. ✓ Opent de dist folder in Finder

## Handmatige Build

Als je liever handmatig wilt bouwen:

### 1. Virtual Environment (optioneel maar aanbevolen)

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Dependencies Installeren

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install py2app
```

### 3. Oude Builds Opruimen

```bash
rm -rf build dist
```

### 4. App Bouwen

```bash
python setup.py py2app
```

### 5. App Testen

```bash
open "dist/JSPR Beamer Setup.app"
```

## Na de Build

### De app gebruiken

Je gebouwde app staat in `dist/JSPR Beamer Setup.app`. Je kunt:

1. **Dubbelklikken** om de app te starten
2. **Verplaatsen naar /Applications**:
   ```bash
   cp -r "dist/JSPR Beamer Setup.app" /Applications/
   ```

### DMG maken voor distributie (optioneel)

Om een DMG installer te maken:

```bash
# Installeer create-dmg
brew install create-dmg

# Maak DMG
create-dmg \
  --volname "JSPR Beamer Setup" \
  --volicon "icon.icns" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "JSPR Beamer Setup.app" 175 120 \
  --hide-extension "JSPR Beamer Setup.app" \
  --app-drop-link 425 120 \
  "JSPR-Beamer-Setup-v1.0.dmg" \
  "dist/"
```

## Troubleshooting

### Build faalt met "ModuleNotFoundError"

Zorg ervoor dat alle dependencies geïnstalleerd zijn:
```bash
pip install -r requirements.txt
```

### App crasht bij starten

Test eerst in development mode:
```bash
python main.py
```

Kijk naar de logs in Console.app:
- Open Console.app
- Zoek naar "JSPR Beamer Setup"

### "App is beschadigd" melding

Als macOS zegt dat de app beschadigd is, moet je de quarantine attribuut verwijderen:
```bash
xattr -cr "dist/JSPR Beamer Setup.app"
```

### App werkt niet op andere Macs

Dit kan komen omdat:
1. De target Mac heeft niet dezelfde Python versie
2. De target Mac heeft niet dezelfde macOS versie

Oplossing: Build op de oudste macOS versie die je wilt ondersteunen.

## Code Signing (voor distributie)

Voor officiële distributie moet je de app code signen:

```bash
# Verkrijg een Developer ID certificaat van Apple

# Sign de app
codesign --deep --force --verify --verbose \
  --sign "Developer ID Application: Jouw Naam (TEAM_ID)" \
  "dist/JSPR Beamer Setup.app"

# Verifieer
codesign --verify --verbose=4 "dist/JSPR Beamer Setup.app"
spctl --assess --verbose=4 "dist/JSPR Beamer Setup.app"
```

## Build Configuratie

De build configuratie staat in `setup.py`. Belangrijke settings:

- **CFBundleVersion**: App versie (update voor elke release)
- **packages**: Python packages om te bundelen
- **includes**: Specifieke modules om te includeren
- **excludes**: Modules om NIET te bundelen (verkleint app size)
- **iconfile**: App icon (.icns bestand)

## App Grootte Verkleinen

De app is vrij groot (~250-500 MB) vanwege:
- OpenCV libraries
- NumPy/SciPy
- scikit-learn
- PyQt5

Om de grootte te verkleinen:

1. **Strip debug symbols** (al ingeschakeld in setup.py):
   ```python
   'strip': True
   ```

2. **Optimize bytecode** (al ingeschakeld):
   ```python
   'optimize': 2
   ```

3. **Exclude ongebruikte modules** in `setup.py`:
   ```python
   'excludes': ['matplotlib', 'pandas', ...]
   ```

## Development vs Production

Voor development:
```bash
python main.py
```

Voor production:
```bash
./build.sh
```

## Support

Bij problemen, check:
1. Python versie: `python3 --version` (moet 3.8+)
2. pip versie: `pip --version`
3. Dependencies: `pip list`
4. Console logs: Console.app

## Versie Updates

Bij nieuwe releases:

1. Update versie in `setup.py`:
   ```python
   'CFBundleVersion': '1.1.0',
   'CFBundleShortVersionString': '1.1.0',
   ```

2. Rebuild:
   ```bash
   ./build.sh
   ```

3. Test thoroughly op verschillende macOS versies

4. Create DMG voor distributie
