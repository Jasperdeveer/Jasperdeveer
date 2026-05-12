import os
import time
import uuid
import requests
from collections import Counter
from datetime import timedelta
from pathlib import Path
from flask import (
    Flask, session, redirect, url_for, request,
    render_template, jsonify,
)
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
import msal

import database
import spamhaus as spamhaus_check
from spam_scorer import score_email

load_dotenv()
database.init_db()

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

SESSION_HOURS = int(os.getenv("SESSION_HOURS", "8"))
_on_https = os.getenv("HTTPS_ONLY", "false").lower() == "true"

app.config.update(
    SECRET_KEY=os.getenv("FLASK_SECRET_KEY", os.urandom(32)),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=_on_https,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=SESSION_HOURS),
)

# ── Server-side token opslag ──────────────────────────────────────────────────
# De Microsoft-toegangstoken wordt NIET in de cookie opgeslagen.
# De cookie bevat alleen een willekeurige sessie-ID.
# De token staat in een bestand op de server, bereikbaar via die ID.

SESSION_DIR = Path(os.getenv("SESSION_DIR", "sessions"))
SESSION_DIR.mkdir(mode=0o700, exist_ok=True)


def _sid() -> str:
    """Geeft de sessie-ID terug; maakt er een aan als die er nog niet is."""
    if "sid" not in session:
        session["sid"] = uuid.uuid4().hex
    return session["sid"]


def _cache_path(sid: str) -> Path:
    # Alleen hexadecimale tekens toestaan (voorkomt path traversal)
    safe = "".join(c for c in sid if c in "0123456789abcdef")
    return SESSION_DIR / f"{safe}.cache"


def _load_cache(sid: str) -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    path = _cache_path(sid)
    if path.exists():
        cache.deserialize(path.read_text(encoding="utf-8"))
    return cache


def _save_cache(sid: str, cache: msal.SerializableTokenCache) -> None:
    if cache.has_state_changed:
        path = _cache_path(sid)
        path.write_text(cache.serialize(), encoding="utf-8")
        path.chmod(0o600)  # alleen eigenaar mag lezen/schrijven


def _delete_cache(sid: str) -> None:
    path = _cache_path(sid)
    if path.exists():
        path.unlink(missing_ok=True)

CLIENT_ID     = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
TENANT_ID     = os.getenv("AZURE_TENANT_ID", "common")
AUTHORITY     = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_URI  = os.getenv("REDIRECT_URI", "http://localhost:5000/callback")

SCOPES = [
    "Mail.ReadWrite",
    "MailboxSettings.ReadWrite",
    "User.Read",
    "Mail.Send",
]

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# Mappen om te scannen
SCAN_FOLDERS = ["inbox", "junkemail"]


# ── Beveiligingsheaders ───────────────────────────────────────────────────────

@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
        "font-src cdn.jsdelivr.net; "
        "img-src 'self' data:; "
        "connect-src 'self';"
    )
    return response


# ── Session-timeout ───────────────────────────────────────────────────────────

@app.before_request
def enforce_session_timeout():
    open_endpoints = {"setup", "authorize", "callback", "static"}
    if request.endpoint in open_endpoints:
        return
    login_time = session.get("login_time")
    if login_time and time.time() - login_time > SESSION_HOURS * 3600:
        _delete_cache(_sid())
        session.clear()
        return redirect(url_for("setup"))


def _cleanup_old_sessions() -> None:
    """Verwijder sessiebestanden die ouder zijn dan SESSION_HOURS."""
    cutoff = time.time() - SESSION_HOURS * 3600
    for path in SESSION_DIR.glob("*.cache"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
        except OSError:
            pass


# ── MSAL helpers ──────────────────────────────────────────────────────────────

def _build_msal_app(cache=None):
    return msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
        token_cache=cache,
    )


def _get_token_from_cache():
    sid   = _sid()
    cache = _load_cache(sid)
    cca   = _build_msal_app(cache=cache)
    accounts = cca.get_accounts()
    if accounts:
        result = cca.acquire_token_silent(SCOPES, account=accounts[0])
        _save_cache(sid, cache)
        return result
    return None


