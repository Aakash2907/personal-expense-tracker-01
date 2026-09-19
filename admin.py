"""
frontend/admin.py  -  Admin dashboard and account management.

What it does : counts users/transactions for the Admin Dashboard, lists all
               accounts, activates/deactivates an account or deletes it.
Why needed   : the Admin actor has "Admin Dashboard" which <<include>>s
               "Manage Accounts" in the use case diagram.
Talks to     : database.py, models.py (Admin class), ui/admin.py (Admin screen).
Diagram      : Use case -> Admin Dashboard, Manage Accounts
               Class -> Admin.viewDashboard(), Admin.manageAccounts()
                        (Admin "manages" many SystemUsers)
"""

from database import execute, query


def get_dashboard_stats():
    """Small numbers shown at the top of the Admin dashboard."""
    def count(sql):
        return query(sql)[0]["n"]
    return {
        "regular_users": count("SELECT COUNT(*) AS n FROM users WHERE role = 'user'"),
        "active_accounts": count("SELECT COUNT(*) AS n FROM users WHERE is_active = 1"),
        "transactions": count("SELECT COUNT(*) AS n FROM transactions"),
        "audit_reports": count("SELECT COUNT(*) AS n FROM audit_reports"),
    }


def list_users():
    """Every account (never includes the password)."""
    return query("SELECT user_id, username, email, role, is_active "
                 "FROM users ORDER BY user_id")


def set_user_active(user_id, active, admin_id):
    """Enable or disable an account. A disabled user cannot log in."""
    if user_id == admin_id:
        raise ValueError("You cannot disable your own account.")
    changed = execute("UPDATE users SET is_active = ? WHERE user_id = ?",
                      (1 if active else 0, user_id))
    if changed == 0:
        raise ValueError("Account not found.")


def delete_user(user_id, admin_id):
    """Delete an account and (through ON DELETE CASCADE) all of its data."""
    if user_id == admin_id:
        raise ValueError("You cannot delete your own account.")
    rows = query("SELECT role FROM users WHERE user_id = ?", (user_id,))
    if not rows:
        raise ValueError("Account not found.")
    if rows[0]["role"] == "admin":
        raise ValueError("Admin accounts cannot be deleted.")
    execute("DELETE FROM users WHERE user_id = ?", (user_id,))
