"""
ui/login.py  -  Login screen and Register window.

What it does : asks for email + password, shows an error when they are wrong,
               and lets a new person create an account.
Why needed   : the flowchart starts with "User Logged In?" -> Enter
               Credentials -> Authentication Successful?
Talks to     : models.py (login_user, RegularUser.register), main.py (App).
Diagram      : Use case -> Register Account, Login
               State diagram -> Idle > Login > Authenticating
               Flowchart -> Enter Credentials / Show Error Message
"""

import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

import models
from ui.widgets import BG, HEADER_BG, WHITE, center_window


class LoginScreen(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        self.email_var = tk.StringVar()
        self.password_var = tk.StringVar()

        card = tk.Frame(self, bg=WHITE, padx=35, pady=25, bd=2, relief="groove")
        card.place(relx=0.5, rely=0.45, anchor="center")

        tk.Label(card, text="PERSONAL EXPENSE TRACKER", font=("Arial", 18, "bold"),
                 bg=WHITE, fg=HEADER_BG).grid(row=0, column=0, columnspan=2, pady=(0, 4))
        tk.Label(card, text="Please login to continue", bg=WHITE,
                 fg="gray").grid(row=1, column=0, columnspan=2, pady=(0, 15))

        tk.Label(card, text="Email:", bg=WHITE).grid(row=2, column=0, sticky="e", pady=5)
        email_entry = ttk.Entry(card, textvariable=self.email_var, width=30)
        email_entry.grid(row=2, column=1, pady=5, padx=(8, 0))

        tk.Label(card, text="Password:", bg=WHITE).grid(row=3, column=0, sticky="e", pady=5)
        password_entry = ttk.Entry(card, textvariable=self.password_var, width=30, show="*")
        password_entry.grid(row=3, column=1, pady=5, padx=(8, 0))

        buttons = tk.Frame(card, bg=WHITE)
        buttons.grid(row=4, column=0, columnspan=2, pady=(15, 5))
        ttk.Button(buttons, text="Login", width=10, command=self.login).pack(side="left", padx=4)
        ttk.Button(buttons, text="Register", width=10, command=self.open_register).pack(side="left", padx=4)
        ttk.Button(buttons, text="Exit", width=10, command=app.destroy).pack(side="left", padx=4)

        tk.Label(card, bg=WHITE, fg="gray", justify="left", font=("Arial", 9),
                 text="Demo accounts:\n"
                      "User    : demo@example.com / demo123\n"
                      "Admin   : admin@example.com / admin123\n"
                      "Auditor : auditor@example.com / audit123"
                 ).grid(row=5, column=0, columnspan=2, pady=(12, 0))

        email_entry.focus_set()
        password_entry.bind("<Return>", lambda event: self.login())   # Enter key = Login

    def login(self):
        email = self.email_var.get().strip()
        password = self.password_var.get()
        if email == "" or password == "":
            messagebox.showerror("Login Failed", "Please enter your email and password.")
            return
        try:
            user = models.login_user(email, password)
        except ValueError as error:                      # wrong password, disabled...
            messagebox.showerror("Login Failed", str(error))
            self.password_var.set("")
            return
        except sqlite3.Error:
            messagebox.showerror("Database Error", "Could not read the database.")
            return
        self.app.show_home(user)                          # Authentication successful

    def open_register(self):
        RegisterWindow(self, self.email_var.set)


class RegisterWindow(tk.Toplevel):
    """Small window used to create a new (regular user) account."""

    def __init__(self, parent, on_registered):
        super().__init__(parent)
        self.title("Register Account")
        self.resizable(False, False)
        center_window(self, 380, 290)
        self.on_registered = on_registered               # fills the email on the login screen

        self.username_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.confirm_var = tk.StringVar()

        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)
        rows = [("Username:", self.username_var, ""), ("Email:", self.email_var, ""),
                ("Password:", self.password_var, "*"), ("Confirm password:", self.confirm_var, "*")]
        for number, (label, variable, hide) in enumerate(rows):
            ttk.Label(frame, text=label).grid(row=number, column=0, sticky="e", pady=6)
            ttk.Entry(frame, textvariable=variable, width=26, show=hide).grid(
                row=number, column=1, pady=6, padx=(8, 0))

        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, columnspan=2, pady=(15, 0))
        ttk.Button(buttons, text="Register", command=self.register).pack(side="left", padx=5)
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left", padx=5)

    def register(self):
        if self.password_var.get() != self.confirm_var.get():
            messagebox.showerror("Register", "The two passwords do not match.", parent=self)
            return
        # Create a RegularUser object; the plain password is hashed inside register()
        new_user = models.RegularUser(None, self.username_var.get(), self.email_var.get(),
                                      self.password_var.get())
        try:
            new_user.register()
        except ValueError as error:                       # invalid input / duplicate email
            messagebox.showerror("Register", str(error), parent=self)
            return
        except sqlite3.Error:
            messagebox.showerror("Database Error", "Could not save the account.", parent=self)
            return
        messagebox.showinfo("Registration Successful",
                            "Your account was created. You can now login.", parent=self)
        self.on_registered(new_user.email.strip().lower())
        self.destroy()