def _auth_headers():
    token = _get_token_from_cache()
    if not token or "access_token" not in token:
        return None
    return {
        "Authorization": f"Bearer {token['access_token']}",
        "Content-Type": "application/json",
    }


# ── Graph helpers ─────────────────────────────────────────────────────────────

def graph_get(path, params=None):
    hdrs = _auth_headers()
    if not hdrs:
        return None
    r = requests.get(f"{GRAPH_BASE}{path}", headers=hdrs, params=params)
    r.raise_for_status()
    return r.json()


def graph_patch(path, body):
    hdrs = _auth_headers()
    if not hdrs:
        return None
    r = requests.patch(f"{GRAPH_BASE}{path}", headers=hdrs, json=body)
    r.raise_for_status()
    return r


def graph_post(path, body):
    hdrs = _auth_headers()
    if not hdrs:
        return None
    r = requests.post(f"{GRAPH_BASE}{path}", headers=hdrs, json=body)
    r.raise_for_status()
    return r.json()


# ── E-mail ophalen ─────────────────────────────────────────────────────────────

def _fetch_from_folder(folder_id: str, max_messages: int = 500) -> list:
    """Haalt berichten op met paginering totdat max_messages bereikt is."""
    params = {
        "$top": min(max_messages, 999),
        "$select": "id,subject,from,receivedDateTime,bodyPreview,internetMessageHeaders",
        "$filter": "isDraft eq false",
        "$orderby": "receivedDateTime desc",
    }
    messages = []
    url = f"{GRAPH_BASE}/me/mailFolders/{folder_id}/messages"
    hdrs = _auth_headers()
    if not hdrs:
        return []

    while url and len(messages) < max_messages:
        r = requests.get(url, headers=hdrs, params=params)
        if not r.ok:
            break
        data = r.json()
        messages.extend(data.get("value", []))
        # Volgende pagina (params alleen bij eerste aanroep meegeven)
        url = data.get("@odata.nextLink")
        params = None

    return messages[:max_messages]


def _get_microsoft_blocked_emails() -> set:
    """Leest geblokkeerde afzenders/domeinen uit Microsoft inbox rules."""
    try:
        rules = graph_get("/me/mailFolders/inbox/messageRules") or {}
        result = set()
        for rule in rules.get("value", []):
            name = rule.get("displayName", "").lower()
            if not name.startswith("blokkeer "):
                continue
            for val in rule.get("conditions", {}).get("senderContains", []):
                result.add(val.strip().lower())
        return result
    except Exception:
        return set()


def _is_blocked(sender_lower: str, blocked_set: set) -> bool:
    """Controleert of een afzender of zijn domein geblokkeerd is."""
    if sender_lower in blocked_set:
        return True
    domain = sender_lower.split("@")[-1] if "@" in sender_lower else ""
    return f"@{domain}" in blocked_set


