import os
import json
import requests
from flask import Flask, session, redirect, url_for, request, render_template, jsonify, flash
from dotenv import load_dotenv
import msal

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
TENANT_ID = os.getenv("AZURE_TENANT_ID", "common")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:5000/callback")

SCOPES = ["Mail.ReadWrite", "MailboxSettings.ReadWrite", "User.Read", "Mail.Send"]

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


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


def _get_headers():
    token = _get_token_from_cache()
    if not token or "access_token" not in token:
        return None
    return {"Authorization": f"Bearer {token['access_token']}", "Content-Type": "application/json"}


def graph_get(path, params=None):
    headers = _get_headers()
    if not headers:
        return None
    r = requests.get(f"{GRAPH_BASE}{path}", headers=headers, params=params)
    r.raise_for_status()
    return r.json()


def graph_patch(path, body):
    headers = _get_headers()
    if not headers:
        return None
    r = requests.patch(f"{GRAPH_BASE}{path}", headers=headers, json=body)
    r.raise_for_status()
    return r


def graph_post(path, body):
    headers = _get_headers()
    if not headers:
        return None
    r = requests.post(f"{GRAPH_BASE}{path}", headers=headers, json=body)
    r.raise_for_status()
    return r.json()


@app.route("/")
def index():
    token = _get_token_from_cache()
    if not token:
        return redirect(url_for("login"))

    user = graph_get("/me", params={"$select": "displayName,mail,userPrincipalName"})
    display_name = user.get("displayName", "") if user else ""
    email = user.get("mail") or user.get("userPrincipalName", "") if user else ""

    emails = _fetch_newsletter_emails()
    return render_template("index.html", emails=emails, display_name=display_name, user_email=email)


def _fetch_newsletter_emails():
    """Fetch emails that have a List-Unsubscribe header (newsletters/marketing)."""
    params = {
        "$top": 100,
        "$select": "id,subject,from,receivedDateTime,internetMessageHeaders",
        "$filter": "isDraft eq false",
        "$orderby": "receivedDateTime desc",
    }
    data = graph_get("/me/mailFolders/inbox/messages", params=params)
    if not data:
        return []

    newsletters = []
    seen_senders = set()

    for msg in data.get("value", []):
        headers = {h["name"].lower(): h["value"] for h in msg.get("internetMessageHeaders", [])}
        unsubscribe = headers.get("list-unsubscribe", "")
        if not unsubscribe:
            continue

        sender_email = msg.get("from", {}).get("emailAddress", {}).get("address", "")
        sender_name = msg.get("from", {}).get("emailAddress", {}).get("name", sender_email)

        if sender_email in seen_senders:
            continue
        seen_senders.add(sender_email)

        mailto_link = None
        https_link = None
        for part in unsubscribe.split(","):
            part = part.strip().strip("<>")
            if part.startswith("mailto:"):
                mailto_link = part
            elif part.startswith("http"):
                https_link = part

        one_click = "list-unsubscribe-post" in headers

        newsletters.append({
            "id": msg["id"],
            "subject": msg.get("subject", "(geen onderwerp)"),
            "sender_name": sender_name,
            "sender_email": sender_email,
            "received": msg.get("receivedDateTime", "")[:10],
            "mailto_link": mailto_link,
            "https_link": https_link,
            "one_click": one_click,
        })

    return newsletters


@app.route("/login")
def login():
    return render_template("login.html")


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
    return redirect(
        f"{AUTHORITY}/oauth2/v2.0/logout?post_logout_redirect_uri={url_for('login', _external=True)}"
    )


@app.route("/api/unsubscribe-mailto", methods=["POST"])
def unsubscribe_mailto():
    """Send an unsubscribe email via Microsoft Graph."""
    data = request.get_json()
    mailto = data.get("mailto", "")
    if not mailto.startswith("mailto:"):
        return jsonify({"error": "Ongeldig mailto adres"}), 400

    # Parse mailto: address and optional subject/body
    rest = mailto[7:]
    to_addr = rest.split("?")[0]
    subject = "Unsubscribe"
    body = "Please unsubscribe me from this mailing list."

    if "?" in rest:
        from urllib.parse import parse_qs
        qs = parse_qs(rest.split("?", 1)[1])
        subject = qs.get("subject", [subject])[0]
        body = qs.get("body", [body])[0]

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
    """Add sender to blocked senders list via mailbox settings."""
    data = request.get_json()
    sender_email = data.get("email", "").strip().lower()
    if not sender_email:
        return jsonify({"error": "Geen e-mailadres opgegeven"}), 400

    try:
        # Get current blocked senders
        settings = graph_get("/me/mailboxSettings")
        current_blocked = (
            settings.get("junkEmailConfiguration", {}).get("blockedSenders", [])
            if settings
            else []
        )

        if sender_email not in current_blocked:
            current_blocked.append(sender_email)
            graph_patch(
                "/me/mailboxSettings",
                {"junkEmailConfiguration": {"blockedSenders": current_blocked}},
            )

        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/move-to-junk", methods=["POST"])
def move_to_junk():
    """Move an email to the Junk folder."""
    data = request.get_json()
    msg_id = data.get("id", "")
    if not msg_id:
        return jsonify({"error": "Geen bericht ID"}), 400

    try:
        graph_post(f"/me/messages/{msg_id}/move", {"destinationId": "junkemail"})
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
