"""
sample_data.py  -  Demo data so the project shows meaningful output at once.

What it does : on the FIRST run it creates the default Admin and Auditor
               accounts, one demo user, three months of sample transactions
               and a monthly budget.
Why needed   : makes the demonstration/viva easy (dashboard, reports and
               charts are filled immediately).
Talks to     : auth.py, transactions.py, budget.py, database.py.
Diagram      : none (it only fills the tables shown in the diagrams).

Demo logins
  User    : demo@example.com     / demo123
  Admin   : admin@example.com    / admin123
  Auditor : auditor@example.com  / audit123
To start again with empty data, delete database/expense_tracker.db.
"""

from datetime import date, timedelta

import auth
import budget
import transactions
from database import query


def load_sample_data():
    """Create demo data only if the database has no users yet."""
    if query("SELECT COUNT(*) AS n FROM users")[0]["n"] > 0:
        return

    auth.create_default_accounts()
    user_id = auth.register_user("Demo Student", "demo@example.com", "demo123")

    # first day of this month, last month and two months ago
    this_month = date.today().replace(day=1)
    last_month = (this_month - timedelta(days=1)).replace(day=1)
    two_months_ago = (last_month - timedelta(days=1)).replace(day=1)

    # (day of month, type, category, description, base amount)
    entries = [
        (1,  "Income",  "Salary",        "Monthly salary",   30000),
        (3,  "Expense", "Food",          "Groceries",         2000),
        (5,  "Expense", "Transport",     "Bus pass",          1000),
        (7,  "Expense", "Education",     "Books and course",  3000),
        (10, "Expense", "Shopping",      "Clothes",           2500),
        (12, "Expense", "Bills",         "Electricity bill",  2000),
        (15, "Expense", "Entertainment", "Movie night",        800),
    ]
    # small changes each month so the trend chart is not flat
    months = [(two_months_ago, 0.9), (last_month, 1.1), (this_month, 1.0)]

    for first_day, factor in months:
        for day, type_, category, description, base in entries:
            when = first_day.replace(day=day)
            if when > date.today():            # never create future dates
                when = date.today()
            amount = base if type_ == "Income" else round(base * factor)
            transactions.add_transaction(user_id, type_, amount, category,
                                         description, when.strftime("%d-%m-%Y"))

    budget.set_budget(user_id, 12000)          # shows a budget warning on screen
