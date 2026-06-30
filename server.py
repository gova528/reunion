#!/usr/bin/env python3
"""
====================================================================
 GRAND REUNION TOUR (GRT 2006-2007) -- BACKEND SERVER
====================================================================
Pure Python standard library backend (no Flask/Django/Node).
Uses http.server for routing and sqlite3 as the runtime database
engine so the project runs immediately with zero external services.

For production, point this at MySQL using the schema in schema.sql
and swap the DB helper functions in this file for mysql.connector
calls (the SQL is intentionally kept ANSI-compatible to ease that
migration).

Run:  python3 server.py
Then open http://localhost:8000/index.html
Default owner login: owner@grt.com / GrtOwner@2026
====================================================================
"""

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "grt_reunion.db")
SESSION_TTL_MINUTES = 60
PORT = 8000

# --------------------------------------------------------------
# Security helpers
# --------------------------------------------------------------
def hash_password(password, salt=None):
    """PBKDF2-HMAC-SHA256 password hashing with per-user salt."""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return f"{salt}${digest.hex()}"


def verify_password(password, stored_hash):
    try:
        salt, digest_hex = stored_hash.split("$")
    except (ValueError, AttributeError):
        return False
    new_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return hmac.compare_digest(new_hash.hex(), digest_hex)


def new_token(n_bytes=32):
    return secrets.token_urlsafe(n_bytes)


def sanitize(text):
    """Basic XSS prevention: escape angle brackets for any stored text."""
    if text is None:
        return text
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


