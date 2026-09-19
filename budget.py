"""
budget.py  -  Monthly budget and budget alerts.

What it does : saves one monthly budget per user, calculates how much of it is
               used, and creates a warning message when spending is close to
               (or over) the budget.
Why needed   : the diagrams contain "Set Budget", "Budget Management",
               "3.0 Manage Budget" and "Notification Component / Alerts".
Talks to     : database.py, transactions.py (total spent), settings.py (are
               alerts enabled?), validation.py, models.py (Budget class).
Diagram      : Use case -> Set Budget          Class -> Budget, updateBudget()
               Flowchart -> Settings > Budget Limit > Set Monthly Budget
               DFD -> 3.0 Manage Budget (D3: Budget Database), Budget Status/Alerts
"""

import calendar
from datetime import date

from database import execute, insert, query
from settings import format_money, get_settings
from transactions import get_total_expenses
from validation import validate_amount

ALERT_PERCENT = 80   # warn when 80% of the budget is used


def month_range(day=None):
    """First and last day (YYYY-MM-DD) of the month that contains 'day'."""
    day = day or date.today()
    last_day = calendar.monthrange(day.year, day.month)[1]
    return day.replace(day=1).isoformat(), day.replace(day=last_day).isoformat()


def set_budget(user_id, amount):
    """Create or update this month's budget (0..1 budget per user)."""
    amount = validate_amount(amount)
    start, end = month_range()
    if get_budget(user_id) is None:
        insert("INSERT INTO budgets (user_id, amount, start_date, end_date) "
               "VALUES (?, ?, ?, ?)", (user_id, amount, start, end))
    else:
        execute("UPDATE budgets SET amount = ?, start_date = ?, end_date = ? "
                "WHERE user_id = ?", (amount, start, end, user_id))
    return True


def get_budget(user_id):
    """Return the user's budget (dictionary) or None if not set.
    A monthly budget renews itself when a new month starts."""
    rows = query("SELECT * FROM budgets WHERE user_id = ?", (user_id,))
    if not rows:
        return None
    budget = rows[0]
    start, end = month_range()
    if budget["end_date"] < start:            # the saved month is over
        execute("UPDATE budgets SET start_date = ?, end_date = ? WHERE user_id = ?",
                (start, end, user_id))
        budget["start_date"], budget["end_date"] = start, end
    return budget


def get_budget_status(user_id):
    """Return budget, spent, remaining and percent used (or None if no budget)."""
    budget = get_budget(user_id)
    if budget is None:
        return None
    spent = get_total_expenses(user_id, budget["start_date"], budget["end_date"])
    return {
        "budget": budget["amount"],
        "spent": spent,
        "remaining": round(budget["amount"] - spent, 2),
        "percent": round(spent / budget["amount"] * 100),
    }


def check_budget_alert(user_id):
    """Return an alert message, or None when no alert is needed.
    (Notification Component: only works if alerts are enabled in Settings.)"""
    settings = get_settings(user_id)
    if not settings["alerts_enabled"]:
        return None
    status = get_budget_status(user_id)
    if status is None:
        return None
    currency = settings["currency"]
    if status["percent"] >= 100:
        return ("Budget exceeded! You have spent " + format_money(status["spent"], currency) +
                " of your " + format_money(status["budget"], currency) + " monthly budget.")
    if status["percent"] >= ALERT_PERCENT:
        return ("Warning: you have used " + str(status["percent"]) +
                "% of your monthly budget.")
    return None
