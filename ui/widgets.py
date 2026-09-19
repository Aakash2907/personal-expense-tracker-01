"""
ui/widgets.py  -  Colours and small helper functions shared by all screens.

What it does : keeps the colour names, a window-centering function and a
               function that builds a table (Treeview with a scroll bar).
Why needed   : so every screen looks the same and we do not repeat code.
Talks to     : every file inside the ui/ folder imports it.
Diagram      : Component diagram -> "User Interface".
"""

import tkinter as tk
from tkinter import ttk

BG = "#f4f6f8"          # window background
HEADER_BG = "#2c3e50"   # dark blue header bar
WHITE = "#ffffff"
GREEN = "#27ae60"
RED = "#c0392b"
BLUE = "#2980b9"


def center_window(window, width, height):
    """Open a window in the middle of the screen."""
    x = (window.winfo_screenwidth() - width) // 2
    y = (window.winfo_screenheight() - height) // 3
    window.geometry(str(width) + "x" + str(height) + "+" + str(x) + "+" + str(y))


def make_header(parent, title):
    """Dark bar with a title on the left. Returns the frame so the caller can
    add extra widgets (like a Logout button) on the right."""
    header = tk.Frame(parent, bg=HEADER_BG, padx=15, pady=10)
    header.pack(fill="x")
    tk.Label(header, text=title, font=("Arial", 16, "bold"),
             bg=HEADER_BG, fg=WHITE).pack(side="left")
    return header


def make_table(parent, columns, widths, height=10):
    """Create a table. Returns (frame, treeview).
    The caller packs the frame and inserts rows into the treeview."""
    frame = tk.Frame(parent)
    tree = ttk.Treeview(frame, columns=columns, show="headings", height=height,
                        selectmode="browse")
    for name, width in zip(columns, widths):
        tree.heading(name, text=name)
        tree.column(name, width=width, anchor="e" if name == "Amount" else "w")
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    return frame, tree


def clear_table(tree):
    """Remove all rows from a table."""
    for row in tree.get_children():
        tree.delete(row)