# --------------------------------------------------------------
# Database layer (SQLite runtime; mirrors schema.sql structure)
# --------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    fresh = not os.path.exists(DB_PATH)
    conn = get_db()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            role_id INTEGER NOT NULL,
            avatar_then TEXT,
            avatar_now TEXT,
            phone TEXT,
            bio TEXT,
            quote TEXT,
            city TEXT,
            profession TEXT,
            company TEXT,
            school_memory TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (role_id) REFERENCES roles(id)
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS login_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_attempted TEXT,
            success INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS invitations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            email TEXT,
            created_by INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            revoked INTEGER DEFAULT 0,
            used_by INTEGER,
            used_at TEXT,
            resend_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS albums (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            cover_photo TEXT,
            created_by INTEGER
        );
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            album_id INTEGER NOT NULL,
            uploaded_by INTEGER,
            file_path TEXT NOT NULL,
            caption TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            venue TEXT,
            hotel_name TEXT,
            hotel_details TEXT,
            map_lat REAL,
            map_lng REAL,
            starts_at TEXT NOT NULL,
            created_by INTEGER
        );
        CREATE TABLE IF NOT EXISTS rsvps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            status TEXT DEFAULT 'maybe',
            guests INTEGER DEFAULT 0,
            UNIQUE(event_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            pinned INTEGER DEFAULT 0,
            created_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            target_type TEXT NOT NULL,
            target_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            target_type TEXT NOT NULL,
            target_id INTEGER NOT NULL,
            UNIQUE(user_id, target_type, target_id)
        );
        CREATE TABLE IF NOT EXISTS lost_found (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            posted_by INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'lost',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS career_opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            posted_by INTEGER NOT NULL,
            title TEXT NOT NULL,
            company TEXT,
            description TEXT,
            location TEXT,
            link TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            body TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT
        );
        """
    )
    conn.commit()

    if fresh:
        seed(conn)
    conn.close()


def seed(conn):
    cur = conn.cursor()
    cur.executemany("INSERT INTO roles (name) VALUES (?)", [("owner",), ("admin",), ("classmate",)])
    conn.commit()

    owner_pw = hash_password("GrtOwner@2026")
    cur.execute(
        "INSERT INTO users (full_name, email, password_hash, role_id, bio) VALUES (?,?,?,1,?)",
        ("Reunion Owner", "owner@grt.com", owner_pw, "Owner & Administrator of GRT 2006-2007."),
    )

    demo_classmates = [
        ("Ananya Rao", "ananya.rao@example.com", "Bengaluru", "Product Manager", "Wipro", "Best lunch-break cricket games ever."),
        ("Vikram Sethi", "vikram.sethi@example.com", "Mumbai", "Architect", "L&T", "Still remember the annual day fiasco!"),
        ("Priya Nair", "priya.nair@example.com", "Hyderabad", "Doctor", "Apollo Hospitals", "Our farewell party was unforgettable."),
        ("Rahul Verma", "rahul.verma@example.com", "Delhi", "Entrepreneur", "Self-employed", "Football team forever!"),
    ]
    for name, email, city, prof, comp, mem in demo_classmates:
        cur.execute(
            """INSERT INTO users (full_name, email, password_hash, role_id, city, profession, company, school_memory)
               VALUES (?,?,?,3,?,?,?,?)""",
            (name, email, hash_password("classmate123"), city, prof, comp, mem),
        )

    cur.execute(
        "INSERT INTO announcements (title, body, pinned, created_by) VALUES (?,?,1,1)",
        ("Welcome to GRT 2026!", "Registrations are now open for the Grand Reunion Tour. RSVP and reconnect with your batch!"),
    )
    cur.execute(
        """INSERT INTO events (title, description, venue, hotel_name, hotel_details, starts_at, created_by)
           VALUES (?,?,?,?,?,?,1)""",
        (
            "Grand Reunion Night",
            "An unforgettable evening of music, memories and reunions.",
            "The Grand Ballroom, City Convention Centre",
            "The Grand Palace Hotel",
            "Rooms blocked at special reunion rate. Mention 'GRT2026' at check-in.",
            "2026-12-19 18:00:00",
        ),
    )
    cur.execute("INSERT INTO albums (title, description, created_by) VALUES (?,?,1)",
                ("Then & Now", "A collection of memories across the years.",))
    cur.execute("INSERT INTO settings (setting_key, setting_value) VALUES (?,?)",
                ("reunion_date", "2026-12-19T18:00:00"))
    cur.execute("INSERT INTO settings (setting_key, setting_value) VALUES (?,?)",
                ("site_title", "Grand Reunion Tour 2006-2007"))
    conn.commit()


# --------------------------------------------------------------
# Session helpers
# --------------------------------------------------------------
def create_session(user_id):
    conn = get_db()
    token = new_token()
    expires = (datetime.utcnow() + timedelta(minutes=SESSION_TTL_MINUTES)).isoformat()
    conn.execute("INSERT INTO sessions (id, user_id, expires_at) VALUES (?,?,?)", (token, user_id, expires))
    conn.commit()
    conn.close()
    return token


def get_user_from_session(token):
    if not token:
        return None
    conn = get_db()
    row = conn.execute(
        """SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id
           WHERE s.id = ? AND s.expires_at > ?""",
        (token, datetime.utcnow().isoformat()),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# --------------------------------------------------------------
# Rate limiting (simple in-memory window per IP)
# --------------------------------------------------------------
_rate_buckets = {}


def rate_limited(ip, key, limit=10, window_seconds=60):
    now = time.time()
    bucket_key = f"{ip}:{key}"
    hits = _rate_buckets.get(bucket_key, [])
    hits = [t for t in hits if now - t < window_seconds]
    hits.append(now)
    _rate_buckets[bucket_key] = hits
    return len(hits) > limit


# --------------------------------------------------------------
# HTTP Handler
# --------------------------------------------------------------
STATIC_EXTENSIONS = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".json": "application/json",
}


class GRTHandler(BaseHTTPRequestHandler):
    server_version = "GRT-Reunion/1.0"

    def log_message(self, fmt, *args):
        pass  # quieter console output

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode())
        except json.JSONDecodeError:
            return {}

    def _session_token(self):
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            part = part.strip()
            if part.startswith("grt_session="):
                return part.split("=", 1)[1]
        return None

    def _current_user(self):
        return get_user_from_session(self._session_token())

    def _client_ip(self):
        return self.client_address[0]

    def _serve_static(self, path):
        if path == "/" or path == "":
            path = "/index.html"
        safe_path = os.path.normpath(path).lstrip("/\\")
        full_path = os.path.join(BASE_DIR, safe_path)
        if not full_path.startswith(BASE_DIR) or not os.path.isfile(full_path):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")
            return
        ext = os.path.splitext(full_path)[1].lower()
        content_type = STATIC_EXTENSIONS.get(ext, "application/octet-stream")
        with open(full_path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            self.handle_api_get(path, parse_qs(parsed.query))
        else:
            self._serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.handle_api_post(parsed.path)
        else:
            self.send_response(404)
            self.end_headers()

    def handle_api_get(self, path, query):
        conn = get_db()
        try:
            if path == "/api/settings":
                rows = conn.execute("SELECT setting_key, setting_value FROM settings").fetchall()
                self._send_json({s["setting_key"]: s["setting_value"] for s in rows})

            elif path == "/api/students":
                search = (query.get("q", [""])[0] or "").lower()
                rows = conn.execute(
                    "SELECT id, full_name, city, profession, company, school_memory, bio, quote FROM users WHERE role_id = 3"
                ).fetchall()
                results = [dict(r) for r in rows if search in r["full_name"].lower() or search in (r["city"] or "").lower()]
                self._send_json({"students": results})

            elif path == "/api/announcements":
                rows = conn.execute("SELECT * FROM announcements ORDER BY pinned DESC, created_at DESC").fetchall()
                self._send_json({"announcements": [dict(r) for r in rows]})

            elif path == "/api/events":
                rows = conn.execute("SELECT * FROM events ORDER BY starts_at ASC").fetchall()
                self._send_json({"events": [dict(r) for r in rows]})

            elif path == "/api/albums":
                rows = conn.execute("SELECT * FROM albums").fetchall()
                self._send_json({"albums": [dict(r) for r in rows]})

            elif path == "/api/photos":
                album_id = query.get("album_id", [None])[0]
                if album_id:
                    rows = conn.execute("SELECT * FROM photos WHERE album_id=?", (album_id,)).fetchall()
                else:
                    rows = conn.execute("SELECT * FROM photos").fetchall()
                self._send_json({"photos": [dict(r) for r in rows]})

            elif path == "/api/messages":
                rows = conn.execute(
                    """SELECT m.*, u.full_name FROM messages m JOIN users u ON u.id = m.user_id
                       ORDER BY m.created_at DESC LIMIT 100"""
                ).fetchall()
                self._send_json({"messages": [dict(r) for r in rows]})

            elif path == "/api/lostfound":
                rows = conn.execute("SELECT * FROM lost_found ORDER BY created_at DESC").fetchall()
                self._send_json({"items": [dict(r) for r in rows]})

            elif path == "/api/careers":
                rows = conn.execute("SELECT * FROM career_opportunities ORDER BY created_at DESC").fetchall()
                self._send_json({"careers": [dict(r) for r in rows]})

            elif path == "/api/notifications":
                user = self._current_user()
                if not user:
                    self._send_json({"error": "unauthorized"}, 401)
                else:
                    rows = conn.execute(
                        "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC", (user["id"],)
                    ).fetchall()
                    self._send_json({"notifications": [dict(r) for r in rows]})

            elif path == "/api/me":
                user = self._current_user()
                if user:
                    user.pop("password_hash", None)
                    self._send_json({"user": user})
                else:
                    self._send_json({"user": None})

            elif path == "/api/invitations":
                user = self._current_user()
                if not user or user["role_id"] != 1:
                    self._send_json({"error": "forbidden"}, 403)
                else:
                    rows = conn.execute("SELECT * FROM invitations ORDER BY created_at DESC").fetchall()
                    self._send_json({"invitations": [dict(r) for r in rows]})

            else:
                self._send_json({"error": "not found"}, 404)
        finally:
            conn.close()

    def handle_api_post(self, path):
        ip = self._client_ip()
        body = self._read_json_body()
        conn = get_db()
        try:
            if path == "/api/login":
                if rate_limited(ip, "login", limit=8, window_seconds=120):
                    self._send_json({"error": "Too many attempts. Try again later."}, 429)
                    return
                email = (body.get("email") or "").strip().lower()
                password = body.get("password") or ""
                row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
                success = bool(row) and bool(row["password_hash"]) and verify_password(password, row["password_hash"])
                conn.execute("INSERT INTO login_logs (email_attempted, success) VALUES (?,?)", (email, int(success)))
                conn.commit()
                if not success:
                    self._send_json({"error": "Invalid email or password."}, 401)
                    return
                token = create_session(row["id"])
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header(
                    "Set-Cookie",
                    f"grt_session={token}; HttpOnly; Path=/; Max-Age={SESSION_TTL_MINUTES*60}; SameSite=Strict",
                )
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "role_id": row["role_id"]}).encode())

            elif path == "/api/logout":
                token = self._session_token()
                if token:
                    conn.execute("DELETE FROM sessions WHERE id=?", (token,))
                    conn.commit()
                self._send_json({"ok": True})

            elif path == "/api/invitations/create":
                user = self._current_user()
                if not user or user["role_id"] != 1:
                    self._send_json({"error": "forbidden"}, 403)
                    return
                token = new_token(12)
                hours = int(body.get("expires_hours", 72))
                expires = (datetime.utcnow() + timedelta(hours=hours)).isoformat()
                conn.execute(
                    "INSERT INTO invitations (token, email, created_by, expires_at) VALUES (?,?,?,?)",
                    (token, sanitize(body.get("email", "")), user["id"], expires),
                )
                conn.commit()
                self._send_json({"ok": True, "token": token, "invite_url": f"/invite.html?token={token}"})

            elif path == "/api/invitations/accept":
                token = body.get("token")
                row = conn.execute("SELECT * FROM invitations WHERE token=?", (token,)).fetchone()
                if not row or row["revoked"] or row["used_by"]:
                    self._send_json({"error": "Invalid or expired invitation."}, 400)
                    return
                if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
                    self._send_json({"error": "This invitation has expired."}, 400)
                    return
                full_name = sanitize(body.get("full_name", "")).strip()
                email = sanitize(body.get("email", "")).strip().lower()
                password = body.get("password") or ""
                if not full_name or not email:
                    self._send_json({"error": "Name and email are required."}, 400)
                    return
                pw_hash = hash_password(password) if password else None
                city = sanitize(body.get("city", "")).strip()
                profession = sanitize(body.get("profession", "")).strip()
                school_memory = sanitize(body.get("school_memory", "")).strip()
                cur = conn.execute(
                    "INSERT INTO users (full_name, email, password_hash, role_id, city, profession, school_memory) "
                    "VALUES (?,?,?,3,?,?,?)",
                    (full_name, email, pw_hash, city, profession, school_memory),
                )
                conn.execute(
                    "UPDATE invitations SET used_by=?, used_at=? WHERE id=?",
                    (cur.lastrowid, datetime.utcnow().isoformat(), row["id"]),
                )
                conn.commit()
                self._send_json({"ok": True})

            elif path == "/api/profile/update":
                user = self._current_user()
                if not user:
                    self._send_json({"error": "unauthorized"}, 401)
                    return
                fields = {}
                for key in ("full_name", "phone", "bio", "quote", "city", "profession",
                            "company", "school_memory", "avatar_then", "avatar_now"):
                    if key in body:
                        fields[key] = sanitize(str(body.get(key) or ""))
                if not fields:
                    self._send_json({"error": "No profile fields supplied."}, 400)
                    return
                set_clause = ", ".join(f"{k}=?" for k in fields)
                conn.execute(
                    f"UPDATE users SET {set_clause} WHERE id=?",
                    (*fields.values(), user["id"]),
                )
                conn.commit()
                self._send_json({"ok": True, "profile": fields})

            elif path == "/api/rsvp":
                user = self._current_user()
                if not user:
                    self._send_json({"error": "unauthorized"}, 401)
                    return
                conn.execute(
                    """INSERT INTO rsvps (event_id, user_id, status, guests) VALUES (?,?,?,?)
                       ON CONFLICT(event_id, user_id) DO UPDATE SET status=excluded.status, guests=excluded.guests""",
                    (body.get("event_id"), user["id"], body.get("status", "maybe"), int(body.get("guests", 0))),
                )
                conn.commit()
                self._send_json({"ok": True})

            elif path == "/api/messages/post":
                user = self._current_user()
                if not user:
                    self._send_json({"error": "unauthorized"}, 401)
                    return
                text = sanitize(body.get("body", "")).strip()
                if not text:
                    self._send_json({"error": "Message cannot be empty."}, 400)
                    return
                conn.execute("INSERT INTO messages (user_id, body) VALUES (?,?)", (user["id"], text))
                conn.commit()
                self._send_json({"ok": True})

            elif path == "/api/lostfound/create":
                user = self._current_user()
                if not user:
                    self._send_json({"error": "unauthorized"}, 401)
                    return
                conn.execute(
                    "INSERT INTO lost_found (posted_by, item_name, description, status) VALUES (?,?,?,?)",
                    (user["id"], sanitize(body.get("item_name", "")), sanitize(body.get("description", "")), body.get("status", "lost")),
                )
                conn.commit()
                self._send_json({"ok": True})

            elif path == "/api/likes/toggle":
                user = self._current_user()
                if not user:
                    self._send_json({"error": "unauthorized"}, 401)
                    return
                target_type = body.get("target_type")
                target_id = body.get("target_id")
                existing = conn.execute(
                    "SELECT id FROM likes WHERE user_id=? AND target_type=? AND target_id=?",
                    (user["id"], target_type, target_id),
                ).fetchone()
                if existing:
                    conn.execute("DELETE FROM likes WHERE id=?", (existing["id"],))
                    liked = False
                else:
                    conn.execute(
                        "INSERT INTO likes (user_id, target_type, target_id) VALUES (?,?,?)",
                        (user["id"], target_type, target_id),
                    )
                    liked = True
                conn.commit()
                count = conn.execute(
                    "SELECT COUNT(*) c FROM likes WHERE target_type=? AND target_id=?", (target_type, target_id)
                ).fetchone()["c"]
                self._send_json({"ok": True, "liked": liked, "count": count})

            elif path == "/api/comments/create":
                user = self._current_user()
                if not user:
                    self._send_json({"error": "unauthorized"}, 401)
                    return
                conn.execute(
                    "INSERT INTO comments (user_id, target_type, target_id, body) VALUES (?,?,?,?)",
                    (user["id"], body.get("target_type"), body.get("target_id"), sanitize(body.get("body", ""))),
                )
                conn.commit()
                self._send_json({"ok": True})

            else:
                self._send_json({"error": "not found"}, 404)
        finally:
            conn.close()


def main():
    init_db()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), GRTHandler)
    print(f"GRT Reunion server running -> http://localhost:{PORT}/index.html")
    print("Owner login: owner@grt.com / GrtOwner@2026")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
