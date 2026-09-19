"""
admin.py

Admin dashboard and account management.
"""

from database import (
    execute,
    query,
)


def get_dashboard_stats():
    """Return statistics for the admin dashboard."""

    def count(sql):
        return query(sql)[0]["n"]

    return {
        "regular_users": count(
            """
            SELECT COUNT(*) AS n
            FROM users
            WHERE role = 'user'
            """
        ),

        "active_accounts": count(
            """
            SELECT COUNT(*) AS n
            FROM users
            WHERE is_active = 1
            """
        ),

        "transactions": count(
            """
            SELECT COUNT(*) AS n
            FROM transactions
            """
        ),

        "audit_reports": count(
            """
            SELECT COUNT(*) AS n
            FROM audit_reports
            """
        ),
    }


def list_users():
    """Return accounts without passwords."""

    return query(
        """
        SELECT
            user_id,
            username,
            email,
            role,
            is_active
        FROM users
        ORDER BY user_id
        """
    )


def set_user_active(
    user_id,
    active,
    admin_id,
):
    """Enable/disable a non-admin account."""

    if user_id == admin_id:
        raise ValueError(
            "You cannot disable your own account."
        )

    rows = query(
        """
        SELECT role
        FROM users
        WHERE user_id = ?
        """,
        (user_id,),
    )

    if not rows:
        raise ValueError(
            "Account not found."
        )

    if rows[0]["role"] == "admin":
        raise ValueError(
            "Admin accounts cannot be disabled."
        )

    changed = execute(
        """
        UPDATE users
        SET is_active = ?
        WHERE user_id = ?
        """,
        (
            1 if active else 0,
            user_id,
        ),
    )

    if changed == 0:
        raise ValueError(
            "Account not found."
        )


def delete_user(
    user_id,
    admin_id,
):
    """Delete a non-admin account."""

    if user_id == admin_id:
        raise ValueError(
            "You cannot delete your own account."
        )

    rows = query(
        """
        SELECT role
        FROM users
        WHERE user_id = ?
        """,
        (user_id,),
    )

    if not rows:
        raise ValueError(
            "Account not found."
        )

    if rows[0]["role"] == "admin":
        raise ValueError(
            "Admin accounts cannot be deleted."
        )

    execute(
        """
        DELETE FROM users
        WHERE user_id = ?
        """,
        (user_id,),
    )