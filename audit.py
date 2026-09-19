"""
audit.py

Audit report generation and downloading.
"""

import csv
import io
from datetime import datetime

from database import (
    execute,
    insert,
    query,
)


def _build_audit_content():
    """Build system-level audit information."""

    rows = query(
        """
        SELECT
            u.user_id,
            u.username,
            u.email,
            u.is_active,
            COUNT(t.transaction_id) AS transactions,

            COALESCE(
                SUM(
                    CASE
                        WHEN t.type = 'Income'
                        THEN t.amount
                        ELSE 0
                    END
                ),
                0
            ) AS income,

            COALESCE(
                SUM(
                    CASE
                        WHEN t.type = 'Expense'
                        THEN t.amount
                        ELSE 0
                    END
                ),
                0
            ) AS expenses

        FROM users u

        LEFT JOIN transactions t
            ON t.user_id = u.user_id

        WHERE u.role = 'user'

        GROUP BY
            u.user_id

        ORDER BY
            u.user_id
        """
    )

    buffer = io.StringIO()

    writer = csv.writer(
        buffer
    )

    writer.writerow(
        [
            "User ID",
            "Username",
            "Email",
            "Active",
            "Transactions",
            "Total Income",
            "Total Expenses",
            "Balance",
        ]
    )

    for row in rows:

        income = round(
            row["income"],
            2,
        )

        expenses = round(
            row["expenses"],
            2,
        )

        writer.writerow(
            [
                row["user_id"],
                row["username"],
                row["email"],
                (
                    "Yes"
                    if row["is_active"]
                    else "No"
                ),
                row["transactions"],
                income,
                expenses,
                round(
                    income - expenses,
                    2,
                ),
            ]
        )

    return buffer.getvalue()


def generate_audit_report(
    auditor_id
):
    """Generate an audit report."""

    return insert(
        """
        INSERT INTO audit_reports
        (
            auditor_id,
            generated_date,
            status,
            content
        )
        VALUES (?, ?, 'Generated', ?)
        """,
        (
            auditor_id,
            datetime.now().strftime(
                "%d-%m-%Y %H:%M"
            ),
            _build_audit_content(),
        ),
    )


def get_audit_reports(
    auditor_id=None
):
    """Return audit reports."""

    if auditor_id is None:

        return query(
            """
            SELECT
                audit_report_id,
                auditor_id,
                generated_date,
                status
            FROM audit_reports
            ORDER BY audit_report_id DESC
            """
        )

    return query(
        """
        SELECT
            audit_report_id,
            auditor_id,
            generated_date,
            status
        FROM audit_reports
        WHERE auditor_id = ?
        ORDER BY audit_report_id DESC
        """,
        (auditor_id,),
    )


def download_audit_report(
    report_id,
    filepath,
    auditor_id=None,
):
    """
    Download an audit report.

    If auditor_id is supplied, the report must belong to that auditor.
    """

    if auditor_id is None:

        rows = query(
            """
            SELECT content
            FROM audit_reports
            WHERE audit_report_id = ?
            """,
            (report_id,),
        )

    else:

        rows = query(
            """
            SELECT content
            FROM audit_reports
            WHERE audit_report_id = ?
              AND auditor_id = ?
            """,
            (
                report_id,
                auditor_id,
            ),
        )

    if not rows:
        raise ValueError(
            "Audit report not found."
        )

    with open(
        filepath,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        file.write(
            rows[0]["content"]
        )

    if auditor_id is None:

        execute(
            """
            UPDATE audit_reports
            SET status = 'Downloaded'
            WHERE audit_report_id = ?
            """,
            (report_id,),
        )

    else:

        execute(
            """
            UPDATE audit_reports
            SET status = 'Downloaded'
            WHERE audit_report_id = ?
              AND auditor_id = ?
            """,
            (
                report_id,
                auditor_id,
            ),
        )

    return filepath