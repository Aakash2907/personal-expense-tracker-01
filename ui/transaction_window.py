"""
ui/transaction_window.py  -  Add/Edit form and the transaction list.

What it does : TransactionForm adds a new expense/income or edits an existing
               one.  TransactionListWindow shows all transactions, lets the
               user filter/search them and edit or delete the selected one.
Why needed   : Add Expense, Add Income, View Expenses, Edit and Delete in the
               use case diagram and flowchart.
Talks to     : models.py (Transaction class), transactions.py (get list),
               budget.py (alert after saving), validation.py, database.py
               (category lists), dashboard.py (refresh callback).
Diagram      : Flowchart -> Open Add Expense Form > Enter Details > Validate
               Input? > Save to Database > Show Success Message
               View Expenses > Apply Filters? > Select Option (Edit / Delete /
               Back) > Confirm Deletion? > Remove from Database
               Sequence -> Add New Transaction > Save > Show Updated Transactions
"""

import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

from budget import check_budget_alert
from database import ALL_CATEGORIES, EXPENSE_CATEGORIES, INCOME_CATEGORIES
from models import Transaction
from settings import format_money, get_settings
from transactions import get_transaction, get_transactions
from ui.widgets import GREEN, RED, center_window, clear_table, make_table
from validation import to_display_date, today_display


# ===========================================================================
# Add / Edit form
# ===========================================================================
class TransactionForm(tk.Toplevel):
    def __init__(self, parent, user, type_, on_saved, transaction=None):
        """type_ = "Expense" or "Income".  If 'transaction' (a dictionary from
        the database) is given, the form edits it instead of adding a new one."""
        super().__init__(parent)
        self.user = user
        self.on_saved = on_saved
        self.transaction = transaction
        self.editing = transaction is not None

        self.title("Edit Transaction" if self.editing else "Add " + type_)
        self.resizable(False, False)
        center_window(self, 400, 330)

        self.type_var = tk.StringVar(value=type_)
        self.amount_var = tk.StringVar()
        self.category_var = tk.StringVar()
        self.description_var = tk.StringVar()
        self.date_var = tk.StringVar(value=today_display())
        if self.editing:                                   # fill the form
            self.amount_var.set(format(transaction["amount"], ".2f"))
            self.category_var.set(transaction["category"])
            self.description_var.set(transaction["description"])
            self.date_var.set(to_display_date(transaction["date"]))

        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Type:").grid(row=0, column=0, sticky="e", pady=6)
        type_box = ttk.Combobox(frame, textvariable=self.type_var, width=24,
                                values=["Expense", "Income"],
                                state="readonly" if self.editing else "disabled")
        type_box.grid(row=0, column=1, pady=6, padx=(8, 0))
        type_box.bind("<<ComboboxSelected>>", lambda event: self.update_categories())

        ttk.Label(frame, text="Amount:").grid(row=1, column=0, sticky="e", pady=6)
        ttk.Entry(frame, textvariable=self.amount_var, width=27).grid(row=1, column=1, pady=6, padx=(8, 0))

        self.category_label = ttk.Label(frame, text="Category:")
        self.category_label.grid(row=2, column=0, sticky="e", pady=6)
        self.category_box = ttk.Combobox(frame, textvariable=self.category_var,
                                         width=24, state="readonly")
        self.category_box.grid(row=2, column=1, pady=6, padx=(8, 0))

        ttk.Label(frame, text="Description:").grid(row=3, column=0, sticky="e", pady=6)
        ttk.Entry(frame, textvariable=self.description_var, width=27).grid(row=3, column=1, pady=6, padx=(8, 0))

        ttk.Label(frame, text="Date (DD-MM-YYYY):").grid(row=4, column=0, sticky="e", pady=6)
        ttk.Entry(frame, textvariable=self.date_var, width=27).grid(row=4, column=1, pady=6, padx=(8, 0))

        buttons = ttk.Frame(frame)
        buttons.grid(row=5, column=0, columnspan=2, pady=(18, 0))
        ttk.Button(buttons, text="Save", command=self.save).pack(side="left", padx=5)
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left", padx=5)

        self.update_categories()

    def update_categories(self):
        """Expenses use Category, income uses Source (different lists)."""
        if self.type_var.get() == "Expense":
            names = EXPENSE_CATEGORIES
            self.category_label.config(text="Category:")
        else:
            names = INCOME_CATEGORIES
            self.category_label.config(text="Source:")
        self.category_box["values"] = names
        if self.category_var.get() not in names:
            # new form: choose the first one; editing after a type change: ask again
            self.category_var.set("" if self.editing else names[0])

    def save(self):
        """Validate -> save to SQLite -> show message -> refresh the dashboard."""
        transaction_id = self.transaction["transaction_id"] if self.editing else None
        transaction = Transaction(self.user.user_id, self.type_var.get(),
                                  self.amount_var.get(), self.category_var.get(),
                                  self.description_var.get(), self.date_var.get(),
                                  transaction_id)
        try:
            if self.editing:
                transaction.edit()
            else:
                transaction.add()
        except ValueError as error:                        # "Validate Input?" -> Invalid
            messagebox.showerror("Invalid Input", str(error), parent=self)
            return                                         # back to the form
        except sqlite3.Error:
            messagebox.showerror("Database Error",
                                 "The transaction could not be saved. Please try again.",
                                 parent=self)
            return

        word = "updated" if self.editing else "saved"
        messagebox.showinfo("Success", transaction.type + " " + word + " successfully.",
                            parent=self)
        if transaction.type == "Expense":                  # Notification Component
            alert = check_budget_alert(self.user.user_id)
            if alert:
                messagebox.showwarning("Budget Alert", alert, parent=self)
        self.on_saved()                                    # Show Updated Transactions
        self.destroy()