def _fetch_newsletter_emails() -> list:
    # Haal berichten op uit alle geconfigureerde mappen
    all_msgs: list = []
    for folder in SCAN_FOLDERS:
        try:
            all_msgs.extend(_fetch_from_folder(folder))
        except Exception:
            pass  # Map bestaat niet of toegang geweigerd — overslaan

    # Combineer lokale database met Microsoft inbox rules (persistent na herstart)
    blocked_set     = database.get_blocked_emails() | _get_microsoft_blocked_emails()
    whitelisted_set = database.get_whitelisted_emails()
    snoozed_set     = database.get_snoozed_emails()

    sender_counts: Counter = Counter(
        msg.get("from", {}).get("emailAddress", {}).get("address", "").lower()
        for msg in all_msgs
    )

    seen_senders: set = set()
    newsletters: list = []

    for msg in all_msgs:
        raw_headers = {
            h["name"].lower(): h["value"]
            for h in msg.get("internetMessageHeaders", [])
        }
        if not raw_headers.get("list-unsubscribe"):
            continue

        sender_addr = msg.get("from", {}).get("emailAddress", {}).get("address", "")
        sender_name = msg.get("from", {}).get("emailAddress", {}).get("name", sender_addr)
        sender_lower = sender_addr.lower()

        if sender_lower in seen_senders or sender_lower in whitelisted_set \
                or _is_blocked(sender_lower, blocked_set) or sender_lower in snoozed_set:
            continue
        seen_senders.add(sender_lower)

        unsubscribe = raw_headers["list-unsubscribe"]
        mailto_link = https_link = None
        for part in unsubscribe.split(","):
            part = part.strip().strip("<>")
            if part.startswith("mailto:"):
                mailto_link = part
            elif part.startswith("http"):
                https_link = part

        domain = sender_lower.split("@")[-1] if "@" in sender_lower else ""
        sh_listed = spamhaus_check.is_listed(domain)
        feedback  = database.get_feedback(sender_lower)

        spam = score_email(
            subject=msg.get("subject", ""),
            sender_email=sender_addr,
            headers=raw_headers,
            body_preview=msg.get("bodyPreview", ""),
            sender_count=sender_counts[sender_lower],
            spamhaus_listed=sh_listed,
            user_feedback=feedback,
        )

        newsletters.append({
            "id":           msg["id"],
            "subject":      msg.get("subject", "(geen onderwerp)"),
            "sender_name":  sender_name,
            "sender_email": sender_addr,
            "received":     msg.get("receivedDateTime", "")[:10],
            "body_preview": msg.get("bodyPreview", ""),
            "mailto_link":  mailto_link,
            "https_link":   https_link,
            "one_click":    "list-unsubscribe-post" in raw_headers,
            "already_blocked": sender_lower in blocked_set,
            "spam":         spam,
        })

    newsletters.sort(key=lambda e: e["spam"]["score"], reverse=True)
    return newsletters


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if not _get_token_from_cache():
        return redirect(url_for("setup"))
    user = graph_get("/me", params={"$select": "displayName,mail,userPrincipalName"})
    user_email = (user or {}).get("mail") or (user or {}).get("userPrincipalName", "")
    db_stats     = database.get_stats()
    login_time   = session.get("login_time", time.time())
    seconds_left = max(0, int(SESSION_HOURS * 3600 - (time.time() - login_time)))
    return render_template(
        "index.html",
        user_email=user_email,
        db_stats=db_stats,
        session_seconds=seconds_left,
    )


@app.route("/api/emails")
def api_emails():
    err = _require_session()
    if err:
        return err
    emails = _fetch_newsletter_emails()
    stats  = {
        "total":  len(emails),
        "spam":   sum(1 for e in emails if e["spam"]["score"] >= 68),
        "likely": sum(1 for e in emails if 42 <= e["spam"]["score"] < 68),
        "promo":  sum(1 for e in emails if 18 <= e["spam"]["score"] < 42),
        "legit":  sum(1 for e in emails if e["spam"]["score"] < 18),
    }
    html = render_template("partials/cards.html", emails=emails)
    return jsonify({"html": html, "stats": stats})


@app.route("/setup")
def setup():
    configured = bool(CLIENT_ID and CLIENT_SECRET)
    return render_template("setup.html", configured=configured, redirect_uri=REDIRECT_URI)


@app.route("/authorize")
def authorize():
    if not (CLIENT_ID and CLIENT_SECRET):
        return redirect(url_for("setup"))
    cca = _build_msal_app()
    auth_url = cca.get_authorization_request_url(
        SCOPES, redirect_uri=REDIRECT_URI, state=os.urandom(16).hex()
    )
    return redirect(auth_url)


