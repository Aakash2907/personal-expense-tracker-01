"""
auth.py

Registration, password hashing, user lookup and optional demo accounts.
"""

import os
import sqlite3

from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)

from database import insert, query
from validation import (
    validate_email,
    validate_password,
    validate_text,
)


def hash_password(password):
    """Create a secure Werkzeug password hash."""

    return generate_password_hash(
        password,
        method="pbkdf2:sha256",
        salt_length=16,
    )


def check_password(password, stored_hash):
    """Safely verify a password."""

    if not password or not stored_hash:
        return False

    try:
        return check_password_hash(
            stored_hash,
            password,
        )
    except (ValueError, TypeError):
        return False


def register_user(
    username,
    email,
    password,
    role="user",
):
    """Validate and create a user."""

    username = validate_text(
        username,
        "username",
        30,
    )

    email = validate_email(email)
    password = validate_password(password)

    if role not in {
        "user",
        "admin",
        "auditor",
    }:
        raise ValueError(
            "Invalid account role."
        )

    try:
        user_id = insert(
            """
            INSERT INTO users
            (username, email, password, role)
            VALUES (?, ?, ?, ?)
            """,
            (
                username,
                email,
                hash_password(password),
                role,
            ),
        )

    except sqlite3.IntegrityError:
        raise ValueError(
            "This email is already registered."
        )

    # Create default settings.
    insert(
        """
        INSERT OR IGNORE INTO settings
        (user_id)
        VALUES (?)
        """,
        (user_id,),
    )

    return user_id


def find_user(email):
    """Find a user by normalized email."""

    email = str(email).strip().lower()

    rows = query(
        """
        SELECT *
        FROM users
        WHERE email = ?
        """,
        (email,),
    )

    return rows[0] if rows else None


def create_default_accounts():
    """
    Create demo accounts only when DEMO_MODE=true.

    This prevents public production deployments from automatically
    receiving predictable administrator credentials.
    """

    if os.environ.get(
        "DEMO_MODE",
        ""
    ).lower() != "true":
        return

    demo_accounts = [
        (
            "Demo User",
            "demo@example.com",
            "demo123",
            "user",
        ),
        (
            "Administrator",
            "admin@example.com",
            "admin123",
            "admin",
        ),
        (
            "Auditor",
            "auditor@example.com",
            "audit123",
            "auditor",
        ),
    ]

    for username, email, password, role in demo_accounts:

        if find_user(email) is not None:
            continue

        register_user(
            username,
            email,
            password,
            role,
        )