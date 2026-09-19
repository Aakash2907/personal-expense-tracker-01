"""
ui/admin_screen.py  -  Admin Dashboard with Manage Accounts.

What it does : shows simple system numbers and a table of all accounts. The
               admin can enable/disable an account or delete it.
Why needed   : Admin actor -> "Admin Dashboard" <<include>> "Manage Accounts".
Talks to     : models.py (Admin object: view_dashboard, manage_accounts, ...),
               main.py (logout).
Diagram      : Use case -> Admin Dashboard, Manage Accounts
               Class -> Admin.viewDashboard(), Admin.manageAccounts()
"""

import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

from ui.widgets import BG, HEADER_BG, WHITE, clear_table, make_header, make_table


class AdminScreen(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        self.admin = app.current_user                 # an Admin object

        header = make_header(self, "ADMIN DASHBOARD")
        ttk.Button(header, text="Logout", command=app.logout).pack(side="right")
        tk.Label(header, text="Logged in as " + self.admin.username, bg=HEADER_BG,
                 fg=WHITE).pack(side="right", padx=15)

        self.stats_label = tk.Label(self, bg=BG, font=("Arial", 11, "bold"), anchor="w")
        self.stats_label.pack(fill="x", padx=15, pady=12)

        tk.Label(self, text="Manage Accounts", bg=BG,
                 font=("Arial", 11, "bold")).pack(anchor="w", padx=15)
        frame, self.table = make_table(self, ("ID", "Username", "Email", "Role", "Status"),
                                       (60, 180, 280, 100, 100), height=12)
        frame.pack(fill="both", expand=True, padx=15, pady=6)

        buttons = tk.Frame(self, bg=BG)
        buttons.pack(pady=10)
        ttk.Button(buttons, text="Enable / Disable Selected",
                   command=self.toggle_selected).pack(side="left", padx=5)
        ttk.Button(buttons, text="Delete Selected",
                   command=self.delete_selected).pack(side="left", padx=5)
        ttk.Button(buttons, text="Refresh", command=self.refresh).pack(side="left", padx=5)

        self.refresh()

    def refresh(self):
        stats = self.admin.view_dashboard()
        self.stats_label.config(
            text="Regular users: " + str(stats["regular_users"]) +
                 "     Active accounts: " + str(stats["active_accounts"]) +
                 "     Transactions: " + str(stats["transactions"]) +
                 "     Audit reports: " + str(stats["audit_reports"]))
        clear_table(self.table)
        for user in self.admin.manage_accounts():
            self.table.insert("", "end", iid=str(user["user_id"]), values=(
                user["user_id"], user["username"], user["email"], user["role"],
                "Active" if user["is_active"] else "Disabled"))

    def get_selected_id(self):
        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("Select an Account", "Please click an account first.")
            return None
        return int(selected[0])

    def toggle_selected(self):
        user_id = self.get_selected_id()
        if user_id is None:
            return
        is_active = self.table.item(str(user_id))["values"][4] == "Active"
        try:
            self.admin.set_account_active(user_id, not is_active)
        except ValueError as error:
            messagebox.showerror("Not Allowed", str(error))
        except sqlite3.Error:
            messagebox.showerror("Database Error", "Could not change the account.")
        self.refresh()

    def delete_selected(self):
        user_id = self.get_selected_id()
        if user_id is None:
            return
        if not messagebox.askyesno("Confirm Delete",
                                   "Delete this account and ALL of its data?"):
            return
        try:
            self.admin.delete_account(user_id)
        except ValueError as error:
            messagebox.showerror("Not Allowed", str(error))
        except sqlite3.Error:
            messagebox.showerror("Database Error", "Could not delete the account.")
        self.refresh()
