"""
database.py

SQLite database setup and database helper functions.
"""

import os
import sqlite3


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DB_PATH = os.path.join(
    BASE_DIR,
    "database",
    "expense_tracker.db",
)


EXPENSE_CATEGORIES = [
    "Food",
    "Transport",
    "Education",
    "Shopping",
    "Entertainment",
    "Bills",
    "Medical",
    "Other",
]

INCOME_CATEGORIES = [
    "Salary",
    "Pocket Money",
    "Scholarship",
    "Gift",
    "Other",
]

ALL_CATEGORIES = sorted(
    set(
        EXPENSE_CATEGORIES
        + INCOME_CATEGORIES
    )
)


def get_connection():
    """Open a SQLite connection."""

    directory = os.path.dirname(DB_PATH)

    if directory:
        os.makedirs(
            directory,
            exist_ok=True,
        )

    conn = sqlite3.connect(
        DB_PATH,
        timeout=10,
    )

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    conn.execute(
        "PRAGMA busy_timeout = 10000"
    )

    return conn


def create_database():
    """Create all required tables."""

    conn = get_connection()

    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user'
                    CHECK (
                        role IN (
                            'user',
                            'auditor',
                            'admin'
                        )
                    ),
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL
                    CHECK (
                        type IN (
                            'Expense',
                            'Income'
                        )
                    ),
                amount REAL NOT NULL
                    CHECK (amount > 0),
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                date TEXT NOT NULL,
                FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS budgets (
                budget_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                amount REAL NOT NULL
                    CHECK (amount > 0),
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS settings (
                user_id INTEGER PRIMARY KEY,
                currency TEXT NOT NULL DEFAULT '₹',
                alerts_enabled INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reports (
                report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                report_type TEXT NOT NULL,
                generated_date TEXT NOT NULL,
                FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS audit_reports (
                audit_report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                auditor_id INTEGER NOT NULL,
                generated_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Generated',
                content TEXT NOT NULL,
                FOREIGN KEY (auditor_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS
                idx_transactions_user_date
            ON transactions(user_id, date);

            CREATE INDEX IF NOT EXISTS
                idx_transactions_user_type
            ON transactions(user_id, type);

            CREATE INDEX IF NOT EXISTS
                idx_transactions_user_category
            ON transactions(user_id, category);

            CREATE INDEX IF NOT EXISTS
                idx_reports_user
            ON reports(user_id);

            CREATE INDEX IF NOT EXISTS
                idx_audit_reports_auditor
            ON audit_reports(auditor_id);
            """
        )

        conn.commit()

    finally:
        conn.close()


def query(sql, params=()):
    """Execute SELECT and return dictionaries."""

    conn = get_connection()

    try:
        rows = conn.execute(
            sql,
            params,
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:
        conn.close()


def insert(sql, params=()):
    """Execute INSERT and return the inserted row ID."""

    conn = get_connection()

    try:
        cursor = conn.execute(
            sql,
            params,
        )

        conn.commit()

        return cursor.lastrowid

    finally:
        conn.close()


def execute(sql, params=()):
    """Execute UPDATE or DELETE."""

    conn = get_connection()

    try:
        cursor = conn.execute(
            sql,
            params,
        )

        conn.commit()

        return cursor.rowcount

    finally:
        conn.close()