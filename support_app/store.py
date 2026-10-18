"""SQLite persistence. Browser sessions are opaque and stored as hashes."""
import hashlib
from contextlib import contextmanager
import json
import secrets
import sqlite3
import time
from pathlib import Path

DEFAULT_DB = Path(__file__).with_name("runtime") / "support.sqlite3"


def session_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class Store:
    def __init__(self, path=DEFAULT_DB):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY, csrf TEXT NOT NULL, created REAL NOT NULL,
                    room TEXT NOT NULL, customer TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY, session TEXT NOT NULL, role TEXT NOT NULL,
                    payload TEXT NOT NULL, created REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS messages_session ON messages(session, id);
                CREATE TABLE IF NOT EXISTS tickets (
                    id TEXT PRIMARY KEY, session TEXT NOT NULL, request_id TEXT NOT NULL,
                    subject TEXT NOT NULL, category TEXT NOT NULL, description TEXT NOT NULL,
                    transcript TEXT NOT NULL, created REAL NOT NULL,
                    UNIQUE(session, request_id));
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def session(self, token):
        if not token or len(token) > 128:
            return None
        return self.session_by_id(session_hash(token))

    def session_by_id(self, sid):
        with self.connect() as db:
            row = db.execute("SELECT * FROM sessions WHERE id=? AND created>?", (sid, time.time() - 86400 * 7)).fetchone()
        return dict(row) if row else None

    def new_session(self):
        token = secrets.token_urlsafe(32)
        sid = session_hash(token)
        with self.connect() as db:
            db.execute("INSERT INTO sessions VALUES (?, ?, ?, ?, ?)",
                       (sid, secrets.token_urlsafe(24), time.time(), "noura-" + secrets.token_hex(12), "demo-customer"))
        return token, self.session_by_id(sid)

    def messages(self, sid, limit=80):
        with self.connect() as db:
            rows = db.execute("SELECT role,payload FROM messages WHERE session=? ORDER BY id DESC LIMIT ?", (sid, limit)).fetchall()
        return [{"role": r["role"], **json.loads(r["payload"])} for r in reversed(rows)]

    def add_message(self, sid, role, payload):
        with self.connect() as db:
            db.execute("INSERT INTO messages(session,role,payload,created) VALUES (?,?,?,?)", (sid, role, json.dumps(payload, ensure_ascii=False), time.time()))

    def clear(self, sid):
        with self.connect() as db:
            db.execute("DELETE FROM messages WHERE session=?", (sid,))

    def tickets(self, sid):
        with self.connect() as db:
            rows = db.execute("SELECT id,subject,category,description,created FROM tickets WHERE session=? ORDER BY created DESC", (sid,)).fetchall()
        return [dict(row) | {"status": "Saved locally"} for row in rows]

    def create_ticket(self, sid, request_id, subject, category, description, attach):
        transcript = self.messages(sid, 12) if attach else []
        with self.connect() as db:
            existing = db.execute("SELECT id FROM tickets WHERE session=? AND request_id=?", (sid, request_id)).fetchone()
            if existing:
                return existing["id"]
            ticket_id = "NC-" + secrets.token_hex(4).upper()
            db.execute("INSERT INTO tickets VALUES (?,?,?,?,?,?,?,?)", (ticket_id, sid, request_id, subject, category, description,
                                                                        json.dumps(transcript, ensure_ascii=False), time.time()))
        return ticket_id


ORDERS = [
    {"id": "NR-1042", "customer": "demo-customer", "product": "Noura Air", "detail": "Wireless over-ear headphones · Sand", "price": 349,
     "status": "Shipped", "status_ar": "تم الشحن", "destination": "Dubai, UAE", "estimate": "2–3 business days after dispatch", "estimate_ar": "2–3 أيام عمل بعد الشحن",
     "progress": 2, "milestones": ["Order confirmed", "Packed with care", "Handed to courier", "Delivered"], "art": "headphones"},
    {"id": "NR-1036", "customer": "demo-customer", "product": "Noura Mini", "detail": "Portable Bluetooth speaker · Terracotta", "price": 189,
     "status": "Delivered", "status_ar": "تم التوصيل", "destination": "Dubai, UAE", "estimate": "Delivery recorded in this demo", "estimate_ar": "تم تسجيل التوصيل في العرض التجريبي",
     "progress": 3, "milestones": ["Order confirmed", "Packed with care", "Handed to courier", "Delivered"], "art": "speaker"},
]


def customer_orders(customer):
    return [{k: v for k, v in order.items() if k != "customer"} for order in ORDERS if order["customer"] == customer]


def lookup_order(customer, order_id):
    return next((order for order in customer_orders(customer) if order["id"] == order_id.strip().upper()), None)
