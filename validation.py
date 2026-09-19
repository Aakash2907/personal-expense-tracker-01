"""
validation.py

Central validation functions used by both the desktop and Flask versions
of the Personal Expense Tracker.
"""

import math
import re
from datetime import datetime

DISPLAY_DATE_FORMAT = "%d-%m-%Y"
DB_DATE_FORMAT = "%Y-%m-%d"

EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
)

EXPENSE_CATEGORIES = {
    "Food",
    "Transport",
    "Education",
    "Shopping",
    "Entertainment",
    "Bills",
    "Medical",
    "Other",
}

INCOME_CATEGORIES = {
    "Salary",
    "Pocket Money",
    "Scholarship",
    "Gift",
    "Other",
}


def validate_amount(text):
    """Return a positive finite amount rounded to two decimals."""

    text = str(text).strip().replace(",", "")

    if text == "":
        raise ValueError("Please enter an amount.")

    try:
        amount = float(text)
    except (TypeError, ValueError):
        raise ValueError("Please enter a valid amount.")

    if not math.isfinite(amount):
        raise ValueError("Please enter a valid amount.")

    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    return round(amount, 2)


def validate_date(text):
    """Convert DD-MM-YYYY into YYYY-MM-DD."""

    text = str(text).strip()

    if not text:
        raise ValueError("Please enter a date.")

    try:
        parsed = datetime.strptime(
            text,
            DISPLAY_DATE_FORMAT
        )
    except ValueError:
        raise ValueError(
            "Please enter a valid date (DD-MM-YYYY)."
        )

    return parsed.strftime(DB_DATE_FORMAT)


def validate_text(text, field_name, max_length=100):
    """Validate normal text fields."""

    text = str(text).strip()

    if text == "":
        raise ValueError(
            "Please enter the " + field_name + "."
        )

    if len(text) > max_length:
        raise ValueError(
            field_name.capitalize() + " is too long."
        )

    return text


def validate_type(type_):
    """Only Expense and Income are allowed."""

    type_ = str(type_).strip()

    if type_ not in ("Expense", "Income"):
        raise ValueError(
            "Type must be Expense or Income."
        )

    return type_


def validate_category(category, transaction_type=None):
    """
    Validate category against the correct category list.

    transaction_type is optional to preserve compatibility with the
    existing desktop code.
    """

    category = str(category).strip()

    if not category:
        raise ValueError(
            "Please select a category."
        )

    if transaction_type == "Expense":
        allowed = EXPENSE_CATEGORIES

    elif transaction_type == "Income":
        allowed = INCOME_CATEGORIES

    else:
        allowed = EXPENSE_CATEGORIES | INCOME_CATEGORIES

    if category not in allowed:
        raise ValueError(
            "Please select a valid category."
        )

    return category


def validate_email(email):
    """Validate and normalize an email address."""

    email = str(email).strip().lower()

    if not EMAIL_PATTERN.fullmatch(email):
        raise ValueError(
            "Please enter a valid email address."
        )

    return email


def validate_password(password):
    """Validate a password."""

    password = str(password)

    if len(password) < 6:
        raise ValueError(
            "Password must be at least 6 characters."
        )

    if len(password) > 128:
        raise ValueError(
            "Password is too long."
        )

    return password


def validate_date_range(start_text="", end_text=""):
    """
    Validate an optional date range.

    Returns:
        (start_db_date, end_db_date)
    """

    start_text = str(start_text or "").strip()
    end_text = str(end_text or "").strip()

    start = (
        validate_date(start_text)
        if start_text
        else None
    )

    end = (
        validate_date(end_text)
        if end_text
        else None
    )

    if start and end and start > end:
        raise ValueError(
            "The 'From' date must be before the 'To' date."
        )

    return start, end


def to_display_date(db_date):
    """Convert YYYY-MM-DD to DD-MM-YYYY."""

    if not db_date:
        return ""

    try:
        return datetime.strptime(
            str(db_date),
            DB_DATE_FORMAT
        ).strftime(DISPLAY_DATE_FORMAT)
    except ValueError:
        return str(db_date)


def today_display():
    """Return today's date as DD-MM-YYYY."""

    return datetime.now().strftime(
        DISPLAY_DATE_FORMAT
    )