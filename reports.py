"""
reports.py  -  Summary / Category / Trend reports, charts and file export.

What it does : builds the three report types from the flowchart, draws simple
               Matplotlib charts, and exports reports (PDF / CSV) and the
               raw transaction list (CSV).
Why needed   : the diagrams contain "View Report", "Generate Report",
               "Export Data", "Reports & Analytics", "4.0 Generate Reports".
Talks to     : transactions.py (totals), settings.py (currency), database.py,
               validation.py, models.py (Report class), ui/reports.py (shows it).
Diagram      : Use case -> View Report <<include>> Generate Report, Export Data
               Flowchart -> Generate Reports > Summary / Category Breakdown /
                            Trend Analysis > Display Report & Charts > Export
               DFD -> 4.0 Generate Reports (Report Request -> Financial Report)
               Class -> Report (reportId, generatedDate, generateReport())
"""

import csv
from datetime import datetime

from database import insert, query
from settings import format_money, get_settings
from transactions import get_total_expenses, get_total_income, get_transactions
from validation import to_display_date, validate_date

REPORT_TYPES = ["Summary", "Category Breakdown", "Trend Analysis"]


# ---------------------------------------------------------------------------
# 1. The numbers
# ---------------------------------------------------------------------------
def get_summary(user_id, start=None, end=None):
    """Total income, total expenses and balance (start/end are YYYY-MM-DD)."""
    income = get_total_income(user_id, start, end)
    expenses = get_total_expenses(user_id, start, end)
    return {"total_income": income, "total_expenses": expenses,
            "balance": round(income - expenses, 2)}


def get_category_breakdown(user_id, start=None, end=None):
    """Expenses grouped by category, biggest first."""
    sql = ("SELECT category, SUM(amount) AS total FROM transactions "
           "WHERE user_id = ? AND type = 'Expense'")
    params = [user_id]
    if start:
        sql += " AND date >= ?"
        params.append(start)
    if end:
        sql += " AND date <= ?"
        params.append(end)
    sql += " GROUP BY category ORDER BY total DESC"
    rows = query(sql, params)

    grand_total = sum(row["total"] for row in rows)
    result = []
    for row in rows:
        percent = row["total"] / grand_total * 100 if grand_total else 0
        result.append({"category": row["category"],
                       "total": round(row["total"], 2),
                       "percent": round(percent, 1)})
    return result


def get_monthly_trend(user_id, months=6):
    """Income and expenses for each of the last few months (oldest first)."""
    rows = query("SELECT substr(date, 1, 7) AS month, type, SUM(amount) AS total "
                 "FROM transactions WHERE user_id = ? GROUP BY month, type "
                 "ORDER BY month", (user_id,))
    data = {}
    for row in rows:
        month = data.setdefault(row["month"], {"month": row["month"],
                                               "income": 0, "expenses": 0})
        if row["type"] == "Income":
            month["income"] = round(row["total"], 2)
        else:
            month["expenses"] = round(row["total"], 2)
    return [data[m] for m in sorted(data)][-months:]


# ---------------------------------------------------------------------------
# 2. Generate a report (returns a dictionary the GUI can display)
# ---------------------------------------------------------------------------
def generate_report(user_id, report_type, start_text="", end_text=""):
    """Build a report. start_text / end_text are optional (DD-MM-YYYY)."""
    if report_type not in REPORT_TYPES:
        raise ValueError("Please select a report type.")
    start = validate_date(start_text) if start_text.strip() else None
    end = validate_date(end_text) if end_text.strip() else None
    if start and end and start > end:
        raise ValueError("The 'From' date must be before the 'To' date.")

    report = {
        "type": report_type,
        "generated_date": datetime.now().strftime("%d-%m-%Y"),
        "period": "All dates" if not (start or end) else
                  (to_display_date(start) if start else "Beginning") + " to " +
                  (to_display_date(end) if end else "Today"),
        "currency": get_settings(user_id)["currency"],
        "summary": get_summary(user_id, start, end),
        "categories": get_category_breakdown(user_id, start, end),
        "trend": get_monthly_trend(user_id) if report_type == "Trend Analysis" else [],
    }
    # remember that this report was generated (Report table)
    insert("INSERT INTO reports (user_id, report_type, generated_date) VALUES (?, ?, ?)",
           (user_id, report_type, datetime.now().strftime("%Y-%m-%d")))
    return report


