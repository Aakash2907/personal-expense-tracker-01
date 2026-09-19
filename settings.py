"""
settings.py  -  User settings (currency and alerts) and money formatting.

What it does : loads/saves the currency symbol and the "alerts on/off" choice,
               and formats numbers such as 20000 -> "₹20,000.00".
Why needed   : the flowchart's Settings menu has Currency, Budget Limit and
               Notifications (Enable/Disable Alerts).
Talks to     : database.py, budget.py (alerts), reports.py and the GUI
               (format_money).
Diagram      : Flowchart -> Settings > Change Currency / Enable-Disable Alerts
               > Save Settings > Show Confirmation
               State diagram -> Settings state
"""

from database import execute, insert, query

CURRENCIES = ["₹", "$", "€", "£"]


def get_settings(user_id):
    """Return {'currency': '₹', 'alerts_enabled': True} for the user."""
    rows = query("SELECT currency, alerts_enabled FROM settings WHERE user_id = ?",
                 (user_id,))
    if not rows:                                  # first time -> create defaults
        insert("INSERT INTO settings (user_id) VALUES (?)", (user_id,))
        return {"currency": "₹", "alerts_enabled": True}
    return {"currency": rows[0]["currency"],
            "alerts_enabled": bool(rows[0]["alerts_enabled"])}


def save_settings(user_id, currency, alerts_enabled):
    """Save the user's currency and alert choice."""
    if currency not in CURRENCIES:
        raise ValueError("Please choose a currency from the list.")
    get_settings(user_id)                         # makes sure the row exists
    execute("UPDATE settings SET currency = ?, alerts_enabled = ? WHERE user_id = ?",
            (currency, 1 if alerts_enabled else 0, user_id))


def format_money(amount, currency="₹"):
    """20000 -> '₹20,000.00'"""
    return currency + format(amount, ",.2f")
