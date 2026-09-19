"""
validation.py  -  Input checking functions.

What it does : checks amount, date, text, email, password, type and category.
Why needed   : the flowchart has a "Validate Input?" decision before saving.
               Each function returns a clean value or raises ValueError with
               a short, friendly message that the GUI shows in a message box.
Talks to     : transactions.py, budget.py, auth.py, reports.py (they call it).
Diagram      : Flowchart -> "Validate Input?" ; Sequence -> before "Save".
"""

import math
from datetime import datetime

DISPLAY_DATE_FORMAT = "%d-%m-%Y"   # what the user types / sees  (18-09-2026)
DB_DATE_FORMAT = "%Y-%m-%d"        # how we store it (sorts correctly in SQL)


def validate_amount(text):
    """Return the amount as a float. Must be numeric and greater than zero."""
    text = str(text).strip().replace(",", "")      # allow 20,000
    if text == "":
        raise ValueError("Please enter an amount.")
    try:
        amount = float(text)
    except ValueError:
        raise ValueError("Please enter a valid amount.")
    if not math.isfinite(amount):                  # blocks 'nan' and 'inf'
        raise ValueError("Please enter a valid amount.")
    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")
    return round(amount, 2)


def validate_date(text):
    """Convert DD-MM-YYYY text into the database format YYYY-MM-DD."""
    try:
        parsed = datetime.strptime(str(text).strip(), DISPLAY_DATE_FORMAT)
    except ValueError:
        raise ValueError("Please enter a valid date (DD-MM-YYYY).")
    return parsed.strftime(DB_DATE_FORMAT)


def validate_text(text, field_name, max_length=100):
    """Text fields (description, username) must not be empty or too long."""
    text = str(text).strip()
    if text == "":
        raise ValueError("Please enter the " + field_name + ".")
    if len(text) > max_length:
        raise ValueError(field_name.capitalize() + " is too long.")
    return text


def validate_type(type_):
    if type_ not in ("Expense", "Income"):
        raise ValueError("Type must be Expense or Income.")
    return type_


def validate_category(category):
    if str(category).strip() == "":
        raise ValueError("Please select a category.")
    return str(category).strip()


def validate_email(email):
    email = str(email).strip().lower()
    if "@" not in email or "." not in email.split("@")[-1] or " " in email:
        raise ValueError("Please enter a valid email address.")
    return email


def validate_password(password):
    if len(str(password)) < 4:
        raise ValueError("Password must be at least 4 characters.")
    return str(password)


# ---------------------------------------------------------------------------
# Small date helpers used by the GUI and reports
# ---------------------------------------------------------------------------
def to_display_date(db_date):
    """'2026-09-18' -> '18-09-2026'"""
    return datetime.strptime(db_date, DB_DATE_FORMAT).strftime(DISPLAY_DATE_FORMAT)


def today_display():
    """Today's date as DD-MM-YYYY (default value in the forms)."""
    return datetime.now().strftime(DISPLAY_DATE_FORMAT)
