"""
transactions.py

Transaction CRUD operations and financial totals.
"""

from database import (
    execute,
    insert,
    query,
)

from validation import (
    validate_amount,
    validate_category,
    validate_date,
    validate_date_range,
    validate_text,
    validate_type,
)


def _clean_fields(
    type_,
    amount,
    category,
    description,
    date_text,
):
    """Validate all transaction fields."""

    type_ = validate_type(type_)

    amount = validate_amount(
        amount
    )

    category = validate_category(
        category,
        type_,
    )

    description = validate_text(
        description,
        "description",
        200,
    )

    date = validate_date(
        date_text
    )

    return (
        type_,
        amount,
        category,
        description,
        date,
    )


def add_transaction(
    user_id,
    type_,
    amount,
    category,
    description,
    date_text,
):
    """Create a transaction."""

    (
        type_,
        amount,
        category,
        description,
        date,
    ) = _clean_fields(
        type_,
        amount,
        category,
        description,
        date_text,
    )

    return insert(
        """
        INSERT INTO transactions
        (
            user_id,
            type,
            amount,
            category,
            description,
            date
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            type_,
            amount,
            category,
            description,
            date,
        ),
    )


def add_expense(
    user_id,
    amount,
    category,
    description,
    date_text,
):
    return add_transaction(
        user_id,
        "Expense",
        amount,
        category,
        description,
        date_text,
    )


def add_income(
    user_id,
    amount,
    source,
    description,
    date_text,
):
    return add_transaction(
        user_id,
        "Income",
        amount,
        source,
        description,
        date_text,
    )


def get_transactions(
    user_id,
    type_=None,
    category=None,
    date_from=None,
    date_to=None,
    search=None,
    limit=None,
):
    """Return the user's transactions."""

    sql = """
        SELECT *
        FROM transactions
        WHERE user_id = ?
    """

    params = [user_id]

    if type_ and type_ != "All":

        type_ = validate_type(
            type_
        )

        sql += " AND type = ?"
        params.append(type_)

    if category and category != "All":

        category = str(
            category
        ).strip()

        if category not in (
            set(
                __import__(
                    "database"
                ).ALL_CATEGORIES
            )
        ):
            raise ValueError(
                "Please select a valid category."
            )

        sql += " AND category = ?"
        params.append(category)

    start, end = validate_date_range(
        date_from,
        date_to,
    )

    if start:
        sql += " AND date >= ?"
        params.append(start)

    if end:
        sql += " AND date <= ?"
        params.append(end)

    if search and str(search).strip():

        search = str(
            search
        ).strip()[:100]

        sql += """
            AND (
                description LIKE ?
                OR category LIKE ?
            )
        """

        search_pattern = (
            "%" + search + "%"
        )

        params.extend(
            [
                search_pattern,
                search_pattern,
            ]
        )

    sql += """
        ORDER BY
            date DESC,
            transaction_id DESC
    """

    if limit is not None:

        try:
            limit = int(limit)
        except (TypeError, ValueError):
            raise ValueError(
                "Invalid transaction limit."
            )

        if limit <= 0:
            raise ValueError(
                "Transaction limit must be positive."
            )

        limit = min(
            limit,
            500,
        )

        sql += " LIMIT ?"
        params.append(limit)

    return query(
        sql,
        params,
    )


def get_transaction(
    user_id,
    transaction_id,
):
    """Return one transaction belonging to the user."""

    rows = query(
        """
        SELECT *
        FROM transactions
        WHERE transaction_id = ?
          AND user_id = ?
        """,
        (
            transaction_id,
            user_id,
        ),
    )

    return rows[0] if rows else None


def update_transaction(
    user_id,
    transaction_id,
    type_,
    amount,
    category,
    description,
    date_text,
):
    """Update a transaction belonging to the user."""

    (
        type_,
        amount,
        category,
        description,
        date,
    ) = _clean_fields(
        type_,
        amount,
        category,
        description,
        date_text,
    )

    changed = execute(
        """
        UPDATE transactions
        SET
            type = ?,
            amount = ?,
            category = ?,
            description = ?,
            date = ?
        WHERE transaction_id = ?
          AND user_id = ?
        """,
        (
            type_,
            amount,
            category,
            description,
            date,
            transaction_id,
            user_id,
        ),
    )

    if changed == 0:
        raise ValueError(
            "Transaction not found."
        )


def delete_transaction(
    user_id,
    transaction_id,
):
    """Delete a user's transaction."""

    changed = execute(
        """
        DELETE FROM transactions
        WHERE transaction_id = ?
          AND user_id = ?
        """,
        (
            transaction_id,
            user_id,
        ),
    )

    if changed == 0:
        raise ValueError(
            "Transaction not found."
        )


def _total(
    user_id,
    type_,
    start=None,
    end=None,
):
    """Calculate total for one transaction type."""

    sql = """
        SELECT
            COALESCE(SUM(amount), 0) AS total
        FROM transactions
        WHERE user_id = ?
          AND type = ?
    """

    params = [
        user_id,
        type_,
    ]

    if start:
        sql += " AND date >= ?"
        params.append(start)

    if end:
        sql += " AND date <= ?"
        params.append(end)

    result = query(
        sql,
        params,
    )

    return round(
        result[0]["total"],
        2,
    )


def get_total_income(
    user_id,
    start=None,
    end=None,
):
    return _total(
        user_id,
        "Income",
        start,
        end,
    )


def get_total_expenses(
    user_id,
    start=None,
    end=None,
):
    return _total(
        user_id,
        "Expense",
        start,
        end,
    )


def get_balance(
    user_id,
    start=None,
    end=None,
):
    return round(
        get_total_income(
            user_id,
            start,
            end,
        )
        -
        get_total_expenses(
            user_id,
            start,
            end,
        ),
        2,
    )