@app.route("/callback")
def callback():
    if request.args.get("error"):
        return f"Login fout: {request.args.get('error_description')}", 400

    cache = msal.SerializableTokenCache()
    cca   = _build_msal_app(cache=cache)
    result = cca.acquire_token_by_authorization_code(
        request.args["code"], scopes=SCOPES, redirect_uri=REDIRECT_URI
    )
    if "error" in result:
        return f"Token fout: {result.get('error_description')}", 400

    # Nieuwe sessie-ID na elke login (voorkomt session fixation)
    session.clear()
    session.permanent    = True
    session["sid"]       = uuid.uuid4().hex
    session["login_time"] = time.time()

    # Token opslaan op server — NIET in de cookie
    _save_cache(session["sid"], cache)

    # Ruim verlopen sessies op (stil, op de achtergrond)
    try:
        _cleanup_old_sessions()
    except Exception:
        pass

    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    _delete_cache(_sid())   # token van schijf verwijderen
    session.clear()
    return redirect(
        f"{AUTHORITY}/oauth2/v2.0/logout"
        f"?post_logout_redirect_uri={url_for('setup', _external=True)}"
    )


# ── API helpers ────────────────────────────────────────────────────────────────

def _require_session():
    if not _get_token_from_cache():
        return jsonify({"error": "Niet ingelogd"}), 401
    return None


# ── Uitschrijven via e-mail ───────────────────────────────────────────────────

@app.route("/api/unsubscribe-mailto", methods=["POST"])
def unsubscribe_mailto():
    err = _require_session()
    if err:
        return err
    data    = request.get_json()
    mailto  = data.get("mailto", "")
    sender  = data.get("sender_email", "")
    name    = data.get("sender_name", "")
    if not mailto.startswith("mailto:"):
        return jsonify({"error": "Ongeldig mailto-adres"}), 400

    rest    = mailto[7:]
    to_addr = rest.split("?")[0]
    subject = "Unsubscribe"
    body    = "Please unsubscribe me from this mailing list."
    if "?" in rest:
        from urllib.parse import parse_qs
        qs      = parse_qs(rest.split("?", 1)[1])
        subject = qs.get("subject", [subject])[0]
        body    = qs.get("body",    [body])[0]

    message = {
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": body},
            "toRecipients": [{"emailAddress": {"address": to_addr}}],
        },
        "saveToSentItems": False,
    }
    try:
        graph_post("/me/sendMail", message)
        if sender:
            database.add_unsubscribed(sender, name)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Blokkeren ─────────────────────────────────────────────────────────────────

@app.route("/api/block-sender", methods=["POST"])
def block_sender():
    err = _require_session()
    if err:
        return err
    data  = request.get_json()
    email = data.get("email", "").strip().lower()
    name  = data.get("name", "")
    if not email:
        return jsonify({"error": "Geen e-mailadres"}), 400
    try:
        # Maak een inboxregel die toekomstige mails automatisch naar Ongewenste mail stuurt.
        # Dit werkt voor persoonlijke @live.nl accounts (mailboxSettings.blockedSenders niet).
        graph_post("/me/mailFolders/inbox/messageRules", {
            "displayName": f"Blokkeer {email}",
            "sequence": 1,
            "isEnabled": True,
            "conditions": {"senderContains": [email]},
            "actions": {"moveToFolder": "junkemail", "stopProcessingRules": True},
        })
        database.add_blocked(email, name)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/block-domain", methods=["POST"])
def block_domain():
    err = _require_session()
    if err:
        return err
    data   = request.get_json()
    domain = data.get("domain", "").strip().lower().lstrip("@")
    name   = data.get("name", "")
    if not domain or "." not in domain:
        return jsonify({"error": "Ongeldig domein"}), 400
    try:
        graph_post("/me/mailFolders/inbox/messageRules", {
            "displayName": f"Blokkeer domein @{domain}",
            "sequence":    1,
            "isEnabled":   True,
            "conditions":  {"senderContains": [f"@{domain}"]},
            "actions":     {"moveToFolder": "junkemail", "stopProcessingRules": True},
        })
        database.add_blocked(f"@{domain}", name)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/block-keyword", methods=["POST"])
