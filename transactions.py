"""
transactions.py  -  Add / view / update / delete expenses and income.

What it does : all database operations for transactions, plus totals.
Why needed   : "Add Expense", "Edit Expense", "Delete Expenses", "View
               Expenses" and "Income Management" all need these functions.
Talks to     : database.py (SQL), validation.py (checks), models.py (the
               Transaction class calls these), budget.py and reports.py
               (they use the totals).
Diagram      : Use case -> Add Expense, Edit Expense (extends Delete Expenses)
               Flowchart -> Add Expense / View Expenses / Edit / Delete
               DFD -> 2.0 Manage Expenses (reads/writes D2: Expense Database)
               Component -> Transaction Management, Expense Tracking,
                            Income Management

Note: one table stores both types. type = 'Expense' or 'Income'.
"""

from database import execute, insert, query
from validation import (validate_amount, validate_category, validate_date,
                        validate_text, validate_type)


def _clean_fields(type_, amount, category, description, date_text):
    """Validate every field once and return them in database-ready form."""
    return (validate_type(type_),
            validate_amount(amount),
            validate_category(category),
            validate_text(description, "description"),
            validate_date(date_text))


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------
def add_transaction(user_id, type_, amount, category, description, date_text):
    """Validate and save a transaction. Returns the new transaction_id."""
    type_, amount, category, description, date = _clean_fields(
        type_, amount, category, description, date_text)
    return insert(
        "INSERT INTO transactions (user_id, type, amount, category, description, date) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, type_, amount, category, description, date))


def add_expense(user_id, amount, category, description, date_text):
    return add_transaction(user_id, "Expense", amount, category, description, date_text)


def add_income(user_id, amount, source, description, date_text):
    """For income the 'category' is the source (e.g. Salary)."""
    return add_transaction(user_id, "Income", amount, source, description, date_text)


# ---------------------------------------------------------------------------
# READ
# ---------------------------------------------------------------------------
def get_transactions(user_id, type_=None, category=None, date_from=None,
                     date_to=None, search=None, limit=None):
    """Return a user's transactions (newest first).
    Every filter is optional. Dates are typed as DD-MM-YYYY."""
    sql = "SELECT * FROM transactions WHERE user_id = ?"
    params = [user_id]

    if type_ and type_ != "All":
        sql += " AND type = ?"
        params.append(type_)
    if category and category != "All":
        sql += " AND category = ?"
        params.append(category)
    if date_from and date_from.strip():
        sql += " AND date >= ?"
        params.append(validate_date(date_from))
    if date_to and date_to.strip():
        sql += " AND date <= ?"
        params.append(validate_date(date_to))
    if search and search.strip():
        sql += " AND (description LIKE ? OR category LIKE ?)"
        params.append("%" + search.strip() + "%")
        params.append("%" + search.strip() + "%")

    sql += " ORDER BY date DESC, transaction_id DESC"
    if limit:
        sql += " LIMIT ?"
        params.append(int(limit))
    return query(sql, params)


def get_transaction(user_id, transaction_id):
    """Return one transaction (or None if it does not exist)."""
    rows = query("SELECT * FROM transactions WHERE transaction_id = ? AND user_id = ?",
                 (transaction_id, user_id))
    return rows[0] if rows else None


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------
def update_transaction(user_id, transaction_id, type_, amount, category,
                       description, date_text):
    """Validate and update an existing transaction."""
    type_, amount, category, description, date = _clean_fields(
        type_, amount, category, description, date_text)
    changed = execute(
        "UPDATE transactions SET type = ?, amount = ?, category = ?, "
        "description = ?, date = ? WHERE transaction_id = ? AND user_id = ?",
        (type_, amount, category, description, date, transaction_id, user_id))
    if changed == 0:
        raise ValueError("Transaction not found.")


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------
def delete_transaction(user_id, transaction_id):
    """Delete a transaction (the GUI asks for confirmation before calling this)."""
    changed = execute("DELETE FROM transactions WHERE transaction_id = ? AND user_id = ?",
                      (transaction_id, user_id))
    if changed == 0:
        raise ValueError("Transaction not found.")


# ---------------------------------------------------------------------------
# TOTALS   (Balance = Total Income - Total Expenses)
# ---------------------------------------------------------------------------
def _total(user_id, type_, start=None, end=None):
    """Sum of one type. start/end are optional YYYY-MM-DD strings."""
    sql = "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions " \
          "WHERE user_id = ? AND type = ?"
    params = [user_id, type_]
    if start:
        sql += " AND date >= ?"
        params.append(start)
    if end:
        sql += " AND date <= ?"
        params.append(end)
    return round(query(sql, params)[0]["total"], 2)


def get_total_income(user_id, start=None, end=None):
    return _total(user_id, "Income", start, end)


def get_total_expenses(user_id, start=None, end=None):
    return _total(user_id, "Expense", start, end)


def get_balance(user_id, start=None, end=None):
    return round(get_total_income(user_id, start, end) -
                 get_total_expenses(user_id, start, end), 2)
