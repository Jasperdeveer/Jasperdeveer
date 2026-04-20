import os
import time
import requests
from collections import Counter
from datetime import timedelta
from flask import (
    Flask, session, redirect, url_for, request,
    render_template, jsonify,
)
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
import msal
from spam_scorer import score_email

load_dotenv()

app = Flask(__name__)

# ── Achter Tailscale serve / reverse proxy ────────────────────────────────────
# ProxyFix zorgt dat Flask het echte protocol (HTTPS) ziet vanuit Tailscale.
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# ── Sessie-instellingen ───────────────────────────────────────────────────────
SESSION_HOURS = int(os.getenv("SESSION_HOURS", "8"))
_on_https = os.getenv("HTTPS_ONLY", "false").lower() == "true"

app.config.update(
    SECRET_KEY=os.getenv("FLASK_SECRET_KEY", os.urandom(32)),
    SESSION_COOKIE_HTTPONLY=True,          # JS kan session-cookie niet lezen
    SESSION_COOKIE_SAMESITE="Lax",         # Blokkeert cross-site requests
    SESSION_COOKIE_SECURE=_on_https,       # True achter Tailscale (HTTPS)
    PERMANENT_SESSION_LIFETIME=timedelta(hours=SESSION_HOURS),
)

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


# ── Beveiligingsheaders ───────────────────────────────────────────────────────

@app.after_request
def set_security_headers(response):
    # Voorkomt dat de browser content "raadt" (bijv. JS in een afbeelding)
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Voorkomt dat de app in een iframe geladen wordt (clickjacking)
    response.headers["X-Frame-Options"] = "DENY"
    # Stuur zo min mogelijk info mee in de Referer-header
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Schakel onnodige browser-API's uit
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    # Sta alleen resources van eigen domein toe (strict maar veilig)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
        "font-src cdn.jsdelivr.net; "
        "img-src 'self' data:; "
        "connect-src 'self';"
    )
    return response


# ── Session-timeout check ─────────────────────────────────────────────────────

@app.before_request
def enforce_session_timeout():
    """Gooi de sessie weg als die ouder is dan SESSION_HOURS."""
    open_endpoints = {"setup", "authorize", "callback", "static"}
    if request.endpoint in open_endpoints:
        return
    login_time = session.get("login_time")
    if login_time and time.time() - login_time > SESSION_HOURS * 3600:
        session.clear()
        return redirect(url_for("setup"))


# ── MSAL helpers ─────────────────────────────────────────────────────────────

def _build_msal_app(cache=None):
    return msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
        token_cache=cache,
    )


def _get_token_from_cache():
    cache = msal.SerializableTokenCache()
    if session.get("token_cache"):
        cache.deserialize(session["token_cache"])
    cca = _build_msal_app(cache=cache)
    accounts = cca.get_accounts()
    if accounts:
        result = cca.acquire_token_silent(SCOPES, account=accounts[0])
        session["token_cache"] = cache.serialize()
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


# ── E-mail ophalen & analyseren ───────────────────────────────────────────────