def block_keyword():
    err = _require_session()
    if err:
        return err
    data    = request.get_json()
    keyword = data.get("keyword", "").strip()
    if not keyword or len(keyword) < 2:
        return jsonify({"error": "Zoekwoord te kort"}), 400
    try:
        graph_post("/me/mailFolders/inbox/messageRules", {
            "displayName": f"Blokkeer naam '{keyword}'",
            "sequence":    1,
            "isEnabled":   True,
            "conditions":  {"senderContains": [keyword]},
            "actions":     {"moveToFolder": "junkemail", "stopProcessingRules": True},
        })
        database.add_blocked(f"~naam:{keyword.lower()}", keyword)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/move-to-junk", methods=["POST"])
def move_to_junk():
    err = _require_session()
    if err:
        return err
    data   = request.get_json()
    msg_id = data.get("id", "")
    if not msg_id:
        return jsonify({"error": "Geen bericht-ID"}), 400
    try:
        graph_post(f"/me/messages/{msg_id}/move", {"destinationId": "deleteditems"})
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/bulk-block", methods=["POST"])
def bulk_block():
    err = _require_session()
    if err:
        return err
    data    = request.get_json()
    entries = data.get("entries", [])
    if not entries:
        return jsonify({"error": "Geen afzenders opgegeven"}), 400

    errors = []
    for entry in entries:
        email = entry.get("email", "").strip().lower()
        name  = entry.get("name", "")
        if not email:
            continue
        try:
            graph_post("/me/mailFolders/inbox/messageRules", {
                "displayName": f"Blokkeer {email}",
                "sequence": 1,
                "isEnabled": True,
                "conditions": {"senderContains": [email]},
                "actions": {"moveToFolder": "junkemail", "stopProcessingRules": True},
            })
            database.add_blocked(email, name)
        except Exception as e:
            errors.append(f"Regel aanmaken mislukt voor {email}: {e}")

    for entry in entries:
        msg_id = entry.get("id")
        if msg_id:
            try:
                graph_post(f"/me/messages/{msg_id}/move", {"destinationId": "deleteditems"})
            except Exception as e:
                errors.append(str(e))

    if errors:
        return jsonify({"ok": False, "errors": errors}), 207
    return jsonify({"ok": True, "blocked": len(entries)})


# ── Ongedaan maken ────────────────────────────────────────────────────────────

@app.route("/api/undo-block", methods=["POST"])
def undo_block():
    err = _require_session()
    if err:
        return err
    data  = request.get_json()
    email = data.get("email", "").strip().lower()
    msg_id = data.get("msg_id", "")
    if not email:
        return jsonify({"error": "Geen e-mailadres"}), 400
    try:
        # Verwijder de inboxregel voor deze afzender
        rules = graph_get("/me/mailFolders/inbox/messageRules") or {}
        for rule in rules.get("value", []):
            if email in rule.get("displayName", "").lower():
                try:
                    hdrs = _auth_headers()
                    requests.delete(
                        f"{GRAPH_BASE}/me/mailFolders/inbox/messageRules/{rule['id']}",
                        headers=hdrs,
                    )
                except Exception:
                    pass
        # Verplaats e-mail terug naar inbox
        if msg_id:
            try:
                graph_post(f"/me/messages/{msg_id}/move", {"destinationId": "inbox"})
            except Exception:
                pass
        # Verwijder uit lokale database
        database.remove_blocked(email)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Whitelist ─────────────────────────────────────────────────────────────────

@app.route("/api/whitelist-sender", methods=["POST"])
def whitelist_sender():
    err = _require_session()
    if err:
        return err
    data  = request.get_json()
    email = data.get("email", "").strip().lower()
    name  = data.get("name", "")
    if not email:
        return jsonify({"error": "Geen e-mailadres"}), 400
    try:
        database.add_whitelisted(email, name)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Snoozen ───────────────────────────────────────────────────────────────────

@app.route("/api/snooze-sender", methods=["POST"])
def snooze_sender():
    err = _require_session()
    if err:
        return err
    data  = request.get_json()
    email = data.get("email", "").strip().lower()
    name  = data.get("name", "")
    days  = int(data.get("days", 30))
    if not email:
        return jsonify({"error": "Geen e-mailadres"}), 400
    try:
        database.snooze_sender(email, name, days)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="127.0.0.1", port=5000, debug=debug)
