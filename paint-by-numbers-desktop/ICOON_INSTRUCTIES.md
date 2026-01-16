# 🎨 App Icoon Instellen - Stap voor Stap

## Optie 1: Automatisch (met script)

### Stap 1: Zoek of maak een PNG icoon
Zorg dat je een PNG bestand hebt (bij voorkeur 512x512 of 1024x1024 pixels)
- Noem het bijvoorbeeld: `app_icon.png`
- Plaats het in de map: `~/Jasperdeveer/paint-by-numbers-desktop/`

### Stap 2: Converteer naar .icns (macOS icoon formaat)
Open Terminal en voer uit:

```bash
cd ~/Jasperdeveer/paint-by-numbers-desktop

# Maak een tijdelijke iconset map
mkdir -p AppIcon.iconset

# Genereer alle benodigde groottes (macOS vereist meerdere)
sips -z 16 16     app_icon.png --out AppIcon.iconset/icon_16x16.png
sips -z 32 32     app_icon.png --out AppIcon.iconset/icon_16x16@2x.png
sips -z 32 32     app_icon.png --out AppIcon.iconset/icon_32x32.png
sips -z 64 64     app_icon.png --out AppIcon.iconset/icon_32x32@2x.png
sips -z 128 128   app_icon.png --out AppIcon.iconset/icon_128x128.png
sips -z 256 256   app_icon.png --out AppIcon.iconset/icon_128x128@2x.png
sips -z 256 256   app_icon.png --out AppIcon.iconset/icon_256x256.png
sips -z 512 512   app_icon.png --out AppIcon.iconset/icon_256x256@2x.png
sips -z 512 512   app_icon.png --out AppIcon.iconset/icon_512x512.png
sips -z 1024 1024 app_icon.png --out AppIcon.iconset/icon_512x512@2x.png

# Converteer iconset naar .icns
iconutil -c icns AppIcon.iconset

# Kopieer naar app bundle
cp AppIcon.icns "JSPR Beamer Setup.app/Contents/Resources/icon.icns"

# Ruim op
rm -rf AppIcon.iconset
```

### Stap 3: Vernieuw icoon cache
```bash
# Vertel macOS dat het icoon is veranderd
touch "JSPR Beamer Setup.app"

# Herstart Dock om icoon te verversen
killall Dock
```

---

## Optie 2: Handmatig (via Finder)

### Als je al een .icns bestand hebt:

1. Ga naar map: `paint-by-numbers-desktop/JSPR Beamer Setup.app/Contents/Resources/`
2. Kopieer je `.icns` bestand daarheen
3. Hernoem het naar: `icon.icns`
4. Open Terminal en voer uit:
   ```bash
   cd ~/Jasperdeveer/paint-by-numbers-desktop
   touch "JSPR Beamer Setup.app"
   killall Dock
   ```

---

## Optie 3: Online Converter

Als je geen Terminal wilt gebruiken:

1. Ga naar: https://cloudconvert.com/png-to-icns
2. Upload je PNG icoon
3. Download het .icns bestand
4. Volg "Optie 2: Handmatig" hierboven

---

## Verificatie

Na het instellen:
- De app in Finder zou je icoon moeten tonen
- Als je de app naar je Dock sleept, verschijnt het icoon daar ook

Als het icoon niet direct verschijnt:
```bash
# Force refresh
killall Finder
killall Dock
```

---

## 💡 Tips voor een mooi icoon:

- **Formaat**: 1024x1024px werkt het best
- **Transparantie**: PNG met transparante achtergrond ziet er professioneel uit
- **Simpel design**: Duidelijk herkenbaar, ook in klein formaat (16x16)
- **Ronde hoeken**: macOS voegt automatisch ronde hoeken toe

---

## Voorbeeld icoon ideeën voor JSPR Beamer Setup:

- 🎨 Verfbus/spuitbus icoon
- 📐 Raster/grid met nummers
- 🖼️ Canvas met projectie stralen
- 🎭 Gestileerde street art afbeelding

---

**Need help?** Stuur me de PNG en ik help je converteren! 🚀
