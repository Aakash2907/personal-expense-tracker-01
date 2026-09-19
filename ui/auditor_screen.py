"""
ui/auditor_screen.py  -  Screen for the Auditor role.

What it does : the auditor can generate a new audit report and download any
               audit report as a CSV file.
Why needed   : Auditor actor -> "Generate Audit Report", "Download Audit Report".
Talks to     : models.py (Auditor object), audit.py (list of reports),
               main.py (logout).
Diagram      : Use case -> Generate Audit Report, Download Audit Report
               Class -> Auditor.generateAuditReport(), downloadAuditReport(),
                        AuditReport.download()
"""

import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from audit import get_audit_reports
from ui.widgets import BG, HEADER_BG, WHITE, clear_table, make_header, make_table


class AuditorScreen(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        self.auditor = app.current_user               # an Auditor object

        header = make_header(self, "AUDITOR")
        ttk.Button(header, text="Logout", command=app.logout).pack(side="right")
        tk.Label(header, text="Logged in as " + self.auditor.username, bg=HEADER_BG,
                 fg=WHITE).pack(side="right", padx=15)

        tk.Label(self, bg=BG, anchor="w", justify="left",
                 text="An audit report lists every user with the number of transactions "
                      "and their total income and expenses.\n"
                      "(Auditors see totals only, never the transaction details.)"
                 ).pack(fill="x", padx=15, pady=12)

        buttons = tk.Frame(self, bg=BG)
        buttons.pack(fill="x", padx=15)
        ttk.Button(buttons, text="Generate Audit Report",
                   command=self.generate).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Download Selected Report",
                   command=self.download).pack(side="left")

        frame, self.table = make_table(self, ("Report ID", "Generated", "Status"),
                                       (100, 220, 140), height=12)
        frame.pack(fill="both", expand=True, padx=15, pady=12)
        self.refresh()

    def refresh(self):
        clear_table(self.table)
        for report in get_audit_reports():
            self.table.insert("", "end", iid=str(report["audit_report_id"]), values=(
                report["audit_report_id"], report["generated_date"], report["status"]))

    def generate(self):
        try:
            report = self.auditor.generate_audit_report()
        except sqlite3.Error:
            messagebox.showerror("Database Error", "Could not create the audit report.")
            return
        messagebox.showinfo("Audit Report", "Audit report #" + str(report.audit_report_id) +
                            " was generated.")
        self.refresh()

    def download(self):
        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("Select a Report", "Please click an audit report first.")
            return
        report_id = int(selected[0])
        path = filedialog.asksaveasfilename(
            title="Download Audit Report", defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")], initialfile="audit_report_" + str(report_id) + ".csv")
        if not path:
            return
        try:
            self.auditor.download_audit_report(report_id, path)
        except (OSError, ValueError):
            messagebox.showerror("Download Failed", "The audit report could not be saved.")
            return
        messagebox.showinfo("Download Complete", "Audit report saved to:\n" + path)
        self.refresh()
