"""
database.py  -  SQLite database setup and small helper functions.

What it does : creates the database file and all tables, and gives the other
               modules three simple helpers: query(), insert(), execute().
Why needed   : every module stores/reads data through this file, so all SQL
               connection code lives in ONE place.
Talks to     : auth.py, transactions.py, budget.py, settings.py, reports.py,
               audit.py, admin.py (they all import query/insert/execute).
Diagram      : Component diagram -> "Finance Database"
               DFD -> D1 User Database, D2 Expense Database, D3 Budget Database
               (in this student version the three data stores are three tables
               inside ONE SQLite file).
"""

import os
import sqlite3

# ---------------------------------------------------------------------------
# Database location (a variable so the unit tests can point it to a temp file)
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "expense_tracker.db")

# The class diagram stores "category" as a plain string, so categories are a
# simple fixed list (there is no Category class/table in the diagrams).
EXPENSE_CATEGORIES = ["Food", "Transport", "Education", "Shopping",
                      "Entertainment", "Bills", "Medical", "Other"]
INCOME_CATEGORIES = ["Salary", "Pocket Money", "Scholarship", "Gift", "Other"]
ALL_CATEGORIES = sorted(set(EXPENSE_CATEGORIES + INCOME_CATEGORIES))


def get_connection():
    """Open a connection to the SQLite file (folder is created if missing)."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # lets us read columns by name
    conn.execute("PRAGMA foreign_keys = ON")  # enforce relationships
    return conn


def create_database():
    """Create all tables if they do not exist yet (called when app starts)."""
    conn = get_connection()
    try:
        conn.executescript("""
        -- SystemUser / RegularUser / Auditor / Admin (class diagram)
        CREATE TABLE IF NOT EXISTS users (
            user_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            username  TEXT    NOT NULL,
            email     TEXT    NOT NULL UNIQUE,
            password  TEXT    NOT NULL,              -- stored as salted hash
            role      TEXT    NOT NULL DEFAULT 'user'
                      CHECK (role IN ('user', 'auditor', 'admin')),
            is_active INTEGER NOT NULL DEFAULT 1
        );

        -- Expense class (also holds Income: type = 'Income')
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL,
            type           TEXT    NOT NULL CHECK (type IN ('Expense', 'Income')),
            amount         REAL    NOT NULL CHECK (amount > 0),
            category       TEXT    NOT NULL,
            description    TEXT    NOT NULL,
            date           TEXT    NOT NULL,          -- saved as YYYY-MM-DD
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );

        -- Budget class (a user sets 0..1 budget)
        CREATE TABLE IF NOT EXISTS budgets (
            budget_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL UNIQUE,
            amount     REAL    NOT NULL CHECK (amount > 0),
            start_date TEXT    NOT NULL,
            end_date   TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );

        -- Settings screen (currency + notifications on/off)
        CREATE TABLE IF NOT EXISTS settings (
            user_id        INTEGER PRIMARY KEY,
            currency       TEXT    NOT NULL DEFAULT '₹',
            alerts_enabled INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );

        -- Report class (one row every time a user generates a report)
        CREATE TABLE IF NOT EXISTS reports (
            report_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL,
            report_type    TEXT    NOT NULL,
            generated_date TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );

        -- AuditReport class (created by an Auditor)
        CREATE TABLE IF NOT EXISTS audit_reports (
            audit_report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            auditor_id      INTEGER NOT NULL,
            generated_date  TEXT    NOT NULL,
            status          TEXT    NOT NULL DEFAULT 'Generated',
            content         TEXT    NOT NULL,         -- the report as CSV text
            FOREIGN KEY (auditor_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
        """)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Three tiny helpers so other modules never repeat connection code.
# All of them use "?" placeholders (parameterized queries) -> no SQL injection.
# ---------------------------------------------------------------------------
def query(sql, params=()):
    """Run a SELECT and return a list of dictionaries (one per row)."""
    conn = get_connection()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def insert(sql, params=()):
    """Run an INSERT and return the new row id."""
    conn = get_connection()
    try:
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def execute(sql, params=()):
    """Run an UPDATE/DELETE and return how many rows were changed."""
    conn = get_connection()
    try:
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()
