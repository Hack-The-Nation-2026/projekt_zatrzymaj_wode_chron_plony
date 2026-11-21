"""Konta użytkowników i historia raportów (SQLite, bez dodatkowych zależności).

- Hasła: PBKDF2-HMAC-SHA256 (200 000 iteracji) z losową solą; w bazie nie ma haseł jawnym tekstem.
- Sesje: losowy token (Bearer) ważny 30 dni; w bazie trzymamy tylko jego skrót SHA-256.
- Historia: pełny raport (JSON) zapisany przy koncie, więc przetrwa restart serwera.

Plik bazy: zmienna WODNIK_DB (domyślnie data/wodnik.db).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional

DB_PATH = Path(os.environ.get("WODNIK_DB", Path(__file__).resolve().parent.parent / "data" / "wodnik.db"))
SESSION_DAYS = 30
PBKDF2_ITER = 200_000
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 8

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    name TEXT,
    pw_salt BLOB NOT NULL,
    pw_hash BLOB NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    analysis_id TEXT NOT NULL,
    parcel_id TEXT,
    place TEXT,
    date TEXT,
    crop TEXT,
    risk_level TEXT,
    created_at REAL NOT NULL,
    report_json TEXT NOT NULL,
    UNIQUE (user_id, analysis_id)
);
CREATE INDEX IF NOT EXISTS reports_user ON reports(user_id, created_at DESC);
"""


class AccountError(ValueError):
    """Błąd po stronie użytkownika (zły e-mail, zajęty adres, złe hasło...)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init() -> None:
    with _lock, _connect() as con:
        con.executescript(SCHEMA)


def _hash_pw(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITER)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _user_json(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "email": row["email"], "name": row["name"],
            "created_at": _iso(row["created_at"])}


def _iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


# --- konto ---------------------------------------------------------------------

def register(email: str, password: str, name: Optional[str] = None) -> dict:
    email = (email or "").strip().lower()
    if not EMAIL_RE.match(email) or len(email) > 254:
        raise AccountError("INVALID_INPUT", "Podaj poprawny adres e-mail.")
    if len(password or "") < MIN_PASSWORD:
        raise AccountError("INVALID_INPUT", f"Hasło musi mieć co najmniej {MIN_PASSWORD} znaków.")
    name = (name or "").strip()[:80] or None
    salt = secrets.token_bytes(16)
    try:
        with _lock, _connect() as con:
            cur = con.execute("INSERT INTO users (email, name, pw_salt, pw_hash, created_at) VALUES (?,?,?,?,?)",
                              (email, name, salt, _hash_pw(password, salt), time.time()))
            row = con.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    except sqlite3.IntegrityError:
        raise AccountError("EMAIL_TAKEN", "Konto z tym adresem e-mail już istnieje.") from None
    return _user_json(row)


def login(email: str, password: str) -> tuple[str, dict]:
    """Zwraca (token, użytkownik). Ten sam komunikat dla złego e-maila i złego hasła."""
    email = (email or "").strip().lower()
    with _connect() as con:
        row = con.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if row is None:
        _hash_pw(password or "", b"0" * 16)  # podobny czas odpowiedzi, gdy konta nie ma
        raise AccountError("BAD_CREDENTIALS", "Nieprawidłowy e-mail lub hasło.")
    if not hmac.compare_digest(_hash_pw(password or "", row["pw_salt"]), row["pw_hash"]):
        raise AccountError("BAD_CREDENTIALS", "Nieprawidłowy e-mail lub hasło.")
    token = secrets.token_urlsafe(32)
    now = time.time()
    with _lock, _connect() as con:
        con.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
        con.execute("INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?,?,?)",
                    (_token_hash(token), row["id"], now + SESSION_DAYS * 86400))
    return token, _user_json(row)


def logout(token: str) -> None:
    with _lock, _connect() as con:
        con.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))


def user_for_token(token: Optional[str]) -> Optional[dict]:
    if not token:
        return None
    with _connect() as con:
        row = con.execute("SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id "
                          "WHERE s.token_hash = ? AND s.expires_at > ?",
                          (_token_hash(token), time.time())).fetchone()
    return _user_json(row) if row else None


# --- historia raportów ------------------------------------------------------------

def save_report(user_id: int, analysis_id: str, report: dict) -> int:
    """Zapisuje raport w historii użytkownika (ta sama analiza tylko raz). Zwraca id wpisu."""
    p = report.get("parcel") or {}
    place = ", ".join(x for x in (p.get("obreb"), p.get("gmina") and f"gm. {p['gmina']}") if x) or None
    with _lock, _connect() as con:
        con.execute(
            "INSERT OR IGNORE INTO reports (user_id, analysis_id, parcel_id, place, date, crop, risk_level, "
            "created_at, report_json) VALUES (?,?,?,?,?,?,?,?,?)",
            (user_id, analysis_id, p.get("id"), place, report.get("date"), report.get("crop"),
             report.get("risk_level"), time.time(), json.dumps(report, ensure_ascii=False)))
        row = con.execute("SELECT id FROM reports WHERE user_id = ? AND analysis_id = ?",
                          (user_id, analysis_id)).fetchone()
    return row["id"]


def _summary(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "analysis_id": row["analysis_id"], "parcel_id": row["parcel_id"],
            "place": row["place"], "date": row["date"], "crop": row["crop"],
            "risk_level": row["risk_level"], "saved_at": _iso(row["created_at"])}


def list_reports(user_id: int, limit: int = 100) -> list[dict]:
    with _connect() as con:
        rows = con.execute("SELECT * FROM reports WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
                           (user_id, limit)).fetchall()
    return [_summary(r) for r in rows]


def get_report(user_id: int, report_id: int) -> Optional[dict]:
    with _connect() as con:
        row = con.execute("SELECT * FROM reports WHERE user_id = ? AND id = ?", (user_id, report_id)).fetchone()
    if not row:
        return None
    return {**_summary(row), "report": json.loads(row["report_json"])}


def delete_report(user_id: int, report_id: int) -> bool:
    with _lock, _connect() as con:
        cur = con.execute("DELETE FROM reports WHERE user_id = ? AND id = ?", (user_id, report_id))
    return cur.rowcount > 0
