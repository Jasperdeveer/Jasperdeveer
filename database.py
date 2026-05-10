"""
Lokale SQLite-opslag voor de Spam Uitschrijver.
Slaat op: geblokkeerde afzenders, whitelist, gebruikersfeedback en actiegeschiedenis.
"""

import os
import sqlite3
from datetime import datetime, timezone, timedelta

DB_PATH = os.getenv("DATABASE_PATH", "spam_memory.db")


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS blocked_senders (
                email      TEXT PRIMARY KEY,
                name       TEXT,
                blocked_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS whitelisted_senders (
                email          TEXT PRIMARY KEY,
                name           TEXT,
                whitelisted_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS spam_feedback (
                email      TEXT PRIMARY KEY,
                is_spam    INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS actions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                email        TEXT NOT NULL,
                name         TEXT,
                action       TEXT NOT NULL,
                performed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS snoozed_senders (
                email        TEXT PRIMARY KEY,
                name         TEXT,
                snooze_until TEXT NOT NULL
            );
        """)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Geblokkeerde afzenders ────────────────────────────────────────────────────

def add_blocked(email: str, name: str = "") -> None:
    email = email.lower().strip()
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO blocked_senders (email, name, blocked_at) VALUES (?,?,?)",
            (email, name, _now()),
        )
        c.execute(
            "INSERT OR REPLACE INTO spam_feedback (email, is_spam, updated_at) VALUES (?,1,?)",
            (email, _now()),
        )
        c.execute(
            "INSERT INTO actions (email, name, action, performed_at) VALUES (?,?,'blocked',?)",
            (email, name, _now()),
        )


def remove_blocked(email: str) -> None:
    with _conn() as c:
        c.execute("DELETE FROM blocked_senders WHERE email=?", (email.lower().strip(),))


def get_blocked_emails() -> set:
    with _conn() as c:
        return {r["email"] for r in c.execute("SELECT email FROM blocked_senders")}


# ── Whitelist ─────────────────────────────────────────────────────────────────

def add_whitelisted(email: str, name: str = "") -> None:
    email = email.lower().strip()
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO whitelisted_senders (email, name, whitelisted_at) VALUES (?,?,?)",
            (email, name, _now()),
        )
        c.execute(
            "INSERT OR REPLACE INTO spam_feedback (email, is_spam, updated_at) VALUES (?,0,?)",
            (email, _now()),
        )
        c.execute(
            "INSERT INTO actions (email, name, action, performed_at) VALUES (?,?,'whitelisted',?)",
            (email, name, _now()),
        )


def remove_whitelisted(email: str) -> None:
    with _conn() as c:
        c.execute("DELETE FROM whitelisted_senders WHERE email=?", (email.lower().strip(),))


def get_whitelisted_emails() -> set:
    with _conn() as c:
        return {r["email"] for r in c.execute("SELECT email FROM whitelisted_senders")}


# ── Gebruikersfeedback ────────────────────────────────────────────────────────

def get_feedback(email: str) -> int | None:
    """Geeft 1 (spam), 0 (vertrouwd) of None (onbekend)."""
    with _conn() as c:
        row = c.execute(
            "SELECT is_spam FROM spam_feedback WHERE email=?", (email.lower().strip(),)
        ).fetchone()
    return row["is_spam"] if row else None


def snooze_sender(email: str, name: str = "", days: int = 30) -> None:
    email = email.lower().strip()
    snooze_until = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO snoozed_senders (email, name, snooze_until) VALUES (?,?,?)",
            (email, name, snooze_until),
        )


def get_snoozed_emails() -> set:
    with _conn() as c:
        return {
            r["email"] for r in c.execute(
                "SELECT email FROM snoozed_senders WHERE snooze_until > datetime('now')"
            )
        }


def add_unsubscribed(email: str, name: str = "") -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO actions (email, name, action, performed_at) VALUES (?,?,'unsubscribed',?)",
            (email.lower().strip(), name, _now()),
        )


# ── Statistieken ──────────────────────────────────────────────────────────────

def get_stats() -> dict:
    with _conn() as c:
        total_blocked     = c.execute("SELECT COUNT(*) FROM blocked_senders").fetchone()[0]
        total_whitelisted = c.execute("SELECT COUNT(*) FROM whitelisted_senders").fetchone()[0]
        month_blocked = c.execute(
            "SELECT COUNT(*) FROM actions WHERE action='blocked' "
            "AND performed_at >= datetime('now','-30 days')"
        ).fetchone()[0]
        month_unsubscribed = c.execute(
            "SELECT COUNT(*) FROM actions WHERE action='unsubscribed' "
            "AND performed_at >= datetime('now','-30 days')"
        ).fetchone()[0]
    return {
        "total_blocked":     total_blocked,
        "total_whitelisted": total_whitelisted,
        "month_blocked":     month_blocked,
        "month_unsubscribed": month_unsubscribed,
    }