def report_to_text(report):
    """Turn the report dictionary into readable text for the screen / PDF."""
    cur = report["currency"]
    s = report["summary"]
    lines = ["=== " + report["type"].upper() + " REPORT ===",
             "Generated : " + report["generated_date"],
             "Period    : " + report["period"],
             "",
             "Total Income   : " + format_money(s["total_income"], cur),
             "Total Expenses : " + format_money(s["total_expenses"], cur),
             "Balance        : " + format_money(s["balance"], cur),
             "",
             "Category-wise expenses"]
    if not report["categories"]:
        lines.append("  (no expenses found)")
    for c in report["categories"]:
        lines.append("  " + c["category"].ljust(15) +
                     format_money(c["total"], cur).rjust(14) +
                     (str(c["percent"]) + "%").rjust(8))
    if report["type"] == "Trend Analysis":
        lines += ["", "Monthly trend"]
        if not report["trend"]:
            lines.append("  (no data found)")
        for m in report["trend"]:
            lines.append("  " + m["month"] + "  Income " +
                         format_money(m["income"], cur) + "  Expenses " +
                         format_money(m["expenses"], cur))
    return "\n".join(lines)


def get_report_history(user_id):
    """Reports this user generated before (newest first)."""
    return query("SELECT * FROM reports WHERE user_id = ? ORDER BY report_id DESC",
                 (user_id,))


# ---------------------------------------------------------------------------
# 3. Charts (Matplotlib "Figure" objects: used on screen AND inside the PDF)
# ---------------------------------------------------------------------------
def make_figure(report):
    """Return a Matplotlib figure that matches the report type."""
    from matplotlib.figure import Figure      # imported here so tests without
                                              # charts still work quickly
    fig = Figure(figsize=(5, 4), dpi=100)
    ax = fig.add_subplot(111)
    cur = report["currency"]

    if report["type"] == "Category Breakdown":
        cats = report["categories"]
        if cats:
            ax.pie([c["total"] for c in cats], labels=[c["category"] for c in cats],
                   autopct="%1.0f%%")
            ax.set_title("Expenses by Category")
        else:
            _no_data(ax)

    elif report["type"] == "Trend Analysis":
        trend = report["trend"]
        if trend:
            positions = list(range(len(trend)))
            ax.bar([p - 0.2 for p in positions], [m["income"] for m in trend],
                   width=0.4, label="Income", color="#43a047")
            ax.bar([p + 0.2 for p in positions], [m["expenses"] for m in trend],
                   width=0.4, label="Expenses", color="#e53935")
            ax.set_xticks(positions)
            ax.set_xticklabels([m["month"] for m in trend], fontsize=8)
            ax.set_ylabel("Amount (" + cur + ")")
            ax.set_title("Monthly Income vs Expenses")
            ax.legend()
        else:
            _no_data(ax)

    else:   # Summary
        s = report["summary"]
        ax.bar(["Income", "Expenses", "Balance"],
               [s["total_income"], s["total_expenses"], s["balance"]],
               color=["#43a047", "#e53935", "#1e88e5"])
        ax.set_ylabel("Amount (" + cur + ")")
        ax.set_title("Income, Expenses and Balance")

    fig.tight_layout()
    return fig


def _no_data(ax):
    ax.text(0.5, 0.5, "No data to show", ha="center", va="center")
    ax.axis("off")


# ---------------------------------------------------------------------------
# 4. Export (Flowchart: Export as PDF/CSV.  Use case: Export Data)
# ---------------------------------------------------------------------------
def export_transactions_csv(user_id, filepath):
    """Save ALL of the user's transactions to a CSV file (Export Data)."""
    with open(filepath, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Date", "Type", "Category", "Description", "Amount"])
        for t in get_transactions(user_id):
            writer.writerow([to_display_date(t["date"]), t["type"], t["category"],
                             t["description"], t["amount"]])
    return filepath


def export_report_csv(report, filepath):
    """Save a generated report to a CSV file."""
    s = report["summary"]
    with open(filepath, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Report", report["type"]])
        writer.writerow(["Generated", report["generated_date"]])
        writer.writerow(["Period", report["period"]])
        writer.writerow([])
        writer.writerow(["Total Income", s["total_income"]])
        writer.writerow(["Total Expenses", s["total_expenses"]])
        writer.writerow(["Balance", s["balance"]])
        writer.writerow([])
        writer.writerow(["Category", "Amount", "Percent"])
        for c in report["categories"]:
            writer.writerow([c["category"], c["total"], c["percent"]])
        if report["trend"]:
            writer.writerow([])
            writer.writerow(["Month", "Income", "Expenses"])
            for m in report["trend"]:
                writer.writerow([m["month"], m["income"], m["expenses"]])
    return filepath


def export_report_pdf(report, filepath):
    """Save a generated report (text page + chart page) as a PDF file."""
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.figure import Figure

    text_page = Figure(figsize=(8.27, 11.69))          # A4 size in inches
    text_page.text(0.08, 0.95, report_to_text(report), va="top",
                   family="monospace", fontsize=9)
    with PdfPages(filepath) as pdf:
        pdf.savefig(text_page)
        pdf.savefig(make_figure(report))
    return filepath
