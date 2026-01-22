# JSPR Beamer Setup - Installatie Handleiding

Volledige installatie-instructies voor JSPR Beamer Setup op een nieuwe laptop.

## Systeemvereisten

- **Python**: 3.8 of hoger
- **Git**: Voor het clonen van de repository
- **Besturingssysteem**: macOS (M1/M2/M3 of Intel) of Linux

## Snelle Installatie (Aanbevolen)

### Stap 1: Clone de Repository

```bash
# Ga naar de gewenste directory (bijv. Documents)
cd ~/Documents

# Clone de repository
git clone https://github.com/[JOUW-USERNAME]/Jasperdeveer.git
cd Jasperdeveer/paint-by-numbers-desktop
```

### Stap 2: Run de Installer

```bash
# Maak het installatiescript uitvoerbaar
chmod +x setup.sh

# Voer de installatie uit
./setup.sh
```

De installer doet automatisch:
- ✓ Python versie check
- ✓ Virtual environment aanmaken
- ✓ Alle dependencies installeren
- ✓ Branches (stable/dev) setup
- ✓ Launcher configureren

### Stap 3: Start de App

Na installatie kun je de app starten:

**macOS:**
```bash
# Via de .command file (dubbelklik in Finder)
# Of via terminal:
./launch.sh
```

**Linux:**
```bash
./launch.sh
# Of zoek "JSPR Beamer Setup" in je applicatie menu
```

## Handmatige Installatie

Als je het stap voor stap wilt doen:

### 1. Clone de Repository

```bash
cd ~/Documents
git clone https://github.com/[JOUW-USERNAME]/Jasperdeveer.git
cd Jasperdeveer/paint-by-numbers-desktop
```

### 2. Python Virtual Environment

```bash
# Check Python versie (moet 3.8+ zijn)
python3 --version

# Maak virtual environment aan
python3 -m venv venv

# Activeer de venv
# macOS/Linux:
source venv/bin/activate

# Je prompt zou nu (venv) moeten tonen
```

### 3. Installeer Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Installeer alle benodigde packages
pip install -r requirements.txt
```

**Let op:** De installatie kan 5-10 minuten duren (vooral opencv en scikit-learn zijn groot).

### 4. Verifieer de Installatie

```bash
# Test of PyQt5 werkt
python3 -c "from PyQt5.QtWidgets import QApplication; print('✓ PyQt5 OK')"

# Test of OpenCV werkt
python3 -c "import cv2; print('✓ OpenCV OK')"

# Test of de app kan starten
python3 main.py
```

### 5. Setup Launchers

```bash
# Maak alle scripts uitvoerbaar
chmod +x *.sh
chmod +x "Start JSPR Beamer.command"

# macOS: Dubbelklik op "Start JSPR Beamer.command" in Finder
# Linux: Run ./install.sh voor systeem-integratie
```

## Git Branches

Het project heeft twee branches:

- **`stable`**: Productie versie (stabiel en getest)
- **`dev`**: Development versie (nieuwste features)

Bij de eerste start krijg je een popup om te kiezen welke versie je wilt gebruiken.

### Handmatig Branch Wisselen

```bash
# Naar stable
git checkout stable

# Naar development
git checkout dev

# Terug naar de claude branch
git checkout claude/enhance-line-drawing-precision-kyhzU
```

## Veelvoorkomende Problemen

### "python3: command not found"

**Oplossing:**
- macOS: Installeer via [python.org](https://www.python.org/downloads/)
- Linux: `sudo apt install python3 python3-pip python3-venv`

### "pip install failed" met permission errors

**Oplossing:**
```bash
# Gebruik NOOIT sudo pip!
# Gebruik altijd een virtual environment:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Virtual environment niet gevonden

**Oplossing:**
```bash
# Maak opnieuw aan
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### macOS: "App kan niet geopend worden omdat ontwikkelaar niet geverifieerd is"

**Oplossing:**
```bash
# Rechtsklik op de app → Open
# Of gebruik de terminal launcher:
./launch.sh
```

### PyQt5 installeert niet op M1/M2/M3 Mac

**Oplossing:**
```bash
# Installeer Rosetta 2 (eenmalig)
/usr/sbin/softwareupdate --install-rosetta

# Of gebruik homebrew python:
brew install python@3.11
/opt/homebrew/bin/python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Dependencies installeren duurt heel lang

**Normaal!** OpenCV en scikit-learn zijn grote packages:
- macOS M1/M2: 5-8 minuten
- macOS Intel: 3-5 minuten
- Linux: 3-5 minuten

Heb geduld en laat het afmaken.

### "Git branch checkout failed"

**Oplossing:**
```bash
# Check of je ongeslagen wijzigingen hebt
git status

# Stash lokale wijzigingen
git stash

# Probeer opnieuw
git checkout stable
```

## Updates Ophalen

Om de nieuwste versie te krijgen:

```bash
# Zorg dat je geen ongeslagen wijzigingen hebt
git status

# Update de huidige branch
git pull origin $(git branch --show-current)

# Of gebruik de update scripts:
./update_stable.sh    # Voor stable versie
./update_dev.sh       # Voor dev versie
```

## Dock/Taskbar Icon Toevoegen

### macOS

1. Open Finder → Ga naar de `paint-by-numbers-desktop` folder
2. Sleep `Start JSPR Beamer.command` naar je Dock
3. Rechtsklik het icon → Options → Keep in Dock

**Voor een mooier icon:**
1. Rechtsklik `JSPR Beamer Setup.app` → Get Info
2. Sleep `assets/icon.png` over het kleine icon linksboven
3. Sleep de .app naar je Dock

### Linux (Ubuntu/Debian)

```bash
# Run de installer (maakt desktop entry aan)
./install.sh

# Zoek "JSPR Beamer Setup" in je applicatie menu
# Sleep naar taskbar om vast te pinnen
```

## Deïnstallatie

```bash
# Verwijder virtual environment
rm -rf venv

# Verwijder de hele folder
cd ..
rm -rf paint-by-numbers-desktop

# macOS: Verwijder van Dock (rechtsklik → Remove from Dock)
# Linux: Verwijder desktop entry
rm ~/.local/share/applications/jspr-beamer.desktop
```

## Scripts Overzicht

| Script | Functie |
|--------|---------|
| `setup.sh` | 🆕 Volledige installatie (nieuw) |
| `launch.sh` | Start app met version selector |
| `run_stable.sh` | Direct stable versie starten |
| `run_dev.sh` | Direct dev versie starten |
| `update_stable.sh` | Update stable van git |
| `update_dev.sh` | Update dev van git |
| `merge_dev_to_stable.sh` | Merge dev → stable |
| `Start JSPR Beamer.command` | macOS launcher (dubbelklik) |
| `install.sh` | Linux systeem-integratie |

## Hulp Nodig?

- **Documentatie**: Zie `README_WORKFLOW.md` voor Git workflow
- **Logs**: Check `/tmp/jspr_app_launcher.log` bij crashes
- **Issues**: [GitHub Issues](https://github.com/[JOUW-USERNAME]/Jasperdeveer/issues)

## Eerste Gebruik

Bij eerste start:
1. Kies "Stable Versie" (groen) → veilig en getest
2. Laad een afbeelding (File → Open Image)
3. Kies aantal kleuren (5-50)
4. Klik "Generate" en wacht
5. Exporteer als PDF of SVG (File → Export)

Veel plezier! 🎨
