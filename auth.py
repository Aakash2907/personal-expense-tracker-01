"""
auth.py  -  Registration, password hashing and user lookup.

What it does : registers new users, hashes/checks passwords, finds users by
               email and creates the default Admin and Auditor accounts.
Why needed   : the diagrams contain "Register Account", "Login" and the
               "Authentication Component / 1.0 User Authentication" process.
Talks to     : database.py (users table), validation.py, models.py (calls it).
Diagram      : Use case -> Register Account, Login
               DFD -> 1.0 User Authentication (reads/writes D1: User Database)
               State diagram -> Login -> Authenticating
"""

import hashlib
import os
import sqlite3

from database import insert, query
from validation import validate_email, validate_password, validate_text


def hash_password(password, salt=None):
    """Return 'salt$hash'. We never store the real password in the database."""
    if salt is None:
        salt = os.urandom(8).hex()          # random text added to the password
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 50000)
    return salt + "$" + digest.hex()


def check_password(password, stored_hash):
    """True if the typed password matches the stored 'salt$hash'."""
    salt = stored_hash.split("$")[0]
    return hash_password(password, salt) == stored_hash


def register_user(username, email, password, role="user"):
    """Validate the details and add a new user. Returns the new user_id."""
    username = validate_text(username, "username", 30)
    email = validate_email(email)
    password = validate_password(password)
    try:
        user_id = insert(
            "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
            (username, email, hash_password(password), role))
    except sqlite3.IntegrityError:
        raise ValueError("This email is already registered.")
    # every user gets default settings (currency, alerts on)
    insert("INSERT INTO settings (user_id) VALUES (?)", (user_id,))
    return user_id


def find_user(email):
    """Return the user row (dictionary) for an email, or None."""
    rows = query("SELECT * FROM users WHERE email = ?", (str(email).strip().lower(),))
    return rows[0] if rows else None


def create_default_accounts():
    """Create one Admin and one Auditor account the first time the app runs.
    (The use-case diagram only lets a normal User register by themselves.)"""
    if find_user("admin@example.com") is None:
        register_user("Admin", "admin@example.com", "admin123", role="admin")
    if find_user("auditor@example.com") is None:
        register_user("Auditor", "auditor@example.com", "audit123", role="auditor")
