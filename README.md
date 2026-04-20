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

Een web-app om snel nieuwsbrieven en spam te blokkeren vanuit je **@live.nl** inbox (werkt ook met @outlook.com en @hotmail.com).

### Functies

- Automatisch detecteren van nieuwsbrieven via de `List-Unsubscribe` e-mailheader
- Uitschrijven via een klik op de afmeldlink (website)
- Uitschrijven via e-mail (mailto-link)
- Afzender blokkeren via je Microsoft mailboxinstellingen
- E-mail direct naar de map Ongewenste e-mail verplaatsen

### Installatie

**1. Azure App Registratie aanmaken**

Ga naar [portal.azure.com](https://portal.azure.com) → Azure Active Directory → App registraties → Nieuwe registratie.

- Ondersteunde accounttypen: *Persoonlijke Microsoft-accounts*
- Redirect URI: `http://localhost:5000/callback`

Kopieer daarna de **Client ID** en maak een **Client Secret** aan onder *Certificaten en geheimen*.

**2. Installeer de dependencies**

```bash
pip install -r requirements.txt
```

**3. Maak een `.env` bestand aan**

```bash
cp .env.example .env
# Vul je Azure Client ID, Secret en een willekeurige FLASK_SECRET_KEY in
```

**4. Start de app**

```bash
python app.py
```

Open `http://localhost:5000` in je browser en log in met je Microsoft-account.