def _fetch_newsletter_emails():
    params = {
        "$top": 150,
        "$select": (
            "id,subject,from,receivedDateTime,"
            "bodyPreview,internetMessageHeaders"
        ),
        "$filter": "isDraft eq false",
        "$orderby": "receivedDateTime desc",
    }
    data = graph_get("/me/mailFolders/inbox/messages", params=params)
    if not data:
        return []

    all_msgs = data.get("value", [])

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
        unsubscribe = raw_headers.get("list-unsubscribe", "")
        if not unsubscribe:
            continue

        sender_addr = msg.get("from", {}).get("emailAddress", {}).get("address", "")
        sender_name = msg.get("from", {}).get("emailAddress", {}).get("name", sender_addr)

        if sender_addr.lower() in seen_senders:
            continue
        seen_senders.add(sender_addr.lower())

        mailto_link = https_link = None
        for part in unsubscribe.split(","):
            part = part.strip().strip("<>")
            if part.startswith("mailto:"):
                mailto_link = part
            elif part.startswith("http"):
                https_link = part

        one_click = "list-unsubscribe-post" in raw_headers

        spam = score_email(
            subject=msg.get("subject", ""),
            sender_email=sender_addr,
            headers=raw_headers,
            body_preview=msg.get("bodyPreview", ""),
            sender_count=sender_counts[sender_addr.lower()],
        )

        newsletters.append({
            "id":           msg["id"],
            "subject":      msg.get("subject", "(geen onderwerp)"),
            "sender_name":  sender_name,
            "sender_email": sender_addr,
            "received":     msg.get("receivedDateTime", "")[:10],
            "mailto_link":  mailto_link,
            "https_link":   https_link,
            "one_click":    one_click,
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
    email = (user or {}).get("mail") or (user or {}).get("userPrincipalName", "")

    emails = _fetch_newsletter_emails()

    stats = {
        "total":  len(emails),
        "spam":   sum(1 for e in emails if e["spam"]["score"] >= 68),
        "likely": sum(1 for e in emails if 42 <= e["spam"]["score"] < 68),
        "promo":  sum(1 for e in emails if 18 <= e["spam"]["score"] < 42),
        "legit":  sum(1 for e in emails if e["spam"]["score"] < 18),
    }

    # Hoe lang heeft de gebruiker nog voordat de sessie verloopt?
    login_time = session.get("login_time", time.time())
    seconds_left = max(0, int(SESSION_HOURS * 3600 - (time.time() - login_time)))

    return render_template(
        "index.html",
        emails=emails,
        user_email=email,
        stats=stats,
        session_seconds=seconds_left,
    )


@app.route("/setup")
def setup():
    configured = bool(CLIENT_ID and CLIENT_SECRET)
    return render_template(
        "setup.html",
        configured=configured,
        redirect_uri=REDIRECT_URI,
    )


@app.route("/authorize")
def authorize():
    if not (CLIENT_ID and CLIENT_SECRET):
        return redirect(url_for("setup"))
    cca = _build_msal_app()
    auth_url = cca.get_authorization_request_url(
        SCOPES,
        redirect_uri=REDIRECT_URI,
        state=os.urandom(16).hex(),
    )
    return redirect(auth_url)


@app.route("/callback")
def callback():
    if request.args.get("error"):
        return f"Login fout: {request.args.get('error_description')}", 400
    cache = msal.SerializableTokenCache()
    cca = _build_msal_app(cache=cache)
    result = cca.acquire_token_by_authorization_code(
        request.args["code"],
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    if "error" in result:
        return f"Token fout: {result.get('error_description')}", 400
    session.permanent = True
    session["token_cache"] = cache.serialize()
    session["login_time"] = time.time()
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        f"{AUTHORITY}/oauth2/v2.0/logout"
        f"?post_logout_redirect_uri={url_for('setup', _external=True)}"
    )


# ── API endpoints ─────────────────────────────────────────────────────────────

def _require_session():
    """Geeft 401 terug als de gebruiker niet ingelogd is."""
    if not _get_token_from_cache():
        return jsonify({"error": "Niet ingelogd"}), 401
    return None


@app.route("/api/unsubscribe-mailto", methods=["POST"])
def unsubscribe_mailto():
    err = _require_session()
    if err:
        return err

    data = request.get_json()
    mailto = data.get("mailto", "")
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
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/block-sender", methods=["POST"])
def block_sender():
    err = _require_session()
    if err:
        return err

    data = request.get_json()
    sender_email = data.get("email", "").strip().lower()
    if not sender_email:
        return jsonify({"error": "Geen e-mailadres"}), 400
    try:
        settings = graph_get("/me/mailboxSettings") or {}
        current  = settings.get("junkEmailConfiguration", {}).get("blockedSenders", [])
        if sender_email not in current:
            current.append(sender_email)
            graph_patch(
                "/me/mailboxSettings",
                {"junkEmailConfiguration": {"blockedSenders": current}},
            )
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/move-to-junk", methods=["POST"])
def move_to_junk():
    err = _require_session()
    if err:
        return err

    data = request.get_json()
    msg_id = data.get("id", "")
    if not msg_id:
        return jsonify({"error": "Geen bericht-ID"}), 400
    try:
        graph_post(f"/me/messages/{msg_id}/move", {"destinationId": "junkemail"})
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
    try:
        settings = graph_get("/me/mailboxSettings") or {}
        current  = settings.get("junkEmailConfiguration", {}).get("blockedSenders", [])
        new_addrs = [
            e["email"].strip().lower()
            for e in entries
            if e.get("email") and e["email"].strip().lower() not in current
        ]
        if new_addrs:
            graph_patch(
                "/me/mailboxSettings",
                {"junkEmailConfiguration": {"blockedSenders": current + new_addrs}},
            )
    except Exception as e:
        errors.append(f"Blokkeren mislukt: {e}")

    for entry in entries:
        msg_id = entry.get("id")
        if msg_id:
            try:
                graph_post(f"/me/messages/{msg_id}/move", {"destinationId": "junkemail"})
            except Exception as e:
                errors.append(f"Verplaatsen mislukt ({entry.get('email')}): {e}")

    if errors:
        return jsonify({"ok": False, "errors": errors}), 207
    return jsonify({"ok": True, "blocked": len(entries)})


if __name__ == "__main__":
    # Nooit debug=True in productie
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="127.0.0.1", port=5000, debug=debug)
