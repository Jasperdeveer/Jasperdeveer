# PadelScore — Installatie op je Mac

## Vereisten
- Mac met macOS 14+
- Xcode 15+ (gratis via App Store)
- iPhone met je Apple ID ingelogd
- Apple Watch Series 4 of nieuwer

## Stap 1: xcodegen installeren

```bash
brew install xcodegen
```

Als je Homebrew nog niet hebt:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

## Stap 2: Xcode project aanmaken

```bash
cd PadelScore
xcodegen generate
open PadelScore.xcodeproj
```

## Stap 3: Signing instellen in Xcode

1. Klik op **PadelScore** in de project navigator (blauw icoontje links)
2. Selecteer target **PadelScore** → tab **Signing & Capabilities**
3. Zet **Automatically manage signing** aan
4. Kies je **Team** (je persoonlijke Apple ID — gratis account werkt)
5. Doe hetzelfde voor target **PadelScore Watch App**

## Stap 4: Installeren op je iPhone + Watch

1. Verbind je iPhone met de Mac via USB
2. Selecteer **PadelScore** als scheme (linksboven in Xcode)
3. Selecteer je iPhone als destination
4. Druk op **▶ Run** (of ⌘R)
5. De Watch app wordt automatisch meegeïnstalleerd op je gekoppelde Watch

## Gratis account — app verloopt na 7 dagen

Na 7 dagen moet je de app opnieuw installeren via Xcode (stap 4 herhalen).
Met AltStore + AltServer op je Mac gaat dit automatisch op de achtergrond.

### AltStore instellen (optioneel, automatisch verlengen)

1. Download AltServer op je Mac: https://altstore.io
2. Installeer AltStore op je iPhone via AltServer
3. Exporteer een `.ipa` van je app: Xcode → Product → Archive → Distribute → Ad Hoc
4. Open AltStore op je iPhone → My Apps → + → kies de `.ipa`
5. AltServer verlengt automatisch elke 7 dagen zolang je Mac aan staat
