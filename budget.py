"""
budget.py

Monthly budget management and budget alerts.
"""

import calendar
from datetime import date

from database import (
    execute,
    insert,
    query,
)

from settings import (
    format_money,
    get_settings,
)

from transactions import (
    get_total_expenses,
)

from validation import (
    validate_amount,
)


ALERT_PERCENT = 80


def month_range(day=None):
    """Return first and last day of a month."""

    day = day or date.today()

    last_day = calendar.monthrange(
        day.year,
        day.month,
    )[1]

    return (
        day.replace(day=1).isoformat(),
        day.replace(
            day=last_day
        ).isoformat(),
    )


def set_budget(
    user_id,
    amount,
):
    """Create or update the user's monthly budget."""

    amount = validate_amount(
        amount
    )

    start, end = month_range()

    existing = get_budget(
        user_id
    )

    if existing is None:

        insert(
            """
            INSERT INTO budgets
            (
                user_id,
                amount,
                start_date,
                end_date
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                amount,
                start,
                end,
            ),
        )

    else:

        execute(
            """
            UPDATE budgets
            SET
                amount = ?,
                start_date = ?,
                end_date = ?
            WHERE user_id = ?
            """,
            (
                amount,
                start,
                end,
                user_id,
            ),
        )

    return True


def get_budget(user_id):
    """Return current budget or None."""

    rows = query(
        """
        SELECT *
        FROM budgets
        WHERE user_id = ?
        """,
        (user_id,),
    )

    if not rows:
        return None

    budget = rows[0]

    start, end = month_range()

    # Automatically renew the budget period
    # while preserving the budget amount.
    if budget["end_date"] < start:

        execute(
            """
            UPDATE budgets
            SET
                start_date = ?,
                end_date = ?
            WHERE user_id = ?
            """,
            (
                start,
                end,
                user_id,
            ),
        )

        budget["start_date"] = start
        budget["end_date"] = end

    return budget


def get_budget_status(user_id):
    """
    Return budget status.

    percent = actual utilization.
    progress_percent = capped at 100 for UI progress bars.
    """

    budget = get_budget(
        user_id
    )

    if budget is None:
        return None

    spent = get_total_expenses(
        user_id,
        budget["start_date"],
        budget["end_date"],
    )

    raw_percent = (
        spent
        / budget["amount"]
        * 100
    )

    return {
        "budget": round(
            budget["amount"],
            2,
        ),
        "spent": round(
            spent,
            2,
        ),
        "remaining": round(
            budget["amount"] - spent,
            2,
        ),
        "percent": round(
            raw_percent
        ),
        "progress_percent": min(
            round(raw_percent),
            100,
        ),
    }


def check_budget_alert(user_id):
    """Return budget warning or None."""

    settings = get_settings(
        user_id
    )

    if not settings[
        "alerts_enabled"
    ]:
        return None

    status = get_budget_status(
        user_id
    )

    if status is None:
        return None

    currency = settings[
        "currency"
    ]

    if status["percent"] >= 100:

        return (
            "Budget exceeded! "
            "You have spent "
            + format_money(
                status["spent"],
                currency,
            )
            + " of your "
            + format_money(
                status["budget"],
                currency,
            )
            + " monthly budget."
        )

    if status["percent"] >= ALERT_PERCENT:

        return (
            "Warning: you have used "
            + str(status["percent"])
            + "% of your monthly budget."
        )

    return None