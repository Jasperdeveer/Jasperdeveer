import os
import re
import requests
from collections import Counter
from flask import (
    Flask, session, redirect, url_for, request,
    render_template, jsonify,
)
from dotenv import load_dotenv
import msal
from spam_scorer import score_email

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

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
    """
    Haalt berichten op die een List-Unsubscribe header bevatten,
    berekent een spamscore per afzender en sorteert op score (hoog → laag).
    """
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

    # Tel hoe vaak elke afzender voorkomt in de opgehaalde set
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

        # Uitschrijflinks extraheren
        mailto_link = https_link = None
        for part in unsubscribe.split(","):
            part = part.strip().strip("<>")
            if part.startswith("mailto:"):
                mailto_link = part
            elif part.startswith("http"):
                https_link = part

        one_click = "list-unsubscribe-post" in raw_headers

        body_preview = msg.get("bodyPreview", "")

        spam = score_email(
            subject=msg.get("subject", ""),
            sender_email=sender_addr,
            headers=raw_headers,
            body_preview=body_preview,
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

    # Sorteer: hoogste spamscore bovenaan
    newsletters.sort(key=lambda e: e["spam"]["score"], reverse=True)
    return newsletters


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if not _get_token_from_cache():
        return redirect(url_for("setup"))

    user = graph_get("/me", params={"$select": "displayName,mail,userPrincipalName"})
    display_name = (user or {}).get("displayName", "")
    email = (user or {}).get("mail") or (user or {}).get("userPrincipalName", "")

    emails = _fetch_newsletter_emails()

    stats = {
        "total":    len(emails),
        "spam":     sum(1 for e in emails if e["spam"]["score"] >= 68),
        "likely":   sum(1 for e in emails if 42 <= e["spam"]["score"] < 68),
        "promo":    sum(1 for e in emails if 18 <= e["spam"]["score"] < 42),
        "legit":    sum(1 for e in emails if e["spam"]["score"] < 18),
    }

    return render_template(
        "index.html",
        emails=emails,
        display_name=display_name,
        user_email=email,
        stats=stats,
    )


@app.route("/setup")
def setup():
    configured = bool(CLIENT_ID and CLIENT_SECRET)
    return render_template("setup.html", configured=configured, redirect_uri=REDIRECT_URI)


@app.route("/login")
def login():
    return redirect(url_for("authorize"))


@app.route("/authorize")
def authorize():
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
    session["token_cache"] = cache.serialize()
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    logout_url = (
        f"{AUTHORITY}/oauth2/v2.0/logout"
        f"?post_logout_redirect_uri={url_for('setup', _external=True)}"
    )
    return redirect(logout_url)


# ── API endpoints ─────────────────────────────────────────────────────────────

@app.route("/api/unsubscribe-mailto", methods=["POST"])
def unsubscribe_mailto():
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
    data = request.get_json()
    sender_email = data.get("email", "").strip().lower()
    if not sender_email:
        return jsonify({"error": "Geen e-mailadres opgegeven"}), 400
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
    """
    Blokkeert alle opgegeven afzenders in één keer en verplaatst
    hun meest recente bericht naar Ongewenste e-mail.
    """
    data    = request.get_json()
    entries = data.get("entries", [])   # [{email, id}, ...]
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
                errors.append(f"Verplaatsen mislukt voor {entry.get('email')}: {e}")

    if errors:
        return jsonify({"ok": False, "errors": errors}), 207
    return jsonify({"ok": True, "blocked": len(entries)})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
