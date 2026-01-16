# 🚀 JSPR Beamer Setup - Eenvoudig Starten

## Optie 1: Gebruik de macOS App (Aanbevolen)

### Eerste keer installatie:

1. **Dubbelklik op "JSPR Beamer Setup.app"** in deze map
   - De app zou moeten starten!

2. **Als je een beveiligingswaarschuwing krijgt:**
   - Ga naar **Systeemvoorkeuren** → **Beveiliging en Privacy**
   - Klik op **"Toch openen"** onderaan
   - Of: rechtsklik op de app → **Openen** → **Openen** bevestigen

3. **Sleep de app naar je Dock:**
   - Sleep **"JSPR Beamer Setup.app"** naar je Dock
   - Nu kun je de app altijd met één klik starten!

### Dagelijks gebruik:

- Klik gewoon op het icoon in je Dock
- Klaar! De app start automatisch met de juiste instellingen

---

## Optie 2: Terminal Script (Alternatief)

Als de .app niet werkt, gebruik dan het bash script:

```bash
cd ~/Jasperdeveer/paint-by-numbers-desktop
./start_app.sh
```

---

## Problemen?

### "Virtual environment not found"
```bash
cd ~/Jasperdeveer/paint-by-numbers-desktop
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### App start niet / crash
1. Open Terminal
2. Ga naar de app directory: `cd ~/Jasperdeveer/paint-by-numbers-desktop`
3. Start handmatig om errors te zien: `./start_app.sh`

### Updates ophalen
```bash
cd ~/Jasperdeveer/paint-by-numbers-desktop
git pull
```

De app in je Dock blijft werken na updates!

---

## ⚡ Tips

- **Sneltoets**: Voeg de app toe aan je Dock voor directe toegang
- **Updates**: Doe `git pull` in de terminal, de app in je Dock blijft gewoon werken
- **Meerdere vensters**: Je kunt de app meerdere keren openen voor verschillende projecten

---

**Gemaakt voor JSPR street art projecten** 🎨
