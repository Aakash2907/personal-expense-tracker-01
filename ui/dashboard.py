"""
ui/dashboard.py  -  Main screen of a regular user (the "Dashboard").

What it does : shows Total Income, Total Expenses, Balance, budget status,
               budget alerts and the most recent transactions. Buttons open
               the other windows (add, view, reports, settings, export).
Why needed   : the flowchart's "Display Dashboard" -> "Select Action" and the
               state diagram's "MainMenu".
Talks to     : transactions.py, budget.py, settings.py (numbers), the other
               ui/ windows, models.py (user.export_data), main.py (logout).
Diagram      : Flowchart -> Display Dashboard, Select Action
               Sequence -> Open App > Fetch Transactions > Display Transactions
               and after saving: Show Updated Transactions (refresh())
               Use case -> Export Data
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from budget import check_budget_alert, get_budget_status
from settings import format_money, get_settings
from transactions import (get_balance, get_total_expenses, get_total_income,
                          get_transactions)
from ui.reports_window import ReportsWindow
from ui.settings_window import SettingsWindow
from ui.transaction_window import TransactionForm, TransactionListWindow
from ui.widgets import (BG, BLUE, GREEN, HEADER_BG, RED, WHITE, clear_table,
                        make_header, make_table)
from validation import to_display_date


class DashboardScreen(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        self.user = app.current_user
        self.build_screen()
        self.refresh()                        # fetch data and display it

    # ------------------------------------------------------------------
    # Building the screen (done once)
    # ------------------------------------------------------------------
    def build_screen(self):
        header = make_header(self, "PERSONAL EXPENSE TRACKER")
        ttk.Button(header, text="Logout", command=self.app.logout).pack(side="right")
        tk.Label(header, text="Welcome, " + self.user.username, bg=HEADER_BG,
                 fg=WHITE, font=("Arial", 11)).pack(side="right", padx=15)

        # three summary "cards": income, expenses, balance
        cards = tk.Frame(self, bg=BG)
        cards.pack(fill="x", padx=15, pady=(15, 5))
        self.income_label = self.make_card(cards, "Total Income", GREEN)
        self.expense_label = self.make_card(cards, "Total Expenses", RED)
        self.balance_label = self.make_card(cards, "Current Balance", BLUE)

        # budget status + alert
        budget_box = tk.LabelFrame(self, text=" Monthly Budget ", bg=BG, padx=10, pady=6)
        budget_box.pack(fill="x", padx=15, pady=8)
        self.budget_label = tk.Label(budget_box, bg=BG, anchor="w")
        self.budget_label.pack(fill="x")
        self.progress = ttk.Progressbar(budget_box, maximum=100)
        self.progress.pack(fill="x", pady=4)
        self.alert_label = tk.Label(budget_box, bg=BG, fg=RED, anchor="w",
                                    font=("Arial", 10, "bold"))
        self.alert_label.pack(fill="x")

        # action buttons
        buttons = tk.Frame(self, bg=BG)
        buttons.pack(fill="x", padx=15, pady=5)
        actions = [("Add Expense", lambda: self.open_form("Expense")),
                   ("Add Income", lambda: self.open_form("Income")),
                   ("View Transactions", self.open_list),
                   ("Reports", self.open_reports),
                   ("Settings", self.open_settings),
                   ("Export Data", self.export_data)]
        for text, command in actions:
            ttk.Button(buttons, text=text, command=command).pack(side="left", padx=4, ipady=4)

        # recent transactions table
        tk.Label(self, text="Recent Transactions", bg=BG,
                 font=("Arial", 11, "bold")).pack(anchor="w", padx=15, pady=(10, 2))
        frame, self.table = make_table(
            self, ("Date", "Type", "Category", "Description", "Amount"),
            (110, 90, 130, 300, 120), height=8)
        frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.table.tag_configure("Expense", foreground=RED)
        self.table.tag_configure("Income", foreground=GREEN)

    def make_card(self, parent, title, colour):
        """One coloured box with a title and a big number. Returns the number label."""
        card = tk.Frame(parent, bg=WHITE, bd=1, relief="solid", padx=10, pady=8)
        card.pack(side="left", expand=True, fill="x", padx=5)
        tk.Label(card, text=title, bg=WHITE, fg="gray").pack()
        value = tk.Label(card, text="", bg=WHITE, fg=colour, font=("Arial", 18, "bold"))
        value.pack()
        return value

    # ------------------------------------------------------------------
    # Refresh = read the database again and update every label / row
    # ------------------------------------------------------------------
    def refresh(self):
        user_id = self.user.user_id
        currency = get_settings(user_id)["currency"]

        income = get_total_income(user_id)
        expenses = get_total_expenses(user_id)
        balance = get_balance(user_id)              # income - expenses
        self.income_label.config(text=format_money(income, currency))
        self.expense_label.config(text=format_money(expenses, currency))
        self.balance_label.config(text=format_money(balance, currency),
                                  fg=BLUE if balance >= 0 else RED)

        status = get_budget_status(user_id)
        if status is None:
            self.budget_label.config(text="No monthly budget set. Open Settings to set one.")
            self.progress["value"] = 0
        else:
            self.budget_label.config(
                text="Budget " + format_money(status["budget"], currency) +
                     "   |   Spent " + format_money(status["spent"], currency) +
                     "   |   Remaining " + format_money(status["remaining"], currency) +
                     "   (" + str(status["percent"]) + "% used)")
            self.progress["value"] = min(status["percent"], 100)
        self.alert_label.config(text=check_budget_alert(user_id) or "")

        clear_table(self.table)
        for t in get_transactions(user_id, limit=8):
            self.table.insert("", "end", tags=(t["type"],), values=(
                to_display_date(t["date"]), t["type"], t["category"],
                t["description"], format_money(t["amount"], currency)))

    # ------------------------------------------------------------------
    # Button actions
    # ------------------------------------------------------------------
    def open_form(self, type_):
        TransactionForm(self, self.user, type_, self.refresh)

    def open_list(self):
        TransactionListWindow(self, self.user, self.refresh)

    def open_reports(self):
        ReportsWindow(self, self.user)

    def open_settings(self):
        SettingsWindow(self, self.user, self.refresh)

    def export_data(self):
        path = filedialog.asksaveasfilename(
            title="Export Data", defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")], initialfile="my_transactions.csv")
        if not path:                                 # user pressed Cancel
            return
        try:
            self.user.export_data(path)
        except OSError:
            messagebox.showerror("Export Failed", "The file could not be saved.")
            return
        messagebox.showinfo("Export Successful", "Your data was saved to:\n" + path)
