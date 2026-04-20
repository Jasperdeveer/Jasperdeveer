"""
Spam-kans berekenen op basis van e-mailkenmerken.

Signalen (gewogen):
  Onderwerp      - spamwoorden (NL+EN), te veel hoofdletters, uitroeptekens, geldbedragen
  Afzender       - verdachte TLD, gratis provider, reply-to afwijking, willekeurig ogend adres
  Headers        - SPF/DKIM-status, X-Spam-Score, verdachte X-Mailer
  Berichttekst   - spamwoorden in preview, urgentie, loterij
  Patroon        - hoge verzendfrequentie van dezelfde afzender
"""

import re

# ---------------------------------------------------------------------------
# Woordenlijsten
# ---------------------------------------------------------------------------

_SPAM_WORDS_NL = [
    "gratis", "gewonnen", "prijs", "aanbieding", "korting",
    "verloting", "klik hier", "dringend", "actie vereist",
    "bevestig je account", "verificatie vereist", "tijdelijk aanbod",
    "laatste kans", "exclusief aanbod", "speciale aanbieding",
    "nu bestellen", "nu kopen", "bestel nu", "ontvang nu",
    "gefeliciteerd", "u bent geselecteerd", "u heeft gewonnen",
    "claim uw prijs", "geen risico", "100% gratis", "geld verdienen",
    "extra inkomen", "werk vanuit huis", "snel geld",
]

_SPAM_WORDS_EN = [
    "free", "winner", "won", "prize", "offer", "discount",
    "click here", "urgent", "action required", "verify your account",
    "limited time", "exclusive offer", "special offer", "order now",
    "free shipping", "last chance", "congratulations", "you have been selected",
    "claim your prize", "no risk", "100% free", "make money",
    "earn money", "work from home", "fast cash", "million dollars",
    "billion", "inheritance", "lottery", "selected winner", "reward",
    "account suspended", "confirm your identity", "unusual activity",
]

_URGENCY_WORDS = [
    "nu", "direct", "onmiddellijk", "vandaag", "snel", "spoedig",
    "immediately", "today only", "expires", "expiring", "act now",
    "dont miss", "don't miss", "hurry",
]

# TLD's die veel worden misbruikt
_SUSPICIOUS_TLDS = {
    ".xyz", ".top", ".click", ".bid", ".work", ".loan", ".win",
    ".stream", ".gq", ".cf", ".tk", ".ml", ".ga", ".monster",
    ".cyou", ".icu", ".sbs", ".cfd", ".hair",
}

# Gratis providers zijn ongebruikelijk als nieuwsbriefafzender
_FREE_PROVIDERS = {
    "gmail.com", "yahoo.com", "yahoo.fr", "yahoo.co.uk", "yahoo.ca",
    "hotmail.com", "outlook.com", "aol.com", "yandex.com", "mail.ru",
    "protonmail.com", "gmx.com", "gmx.net", "icloud.com", "me.com",
}

# Bekende bulk-mail software — op zichzelf geen spam, maar scoort mee
_BULK_MAILERS = [
    "mailchimp", "sendgrid", "constantcontact", "klaviyo",
    "mailgun", "brevo", "sendinblue", "aweber", "getresponse",
]


# ---------------------------------------------------------------------------
# Hulpfuncties
# ---------------------------------------------------------------------------

def _caps_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if c.isupper()) / len(letters)


def _count_words(text: str, word_list: list[str]) -> list[str]:
    lower = text.lower()
    return [w for w in word_list if w in lower]


def _looks_random(local: str) -> bool:
    """Heuristiek: lokaal deel van e-mailadres ziet er willekeurig gegenereerd uit."""
    if len(local) < 8:
        return False
    digit_ratio = sum(1 for c in local if c.isdigit()) / len(local)
    return digit_ratio > 0.4 or bool(re.search(r"[a-z]{2}\d{4,}", local))


# ---------------------------------------------------------------------------
# Hoofdfunctie
# ---------------------------------------------------------------------------

