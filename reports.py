"""
reports.py

Summary, category and trend reports,
charts and CSV/PDF export.
"""

import csv
from datetime import datetime

from database import (
    insert,
    query,
)

from settings import (
    format_money,
    get_settings,
)

from transactions import (
    get_total_expenses,
    get_total_income,
    get_transactions,
)

from validation import (
    to_display_date,
    validate_date_range,
)


REPORT_TYPES = [
    "Summary",
    "Category Breakdown",
    "Trend Analysis",
]


def get_summary(
    user_id,
    start=None,
    end=None,
):
    income = get_total_income(
        user_id,
        start,
        end,
    )

    expenses = get_total_expenses(
        user_id,
        start,
        end,
    )

    return {
        "total_income": income,
        "total_expenses": expenses,
        "balance": round(
            income - expenses,
            2,
        ),
    }


def get_category_breakdown(
    user_id,
    start=None,
    end=None,
):
    sql = """
        SELECT
            category,
            SUM(amount) AS total
        FROM transactions
        WHERE user_id = ?
          AND type = 'Expense'
    """

    params = [user_id]

    if start:
        sql += " AND date >= ?"
        params.append(start)

    if end:
        sql += " AND date <= ?"
        params.append(end)

    sql += """
        GROUP BY category
        ORDER BY total DESC
    """

    rows = query(
        sql,
        params,
    )

    grand_total = sum(
        row["total"]
        for row in rows
    )

    result = []

    for row in rows:

        percent = (
            row["total"]
            / grand_total
            * 100
            if grand_total
            else 0
        )

        result.append(
            {
                "category": row["category"],
                "total": round(
                    row["total"],
                    2,
                ),
                "percent": round(
                    percent,
                    1,
                ),
            }
        )

    return result


def get_monthly_trend(
    user_id,
    months=6,
    start=None,
    end=None,
):
    """
    Return monthly income/expense totals.

    start/end are YYYY-MM-DD.
    """

    sql = """
        SELECT
            substr(date, 1, 7) AS month,
            type,
            SUM(amount) AS total
        FROM transactions
        WHERE user_id = ?
    """

    params = [user_id]

    if start:
        sql += " AND date >= ?"
        params.append(start)

    if end:
        sql += " AND date <= ?"
        params.append(end)

    sql += """
        GROUP BY month, type
        ORDER BY month
    """

    rows = query(
        sql,
        params,
    )

    data = {}

    for row in rows:

        month = data.setdefault(
            row["month"],
            {
                "month": row["month"],
                "income": 0,
                "expenses": 0,
            },
        )

        if row["type"] == "Income":
            month["income"] = round(
                row["total"],
                2,
            )

        else:
            month["expenses"] = round(
                row["total"],
                2,
            )

    result = [
        data[key]
        for key in sorted(data)
    ]

    if months:
        result = result[-months:]

    return result


def generate_report(
    user_id,
    report_type,
    start_text="",
    end_text="",
):
    """Generate a complete report."""

    if report_type not in REPORT_TYPES:
        raise ValueError(
            "Please select a report type."
        )

    start, end = validate_date_range(
        start_text,
        end_text,
    )

    if not start and not end:
        period = "All dates"

    else:

        period = (
            (
                to_display_date(start)
                if start
                else "Beginning"
            )
            + " to "
            + (
                to_display_date(end)
                if end
                else "Today"
            )
        )

    report = {
        "type": report_type,

        "generated_date":
            datetime.now().strftime(
                "%d-%m-%Y"
            ),

        "period": period,

        "currency":
            get_settings(user_id)[
                "currency"
            ],

        "summary":
            get_summary(
                user_id,
                start,
                end,
            ),

        "categories":
            get_category_breakdown(
                user_id,
                start,
                end,
            ),

        "trend":
            (
                get_monthly_trend(
                    user_id,
                    start=start,
                    end=end,
                )
                if report_type
                == "Trend Analysis"
                else []
            ),
    }

    insert(
        """
        INSERT INTO reports
        (
            user_id,
            report_type,
            generated_date
        )
        VALUES (?, ?, ?)
        """,
        (
            user_id,
            report_type,
            datetime.now().strftime(
                "%Y-%m-%d"
            ),
        ),
    )

    return report


def report_to_text(report):
    """Convert report to readable text."""

    currency = report[
        "currency"
    ]

    summary = report[
        "summary"
    ]

    lines = [
        "=== "
        + report["type"].upper()
        + " REPORT ===",

        "Generated : "
        + report["generated_date"],

        "Period    : "
        + report["period"],

        "",

        "Total Income   : "
        + format_money(
            summary["total_income"],
            currency,
        ),

        "Total Expenses : "
        + format_money(
            summary["total_expenses"],
            currency,
        ),

        "Balance        : "
        + format_money(
            summary["balance"],
            currency,
        ),

        "",

        "Category-wise expenses",
    ]

    if not report[
        "categories"
    ]:
        lines.append(
            "  (no expenses found)"
        )

    for category in report[
        "categories"
    ]:

        lines.append(
            "  "
            + category[
                "category"
            ].ljust(15)
            + format_money(
                category["total"],
                currency,
            ).rjust(14)
            + (
                str(
                    category[
                        "percent"
                    ]
                )
                + "%"
            ).rjust(8)
        )

    if report[
        "type"
    ] == "Trend Analysis":

        lines += [
            "",
            "Monthly trend",
        ]

        if not report[
            "trend"
        ]:
            lines.append(
                "  (no data found)"
            )

        for month in report[
            "trend"
        ]:

            lines.append(
                "  "
                + month["month"]
                + "  Income "
                + format_money(
                    month["income"],
                    currency,
                )
                + "  Expenses "
                + format_money(
                    month["expenses"],
                    currency,
                )
            )

    return "\n".join(lines)


