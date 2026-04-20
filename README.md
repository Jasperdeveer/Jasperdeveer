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
Werkt op **iPhone** — installeer via Safari als app op je beginscherm.

### Functies

- Automatisch detecteren van nieuwsbrieven via `List-Unsubscribe` header
- **Spamkans-voorspelling** op basis van 10+ signalen (SPF/DKIM, spamwoorden, verdacht domein…)
- Uitschrijven via website of e-mail
- Afzender blokkeren + naar Ongewenste e-mail verplaatsen
- Bulk-blokkeren: meerdere afzenders tegelijk
- Beveiligde sessies: HttpOnly-cookies, HTTPS-only, session timeout
- PWA — installeerbaar op iPhone-beginscherm via Safari

### Deployment op Railway (gratis)

1. Maak een account op [railway.app](https://railway.app) via GitHub
2. **New Project → Deploy from GitHub repo** → selecteer deze repo
3. Noteer de gegenereerde URL (bijv. `https://xxx.up.railway.app`)
4. Maak een [Azure App Registratie](https://portal.azure.com) aan (persoonlijke accounts, redirect URI = `https://xxx.up.railway.app/callback`)
5. Stel in Railway de variabelen in: `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID=common`, `REDIRECT_URI`, `FLASK_SECRET_KEY`, `HTTPS_ONLY=true`
6. Open de app in Safari op iPhone → Deel-icoon → **"Zet op beginscherm"**

De app zelf legt alle stappen uit zodra je hem opent.