def score_email(
    subject: str,
    sender_email: str,
    headers: dict,
    body_preview: str = "",
    sender_count: int = 1,
) -> dict:
    """
    Geeft een dict terug:
      score   : int  0-100
      label   : str  leesbare omschrijving
      color   : str  Bootstrap kleurnaam (danger / warning / info / success)
      icon    : str  Bootstrap Icons klasse
      reasons : list korte uitleg per gevonden signaal
    """
    score = 0
    reasons: list[str] = []

    subject = subject or ""
    body_preview = body_preview or ""
    sender_email = (sender_email or "").lower()
    domain = sender_email.split("@")[-1] if "@" in sender_email else ""
    local = sender_email.split("@")[0] if "@" in sender_email else ""

    # ── Onderwerp ────────────────────────────────────────────────────────────

    spam_in_subject = _count_words(subject, _SPAM_WORDS_NL + _SPAM_WORDS_EN)
    if spam_in_subject:
        pts = min(len(spam_in_subject) * 8, 28)
        score += pts
        sample = ", ".join(f'"{w}"' for w in spam_in_subject[:3])
        reasons.append(f"Spamwoorden in onderwerp: {sample}")

    if _caps_ratio(subject) > 0.45 and len(subject) > 4:
        score += 12
        reasons.append("Veel hoofdletters in onderwerp")

    excl = subject.count("!") + subject.count("?")
    if excl >= 2:
        score += 8
        reasons.append(f"Overdadig leesteken gebruik ({excl}× ! of ?)")

    if re.search(r"[€$£]\s*[\d,.]+|[\d,.]+\s*[€$£]", subject):
        score += 12
        reasons.append("Geldbedrag in onderwerp")

    urgency_in_subject = _count_words(subject, _URGENCY_WORDS)
    if urgency_in_subject:
        score += 8
        reasons.append(f"Urgentietaal in onderwerp: {urgency_in_subject[0]!r}")

    # ── Berichttekst (preview) ───────────────────────────────────────────────

    spam_in_body = _count_words(body_preview, _SPAM_WORDS_NL + _SPAM_WORDS_EN)
    if len(spam_in_body) >= 3:
        score += 10
        reasons.append(f"Spamwoorden in berichttekst ({len(spam_in_body)} stuks)")

    if re.search(r"[€$£]\s*[\d,.]+|[\d,.]+\s*[€$£]", body_preview):
        score += 8
        reasons.append("Geldbedrag in berichttekst")

    # ── Afzender ─────────────────────────────────────────────────────────────

    for tld in _SUSPICIOUS_TLDS:
        if domain.endswith(tld):
            score += 22
            reasons.append(f"Verdacht afzenderdomein ({domain})")
            break

    if domain in _FREE_PROVIDERS:
        score += 14
        reasons.append(f"Gratis e-mailprovider als nieuwsbriefzender ({domain})")

    if _looks_random(local):
        score += 10
        reasons.append("Willekeurig ogend e-mailadres")

    reply_to = headers.get("reply-to", "")
    if reply_to and sender_email and sender_email not in reply_to.lower():
        score += 18
        reasons.append("Reply-to-adres wijkt af van afzender")

    # ── Authenticatie (SPF / DKIM) ───────────────────────────────────────────

    auth = headers.get("authentication-results", "").lower()
    if auth:
        if "spf=fail" in auth:
            score += 28
            reasons.append("SPF-verificatie mislukt (e-mail mogelijk vervalst)")
        elif "dkim=fail" in auth:
            score += 22
            reasons.append("DKIM-verificatie mislukt (e-mail mogelijk vervalst)")
        elif "spf=none" in auth and "dkim=none" in auth:
            score += 12
            reasons.append("Geen SPF- of DKIM-authenticatie aanwezig")
        elif "spf=softfail" in auth:
            score += 10
            reasons.append("SPF softfail (afzender niet volledig gemachtigd)")

    # ── X-Spam-Score header ──────────────────────────────────────────────────

    for hname in ("x-spam-score", "x-spam-level", "x-ms-exchange-antispam-messagedataforcontent"):
        raw = headers.get(hname, "")
        if raw:
            m = re.search(r"[\d.]+", raw)
            if m:
                val = float(m.group())
                if val > 3:
                    pts = min(int(val * 4), 25)
                    score += pts
                    reasons.append(f"Hoge spam-score in headers ({val:.1f})")
            break

    # ── X-Mailer / User-Agent ────────────────────────────────────────────────

    mailer = headers.get("x-mailer", "").lower() + headers.get("user-agent", "").lower()
    for bm in _BULK_MAILERS:
        if bm in mailer:
            score += 5
            reasons.append(f"Bulk-mailing software ({bm})")
            break

    # ── Verzendfrequentie ─────────────────────────────────────────────────────

    if sender_count >= 15:
        score += 12
        reasons.append(f"Zeer hoge verzendfrequentie ({sender_count} e-mails in inbox)")
    elif sender_count >= 7:
        score += 6
        reasons.append(f"Hoge verzendfrequentie ({sender_count} e-mails in inbox)")

    # ── Eindoordeel ───────────────────────────────────────────────────────────

    score = max(0, min(score, 100))

    if score >= 68:
        label, color, icon = "Vrijwel zeker spam", "danger", "bi-exclamation-triangle-fill"
    elif score >= 42:
        label, color, icon = "Waarschijnlijk spam", "warning", "bi-exclamation-circle-fill"
    elif score >= 18:
        label, color, icon = "Mogelijk reclame", "info", "bi-info-circle-fill"
    else:
        label, color, icon = "Legitieme nieuwsbrief", "success", "bi-check-circle-fill"

    return {
        "score": score,
        "label": label,
        "color": color,
        "icon": icon,
        "reasons": reasons,
    }