def get_report_history(user_id):
    """Return reports generated by this user."""

    return query(
        """
        SELECT *
        FROM reports
        WHERE user_id = ?
        ORDER BY report_id DESC
        """,
        (user_id,),
    )


def make_figure(report):
    """Create a Matplotlib figure."""

    from matplotlib.figure import Figure

    figure = Figure(
        figsize=(5, 4),
        dpi=100,
    )

    axis = figure.add_subplot(111)

    currency = report[
        "currency"
    ]

    if report[
        "type"
    ] == "Category Breakdown":

        categories = report[
            "categories"
        ]

        if categories:

            axis.pie(
                [
                    item["total"]
                    for item in categories
                ],
                labels=[
                    item["category"]
                    for item in categories
                ],
                autopct="%1.0f%%",
            )

            axis.set_title(
                "Expenses by Category"
            )

        else:
            _no_data(axis)

    elif report[
        "type"
    ] == "Trend Analysis":

        trend = report[
            "trend"
        ]

        if trend:

            positions = list(
                range(len(trend))
            )

            axis.bar(
                [
                    position - 0.2
                    for position in positions
                ],
                [
                    item["income"]
                    for item in trend
                ],
                width=0.4,
                label="Income",
            )

            axis.bar(
                [
                    position + 0.2
                    for position in positions
                ],
                [
                    item["expenses"]
                    for item in trend
                ],
                width=0.4,
                label="Expenses",
            )

            axis.set_xticks(
                positions
            )

            axis.set_xticklabels(
                [
                    item["month"]
                    for item in trend
                ],
                fontsize=8,
            )

            axis.set_ylabel(
                "Amount (" + currency + ")"
            )

            axis.set_title(
                "Monthly Income vs Expenses"
            )

            axis.legend()

        else:
            _no_data(axis)

    else:

        summary = report[
            "summary"
        ]

        axis.bar(
            [
                "Income",
                "Expenses",
                "Balance",
            ],
            [
                summary[
                    "total_income"
                ],
                summary[
                    "total_expenses"
                ],
                summary[
                    "balance"
                ],
            ],
        )

        axis.set_ylabel(
            "Amount (" + currency + ")"
        )

        axis.set_title(
            "Income, Expenses and Balance"
        )

    figure.tight_layout()

    return figure


def _no_data(axis):
    axis.text(
        0.5,
        0.5,
        "No data to show",
        ha="center",
        va="center",
    )

    axis.axis("off")


def export_transactions_csv(
    user_id,
    filepath,
):
    """Export all user transactions."""

    with open(
        filepath,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(
            file
        )

        writer.writerow(
            [
                "Date",
                "Type",
                "Category",
                "Description",
                "Amount",
            ]
        )

        for transaction in get_transactions(
            user_id
        ):

            writer.writerow(
                [
                    to_display_date(
                        transaction["date"]
                    ),
                    transaction["type"],
                    transaction["category"],
                    transaction["description"],
                    transaction["amount"],
                ]
            )

    return filepath


def export_report_csv(
    report,
    filepath,
):
    """Export a report as CSV."""

    summary = report[
        "summary"
    ]

    with open(
        filepath,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(
            file
        )

        writer.writerow(
            [
                "Report",
                report["type"],
            ]
        )

        writer.writerow(
            [
                "Generated",
                report["generated_date"],
            ]
        )

        writer.writerow(
            [
                "Period",
                report["period"],
            ]
        )

        writer.writerow([])

        writer.writerow(
            [
                "Total Income",
                summary[
                    "total_income"
                ],
            ]
        )

        writer.writerow(
            [
                "Total Expenses",
                summary[
                    "total_expenses"
                ],
            ]
        )

        writer.writerow(
            [
                "Balance",
                summary["balance"],
            ]
        )

        writer.writerow([])

        writer.writerow(
            [
                "Category",
                "Amount",
                "Percent",
            ]
        )

        for category in report[
            "categories"
        ]:

            writer.writerow(
                [
                    category[
                        "category"
                    ],
                    category[
                        "total"
                    ],
                    category[
                        "percent"
                    ],
                ]
            )

        if report["trend"]:

            writer.writerow([])

            writer.writerow(
                [
                    "Month",
                    "Income",
                    "Expenses",
                ]
            )

            for month in report[
                "trend"
            ]:

                writer.writerow(
                    [
                        month["month"],
                        month["income"],
                        month["expenses"],
                    ]
                )

    return filepath


def export_report_pdf(
    report,
    filepath,
):
    """Export report as PDF."""

    from matplotlib.backends.backend_pdf import (
        PdfPages,
    )
    from matplotlib.figure import Figure

    text_page = Figure(
        figsize=(8.27, 11.69)
    )

    text_page.text(
        0.08,
        0.95,
        report_to_text(report),
        va="top",
        family="monospace",
        fontsize=9,
    )

    with PdfPages(filepath) as pdf:

        pdf.savefig(
            text_page
        )

        pdf.savefig(
            make_figure(report)
        )

    return filepath