- 👋 Hi, I'm @Jasperdeveer
- 👀 I'm interested in graphic design, photography and music production
- 🌱 I'm currently learning jquery and react
- 📫 Info@jasperdeveer.nl 

<!---
Jasperdeveer/Jasperdeveer is a ✨ special ✨ repository because its `README.md` (this file) appears on your GitHub profile.
You can click the Preview link to take a look at your changes.
--->

---

## Spam Uitschrijver

Web-app (PWA) om snel nieuwsbrieven en spam te blokkeren vanuit je **@live.nl** inbox.
Werkt ook op **iPhone** — installeer hem via Safari als app op je beginscherm.

### Functies

- Automatisch detecteren van nieuwsbrieven via `List-Unsubscribe` header
- **Spamkans-voorspelling** op basis van 10+ signalen (SPF/DKIM, spamwoorden, verdacht domein, enz.)
- Uitschrijven via website of e-mail
- Afzender blokkeren (Microsoft-mailboxinstelling) + naar Ongewenste e-mail verplaatsen
- Bulk-blokkeren: meerdere afzenders tegelijk
- PWA — installeerbaar op iPhone-beginscherm via Safari

---

### Installeren op iPhone (na deployment)

1. Open de app-URL in **Safari**
2. Tik op het **Deel-icoon** (vierkantje met pijl omhoog)
3. Kies **"Zet op beginscherm"**
4. De app opent voortaan als een echte app, zonder adresbalk

---

### Deployment op Railway (gratis, ~3 minuten)

**Stap 1 — Azure App Registratie aanmaken**

Ga naar [portal.azure.com](https://portal.azure.com):
- App registraties → Nieuwe registratie
- Accounttype: *Persoonlijke Microsoft-accounts*
- Redirect URI: `https://<jouw-app>.up.railway.app/callback`

Kopieer de **Client ID** en maak een **Client Secret** aan.

**Stap 2 — Railway project aanmaken**

1. Ga naar [railway.app](https://railway.app) en log in met GitHub
2. Klik op **New Project → Deploy from GitHub repo**
3. Selecteer deze repository

**Stap 3 — Omgevingsvariabelen instellen**

Ga in Railway naar je project → tabblad **Variables** en voeg toe:

| Variabele | Waarde |
|---|---|
| `AZURE_CLIENT_ID` | jouw Client ID |
| `AZURE_CLIENT_SECRET` | jouw Client Secret |
| `AZURE_TENANT_ID` | `common` |
| `REDIRECT_URI` | `https://<jouw-app>.up.railway.app/callback` |
| `FLASK_SECRET_KEY` | een lange willekeurige string |

**Stap 4 — Klaar!**

Railway geeft je een URL (bijv. `https://spam-uitschrijver.up.railway.app`).
Voeg die URL toe als Redirect URI in je Azure App Registratie.

---

### Lokaal draaien

```bash
pip install -r requirements.txt
cp .env.example .env   # vul je waarden in
python app.py
```

Open `http://localhost:5000` in je browser.
