"""
audit.py  -  Audit reports for the Auditor role.

What it does : creates a system-wide audit report (one line per user with
               their number of transactions and totals), lists old audit
               reports and saves one to a CSV file.
Why needed   : the Auditor actor has "Generate Audit Report" and
               "Download Audit Report" in the use case diagram.
Talks to     : database.py, models.py (Auditor and AuditReport classes),
               ui/auditor.py (the Auditor screen).
Diagram      : Use case -> Generate Audit Report, Download Audit Report
               Class -> Auditor.generateAuditReport(), downloadAuditReport(),
                        AuditReport (auditReportId, generatedDate, status)
Note         : auditors only see totals per user, never the descriptions.
"""

import csv
import io
from datetime import datetime

from database import execute, insert, query


def _build_audit_content():
    """Return the audit report as CSV text."""
    rows = query("""
        SELECT u.user_id, u.username, u.email, u.is_active,
               COUNT(t.transaction_id) AS transactions,
               COALESCE(SUM(CASE WHEN t.type = 'Income'  THEN t.amount END), 0) AS income,
               COALESCE(SUM(CASE WHEN t.type = 'Expense' THEN t.amount END), 0) AS expenses
        FROM users u LEFT JOIN transactions t ON t.user_id = u.user_id
        WHERE u.role = 'user'
        GROUP BY u.user_id
        ORDER BY u.user_id""")

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["User ID", "Username", "Email", "Active", "Transactions",
                     "Total Income", "Total Expenses", "Balance"])
    for r in rows:
        writer.writerow([r["user_id"], r["username"], r["email"],
                         "Yes" if r["is_active"] else "No", r["transactions"],
                         round(r["income"], 2), round(r["expenses"], 2),
                         round(r["income"] - r["expenses"], 2)])
    return buffer.getvalue()


def generate_audit_report(auditor_id):
    """Create and save a new audit report. Returns its audit_report_id."""
    return insert(
        "INSERT INTO audit_reports (auditor_id, generated_date, status, content) "
        "VALUES (?, ?, 'Generated', ?)",
        (auditor_id, datetime.now().strftime("%d-%m-%Y %H:%M"), _build_audit_content()))


def get_audit_reports():
    """All audit reports, newest first (without the big content column)."""
    return query("SELECT audit_report_id, auditor_id, generated_date, status "
                 "FROM audit_reports ORDER BY audit_report_id DESC")


def download_audit_report(report_id, filepath):
    """Write the audit report to a CSV file and mark it as Downloaded."""
    rows = query("SELECT content FROM audit_reports WHERE audit_report_id = ?",
                 (report_id,))
    if not rows:
        raise ValueError("Audit report not found.")
    with open(filepath, "w", newline="", encoding="utf-8") as file:
        file.write(rows[0]["content"])
    execute("UPDATE audit_reports SET status = 'Downloaded' WHERE audit_report_id = ?",
            (report_id,))
    return filepath
