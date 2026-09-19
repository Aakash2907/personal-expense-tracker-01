"""
ui/settings_window.py  -  Settings: currency, monthly budget, alerts.

What it does : lets the user change the currency symbol, set the monthly
               budget limit and switch budget alerts on or off.
Why needed   : the flowchart's Settings menu (Currency / Budget Limit /
               Notifications) and the use case "Set Budget".
Talks to     : settings.py (save/load), models.py (user.set_budget),
               dashboard.py (refresh after saving).
Diagram      : Flowchart -> Open Settings > Select Setting > Change Currency /
               Set Monthly Budget / Enable-Disable Alerts > Save Settings >
               Show Confirmation
               State diagram -> Settings   Use case -> Set Budget
"""

import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

from budget import get_budget
from settings import CURRENCIES, get_settings, save_settings
from ui.widgets import center_window


class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, user, on_saved):
        super().__init__(parent)
        self.user = user
        self.on_saved = on_saved
        self.title("Settings")
        self.resizable(False, False)
        center_window(self, 420, 250)

        current = get_settings(user.user_id)
        budget = get_budget(user.user_id)
        self.currency_var = tk.StringVar(value=current["currency"])
        self.budget_var = tk.StringVar(value=format(budget["amount"], ".2f") if budget else "")
        self.alerts_var = tk.BooleanVar(value=current["alerts_enabled"])

        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Currency:").grid(row=0, column=0, sticky="e", pady=8)
        ttk.Combobox(frame, textvariable=self.currency_var, values=CURRENCIES,
                     width=8, state="readonly").grid(row=0, column=1, sticky="w", padx=(8, 0))

        ttk.Label(frame, text="Monthly budget limit:").grid(row=1, column=0, sticky="e", pady=8)
        ttk.Entry(frame, textvariable=self.budget_var, width=14).grid(
            row=1, column=1, sticky="w", padx=(8, 0))

        ttk.Checkbutton(frame, text="Enable budget alerts (notifications)",
                        variable=self.alerts_var).grid(row=2, column=0, columnspan=2,
                                                       sticky="w", pady=8)

        buttons = ttk.Frame(frame)
        buttons.grid(row=3, column=0, columnspan=2, pady=(15, 0))
        ttk.Button(buttons, text="Save Settings", command=self.save).pack(side="left", padx=5)
        ttk.Button(buttons, text="Back", command=self.destroy).pack(side="left", padx=5)

    def save(self):
        budget_text = self.budget_var.get().strip()
        try:
            if budget_text != "":                    # blank = leave the budget alone
                self.user.set_budget(budget_text)    # validates the amount
            save_settings(self.user.user_id, self.currency_var.get(),
                          self.alerts_var.get())
        except ValueError as error:
            messagebox.showerror("Invalid Input", str(error), parent=self)
            return
        except sqlite3.Error:
            messagebox.showerror("Database Error", "Could not save the settings.", parent=self)
            return
        messagebox.showinfo("Settings Saved", "Your settings were saved.", parent=self)
        self.on_saved()                              # dashboard shows the new values
        self.destroy()