# ===========================================================================
# Transaction list with search / filter, edit and delete
# ===========================================================================
class TransactionListWindow(tk.Toplevel):
    def __init__(self, parent, user, on_change):
        super().__init__(parent)
        self.user = user
        self.on_change = on_change                         # refreshes the dashboard
        self.title("View Transactions")
        center_window(self, 900, 560)

        self.type_var = tk.StringVar(value="All")
        self.category_var = tk.StringVar(value="All")
        self.from_var = tk.StringVar()
        self.to_var = tk.StringVar()
        self.search_var = tk.StringVar()

        # ---- filter row ("Apply Filters?" in the flowchart) ----
        filters = ttk.LabelFrame(self, text="Search and Filter", padding=8)
        filters.pack(fill="x", padx=10, pady=8)

        ttk.Label(filters, text="Type:").grid(row=0, column=0, sticky="e")
        ttk.Combobox(filters, textvariable=self.type_var, width=10, state="readonly",
                     values=["All", "Expense", "Income"]).grid(row=0, column=1, padx=(4, 12))
        ttk.Label(filters, text="Category:").grid(row=0, column=2, sticky="e")
        ttk.Combobox(filters, textvariable=self.category_var, width=14, state="readonly",
                     values=["All"] + ALL_CATEGORIES).grid(row=0, column=3, padx=(4, 12))
        ttk.Label(filters, text="From (DD-MM-YYYY):").grid(row=0, column=4, sticky="e")
        ttk.Entry(filters, textvariable=self.from_var, width=12).grid(row=0, column=5, padx=(4, 12))
        ttk.Label(filters, text="To:").grid(row=0, column=6, sticky="e")
        ttk.Entry(filters, textvariable=self.to_var, width=12).grid(row=0, column=7, padx=(4, 0))

        ttk.Label(filters, text="Search:").grid(row=1, column=0, sticky="e", pady=(8, 0))
        search_entry = ttk.Entry(filters, textvariable=self.search_var, width=30)
        search_entry.grid(row=1, column=1, columnspan=3, sticky="w", padx=(4, 12), pady=(8, 0))
        search_entry.bind("<Return>", lambda event: self.load_transactions())
        ttk.Button(filters, text="Apply Filters", command=self.load_transactions).grid(
            row=1, column=4, columnspan=2, pady=(8, 0))
        ttk.Button(filters, text="Clear", command=self.clear_filters).grid(
            row=1, column=6, columnspan=2, pady=(8, 0))

        # ---- table ----
        frame, self.table = make_table(
            self, ("Date", "Type", "Category", "Description", "Amount"),
            (110, 90, 140, 340, 130), height=14)
        frame.pack(fill="both", expand=True, padx=10)
        self.table.tag_configure("Expense", foreground=RED)
        self.table.tag_configure("Income", foreground=GREEN)
        self.table.bind("<Double-1>", lambda event: self.edit_selected())

        self.count_label = ttk.Label(self, text="")
        self.count_label.pack(anchor="w", padx=10, pady=4)

        # ---- buttons ("Select Option": Edit / Delete / Back) ----
        buttons = ttk.Frame(self)
        buttons.pack(pady=(0, 10))
        ttk.Button(buttons, text="Edit Selected", command=self.edit_selected).pack(side="left", padx=5)
        ttk.Button(buttons, text="Delete Selected", command=self.delete_selected).pack(side="left", padx=5)
        ttk.Button(buttons, text="Back", command=self.destroy).pack(side="left", padx=5)

        self.load_transactions()

    def load_transactions(self):
        """Read the (filtered) transactions from SQLite and show them."""
        try:
            rows = get_transactions(
                self.user.user_id, type_=self.type_var.get(),
                category=self.category_var.get(), date_from=self.from_var.get(),
                date_to=self.to_var.get(), search=self.search_var.get())
        except ValueError as error:                        # e.g. bad date in the filter
            messagebox.showerror("Invalid Filter", str(error), parent=self)
            return
        currency = get_settings(self.user.user_id)["currency"]

        clear_table(self.table)
        for t in rows:
            # iid = the transaction id, so we always know which row is which
            self.table.insert("", "end", iid=str(t["transaction_id"]), tags=(t["type"],),
                              values=(to_display_date(t["date"]), t["type"], t["category"],
                                      t["description"], format_money(t["amount"], currency)))
        self.count_label.config(text="Showing " + str(len(rows)) + " transaction(s)")

    def clear_filters(self):
        self.type_var.set("All")
        self.category_var.set("All")
        self.from_var.set("")
        self.to_var.set("")
        self.search_var.set("")
        self.load_transactions()

    def get_selected_id(self):
        """Return the selected transaction id, or None (with a message)."""
        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("Select a Transaction",
                                   "Please click a transaction in the table first.",
                                   parent=self)
            return None
        return int(selected[0])

    def after_change(self):
        """Called after an edit or delete: refresh this list and the dashboard."""
        self.load_transactions()
        self.on_change()

    def edit_selected(self):
        transaction_id = self.get_selected_id()
        if transaction_id is None:
            return
        transaction = get_transaction(self.user.user_id, transaction_id)
        if transaction is None:
            messagebox.showerror("Not Found", "This transaction no longer exists.", parent=self)
            self.load_transactions()
            return
        TransactionForm(self, self.user, transaction["type"], self.after_change, transaction)

    def delete_selected(self):
        transaction_id = self.get_selected_id()
        if transaction_id is None:
            return
        # "Confirm Deletion?" -> No: go back to the list
        if not messagebox.askyesno("Confirm Delete",
                                   "Are you sure you want to delete this transaction?",
                                   parent=self):
            return
        try:
            Transaction(self.user.user_id, transaction_id=transaction_id).delete()
        except ValueError as error:
            messagebox.showerror("Delete Failed", str(error), parent=self)
        except sqlite3.Error:
            messagebox.showerror("Database Error", "Could not delete the transaction.",
                                 parent=self)
        else:
            messagebox.showinfo("Deleted", "Transaction deleted successfully.", parent=self)
        self.after_change()
