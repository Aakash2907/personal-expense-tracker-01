"""
app.py

Flask web version of the Personal Expense Tracker.

For Vercel:
    app = Flask application object

Important:
    SQLite on Vercel is temporary storage.
    Use PostgreSQL for persistent production data.
"""

import hmac
import os
import sqlite3
import tempfile
from datetime import date, datetime
from functools import wraps

from flask import (
    Flask,
    Response,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

import admin as admin_module
import audit as audit_module
import budget as budget_module
import database
import models
import reports as reports_module
import sample_data
import settings as settings_module
import transactions as tx

from validation import to_display_date


# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

if os.environ.get("VERCEL"):
    database.DB_PATH = os.path.join(
        tempfile.gettempdir(),
        "expense_tracker.db",
    )


database.create_database()


# Demo/sample data is explicitly controlled.
if os.environ.get(
    "DEMO_MODE",
    "",
).lower() == "true":

    sample_data.load_sample_data()


# ============================================================================
# FLASK CONFIGURATION
# ============================================================================

app = Flask(__name__)

secret_key = os.environ.get(
    "SECRET_KEY"
)

if not secret_key:

    # Local development can use a generated
    # temporary key. Vercel should always have
    # SECRET_KEY configured.
    if os.environ.get("VERCEL"):
        raise RuntimeError(
            "SECRET_KEY environment variable "
            "is required on Vercel."
        )

    secret_key = os.urandom(
        32
    ).hex()


app.secret_key = secret_key


app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(
        os.environ.get("VERCEL")
    ),
)


TYPES = {
    "expense": "Expense",
    "income": "Income",
}


# ============================================================================
# SECURITY
# ============================================================================

def csrf_token():
    """Return the current session's CSRF token."""

    if "csrf" not in session:
        session["csrf"] = os.urandom(
            32
        ).hex()

    return session["csrf"]


@app.before_request
def check_csrf_token():
    """Validate CSRF tokens on every POST."""

    if request.method != "POST":
        return

    sent = request.form.get(
        "csrf_token",
        "",
    )

    expected = session.get(
        "csrf",
        "",
    )

    if (
        not expected
        or not sent
        or not hmac.compare_digest(
            sent.encode("utf-8"),
            expected.encode("utf-8"),
        )
    ):
        abort(
            400,
            "Your form expired. "
            "Please refresh and try again.",
        )


@app.after_request
def add_security_headers(response):

    response.headers[
        "X-Content-Type-Options"
    ] = "nosniff"

    response.headers[
        "X-Frame-Options"
    ] = "DENY"

    response.headers[
        "Referrer-Policy"
    ] = "strict-origin-when-cross-origin"

    if session.get("user_id"):

        response.headers[
            "Cache-Control"
        ] = (
            "no-store, "
            "no-cache, "
            "must-revalidate, "
            "max-age=0"
        )

        response.headers[
            "Pragma"
        ] = "no-cache"

    return response


# ============================================================================
# TEMPLATE HELPERS
# ============================================================================

@app.context_processor
def inject_template_values():

    return {
        "user": (
            g.get("user")
            or current_user()
        ),
        "csrf_token": csrf_token,
    }


@app.template_filter("money")
def money_filter(
    amount,
    currency="₹",
):
    return settings_module.format_money(
        amount,
        currency,
    )


@app.template_filter("dmy")
def date_filter(db_date):
    return to_display_date(
        db_date
    )


# ============================================================================
# GENERAL HELPERS
# ============================================================================

def display_date(value):
    """
    Browser date:
        YYYY-MM-DD

    Application date:
        DD-MM-YYYY
    """

    value = (
        value or ""
    ).strip()

    try:

        return datetime.strptime(
            value,
            "%Y-%m-%d",
        ).strftime(
            "%d-%m-%Y"
        )

    except ValueError:

        return value


def current_user():
    """Return the authenticated user."""

    user_id = session.get(
        "user_id"
    )

    if not user_id:
        return None

    rows = database.query(
        """
        SELECT *
        FROM users
        WHERE user_id = ?
        """,
        (user_id,),
    )

    if not rows:
        session.clear()
        return None

    row = rows[0]

    if not row["is_active"]:
        session.clear()
        return None

    return models.create_user(
        row
    )


def home_url_for(user):

    pages = {
        "user": "dashboard",
        "admin": "admin_page",
        "auditor": "auditor_page",
    }

    return url_for(
        pages[
            user.get_role()
        ]
    )


def login_required(role):
    """Require authentication and a specific role."""

    def decorator(view):

        @wraps(view)
        def wrapper(
            *args,
            **kwargs,
        ):

            user = current_user()

            if user is None:

                flash(
                    "Please login to continue.",
                    "error",
                )

                return redirect(
                    url_for("login")
                )

            if user.get_role() != role:

                return redirect(
                    home_url_for(user)
                )

            g.user = user

            return view(
                *args,
                **kwargs,
            )

        return wrapper

    return decorator


def send_csv(
    create_file,
    filename,
):
    """Create a temporary CSV and send it."""

    handle, path = tempfile.mkstemp(
        suffix=".csv"
    )

    os.close(handle)

    try:

        create_file(path)

        with open(
            path,
            "rb",
        ) as file:

            data = file.read()

    finally:

        if os.path.exists(path):
            os.remove(path)

    return Response(
        data,
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                "attachment; filename="
                + filename
        },
    )


def send_pdf(
    create_file,
    filename,
):
    """Create a temporary PDF and send it."""

    handle, path = tempfile.mkstemp(
        suffix=".pdf"
    )

    os.close(handle)

    try:

        create_file(path)

        with open(
            path,
            "rb",
        ) as file:

            data = file.read()

    finally:

        if os.path.exists(path):
            os.remove(path)

    return Response(
        data,
        mimetype="application/pdf",
        headers={
            "Content-Disposition":
                "attachment; filename="
                + filename
        },
    )


# ============================================================================
# HOME / LOGIN / REGISTER
# ============================================================================

@app.route("/")
def home():

    user = current_user()

    if user:
        return redirect(
            home_url_for(user)
        )

    return redirect(
        url_for("login")
    )


@app.route(
    "/login",
    methods=["GET", "POST"],
)
def login():

    email = ""

    if request.method == "POST":

        email = request.form.get(
            "email",
            "",
        )

        try:

            user = models.login_user(
                email,
                request.form.get(
                    "password",
                    "",
                ),
            )

        except ValueError as error:

            flash(
                str(error),
                "error",
            )

        else:

            session.clear()

            session["user_id"] = (
                user.user_id
            )

            # Fresh CSRF token after authentication.
            session["csrf"] = (
                os.urandom(32).hex()
            )

            return redirect(
                home_url_for(user)
            )

    return render_template(
        "login.html",
        email=email,
    )


@app.route(
    "/register",
    methods=["GET", "POST"],
)
def register():

    form = {
        "username": "",
        "email": "",
    }

    if request.method == "POST":

        form = {
            "username":
                request.form.get(
                    "username",
                    "",
                ),
            "email":
                request.form.get(
                    "email",
                    "",
                ),
        }

        password = request.form.get(
            "password",
            "",
        )

        confirm = request.form.get(
            "confirm",
            "",
        )

        if password != confirm:

            flash(
                "The two passwords do not match.",
                "error",
            )

        else:

            try:

                models.RegularUser(
                    None,
                    form["username"],
                    form["email"],
                    password,
                ).register()

            except ValueError as error:

                flash(
                    str(error),
                    "error",
                )

            else:

                flash(
                    "Account created. "
                    "You can now login.",
                    "success",
                )

                return redirect(
                    url_for("login")
                )

    return render_template(
        "register.html",
        form=form,
    )


@app.route(
    "/logout",
    methods=["POST"],
)
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# ============================================================================
# DASHBOARD
# ============================================================================

@app.route("/dashboard")
@login_required("user")
def dashboard():

    user_id = g.user.user_id

    settings = (
        settings_module.get_settings(
            user_id
        )
    )

    return render_template(
        "dashboard.html",

        currency=settings[
            "currency"
        ],

        income=tx.get_total_income(
            user_id
        ),

        expenses=tx.get_total_expenses(
            user_id
        ),

        balance=tx.get_balance(
            user_id
        ),

        status=budget_module.get_budget_status(
            user_id
        ),

        alert=budget_module.check_budget_alert(
            user_id
        ),

        recent=tx.get_transactions(
            user_id,
            limit=8,
        ),
    )


# ============================================================================
# TRANSACTIONS
# ============================================================================

def transaction_form(
    type_,
    existing=None,
):
    """Handle add/edit transaction form."""

    user_id = g.user.user_id

    editing = (
        existing is not None
    )

    if request.method == "POST":

        form = {
            "type": (
                request.form.get(
                    "type",
                    type_,
                )
                if editing
                else type_
            ),

            "amount":
                request.form.get(
                    "amount",
                    "",
                ),

            "category":
                request.form.get(
                    "category",
                    "",
                ),

            "description":
                request.form.get(
                    "description",
                    "",
                ),

            "date":
                request.form.get(
                    "date",
                    "",
                ),
        }

        transaction = models.Transaction(
            user_id,
            form["type"],
            form["amount"],
            form["category"],
            form["description"],
            display_date(
                form["date"]
            ),
            (
                existing[
                    "transaction_id"
                ]
                if editing
                else None
            ),
        )

        try:

            if editing:
                transaction.edit()
            else:
                transaction.add()

        except ValueError as error:

            flash(
                str(error),
                "error",
            )

        else:

            flash(
                transaction.type
                + (
                    " updated"
                    if editing
                    else " saved"
                )
                + " successfully.",
                "success",
            )

            if (
                transaction.type
                == "Expense"
            ):

                alert = (
                    budget_module
                    .check_budget_alert(
                        user_id
                    )
                )

                if alert:
                    flash(
                        alert,
                        "warning",
                    )

            return redirect(
                url_for(
                    "transactions_list"
                    if editing
                    else "dashboard"
                )
            )

    elif editing:

        form = {
            "type":
                existing["type"],

            "amount":
                format(
                    existing["amount"],
                    ".2f",
                ),

            "category":
                existing["category"],

            "description":
                existing["description"],

            "date":
                existing["date"],
        }

    else:

        form = {
            "type": type_,
            "amount": "",
            "category": "",
            "description": "",
            "date":
                date.today().isoformat(),
        }

    return render_template(
        "transaction_form.html",
        form=form,
        editing=editing,
        expense_categories=(
            database.EXPENSE_CATEGORIES
        ),
        income_categories=(
            database.INCOME_CATEGORIES
        ),
    )


@app.route(
    "/add/<type_name>",
    methods=["GET", "POST"],
)
@login_required("user")
def add_transaction(type_name):

    if type_name not in TYPES:
        abort(404)

    return transaction_form(
        TYPES[type_name]
    )


@app.route(
    "/transactions/<int:transaction_id>/edit",
    methods=["GET", "POST"],
)
@login_required("user")
def edit_transaction(
    transaction_id,
):

    existing = tx.get_transaction(
        g.user.user_id,
        transaction_id,
    )

    if existing is None:
        abort(404)

    return transaction_form(
        existing["type"],
        existing,
    )


@app.route("/transactions")
@login_required("user")
def transactions_list():

    user_id = g.user.user_id

    filters = {
        "type":
            request.args.get(
                "type",
                "All",
            ),

        "category":
            request.args.get(
                "category",
                "All",
            ),

        "from":
            request.args.get(
                "from",
                "",
            ),

        "to":
            request.args.get(
                "to",
                "",
            ),

        "q":
            request.args.get(
                "q",
                "",
            ),
    }

    try:

        rows = tx.get_transactions(
            user_id,
            type_=filters["type"],
            category=filters["category"],
            date_from=display_date(
                filters["from"]
            ),
            date_to=display_date(
                filters["to"]
            ),
            search=filters["q"],
        )

    except ValueError as error:

        flash(
            str(error),
            "error",
        )

        rows = []

    return render_template(
        "transactions.html",
        rows=rows,
        filters=filters,
        categories=database.ALL_CATEGORIES,
        currency=(
            settings_module
            .get_settings(user_id)[
                "currency"
            ]
        ),
    )


@app.route(
    "/transactions/<int:transaction_id>/delete",
    methods=["POST"],
)
@login_required("user")
def delete_transaction(
    transaction_id,
):

    try:

        models.Transaction(
            g.user.user_id,
            transaction_id=transaction_id,
        ).delete()

        flash(
            "Transaction deleted successfully.",
            "success",
        )

    except ValueError as error:

        flash(
            str(error),
            "error",
        )

    return redirect(
        url_for("transactions_list")
    )


# ============================================================================
# REPORTS
# ============================================================================

def build_report():

    form = {
        "type":
            request.args.get(
                "type",
                "Summary",
            ),

        "from":
            request.args.get(
                "from",
                "",
            ),

        "to":
            request.args.get(
                "to",
                "",
            ),
    }

    try:

        report = models.Report(
            g.user.user_id,
            form["type"],
            display_date(
                form["from"]
            ),
            display_date(
                form["to"]
            ),
        )

        report.generate_report()

    except ValueError as error:

        flash(
            str(error),
            "error",
        )

        form = {
            "type": "Summary",
            "from": "",
            "to": "",
        }

        report = models.Report(
            g.user.user_id,
            "Summary",
        )

        report.generate_report()

    return (
        report.data,
        form,
    )


@app.route("/reports")
@login_required("user")
def reports_page():

    report, form = build_report()

    return render_template(
        "reports.html",
        report=report,
        form=form,
        report_types=(
            reports_module.REPORT_TYPES
        ),
    )


@app.route("/reports/export")
@login_required("user")
def export_report():

    report, _ = build_report()

    return send_csv(
        lambda path:
            reports_module.export_report_csv(
                report,
                path,
            ),
        "report.csv",
    )


@app.route("/reports/export/pdf")
@login_required("user")
def export_report_pdf():

    report, _ = build_report()

    return send_pdf(
        lambda path:
            reports_module.export_report_pdf(
                report,
                path,
            ),
        "report.pdf",
    )


@app.route("/export")
@login_required("user")
def export_data():

    return send_csv(
        g.user.export_data,
        "my_transactions.csv",
    )


# ============================================================================
# SETTINGS
# ===================================================================================

@app.route(
    "/settings",
    methods=["GET", "POST"],
)
@login_required("user")
def settings_page():

    user_id = g.user.user_id

    if request.method == "POST":

        budget_text = (
            request.form
            .get(
                "budget",
                "",
            )
            .strip()
        )

        try:

            if budget_text:
                g.user.set_budget(
                    budget_text
                )

            settings_module.save_settings(
                user_id,
                request.form.get(
                    "currency",
                    "",
                ),
                "alerts"
                in request.form,
            )

        except ValueError as error:

            flash(
                str(error),
                "error",
            )

        else:

            flash(
                "Your settings were saved.",
                "success",
            )

            return redirect(
                url_for("dashboard")
            )

    current_budget = (
        budget_module.get_budget(
            user_id
        )
    )

    return render_template(
        "settings.html",

        current=(
            settings_module
            .get_settings(user_id)
        ),

        budget_amount=(
            format(
                current_budget[
                    "amount"
                ],
                ".2f",
            )
            if current_budget
            else ""
        ),

        currencies=(
            settings_module.CURRENCIES
        ),
    )


# ============================================================================
# ADMIN
# ============================================================================

@app.route("/admin")
@login_required("admin")
def admin_page():

    return render_template(
        "admin.html",
        stats=g.user.view_dashboard(),
        accounts=g.user.manage_accounts(),
    )


@app.route(
    "/admin/<int:account_id>/active",
    methods=["POST"],
)
@login_required("admin")
def admin_set_active(
    account_id,
):

    try:

        g.user.set_account_active(
            account_id,
            request.form.get(
                "active"
            ) == "1",
        )

        flash(
            "Account updated.",
            "success",
        )

    except ValueError as error:

        flash(
            str(error),
            "error",
        )

    return redirect(
        url_for("admin_page")
    )


@app.route(
    "/admin/<int:account_id>/delete",
    methods=["POST"],
)
@login_required("admin")
def admin_delete(
    account_id,
):

    try:

        g.user.delete_account(
            account_id
        )

        flash(
            "Account deleted.",
            "success",
        )

    except ValueError as error:

        flash(
            str(error),
            "error",
        )

    return redirect(
        url_for("admin_page")
    )


# ============================================================================
# AUDITOR
# ============================================================================

@app.route("/auditor")
@login_required("auditor")
def auditor_page():

    return render_template(
        "auditor.html",
        audit_reports=(
            audit_module
            .get_audit_reports(
                g.user.user_id
            )
        ),
    )


@app.route(
    "/auditor/generate",
    methods=["POST"],
)
@login_required("auditor")
def auditor_generate():

    report = (
        g.user
        .generate_audit_report()
    )

    flash(
        "Audit report #"
        + str(
            report.audit_report_id
        )
        + " was generated.",
        "success",
    )

    return redirect(
        url_for("auditor_page")
    )


@app.route(
    "/auditor/<int:report_id>/download"
)
@login_required("auditor")
def auditor_download(
    report_id,
):

    try:

        return send_csv(
            lambda path:
                g.user.download_audit_report(
                    report_id,
                    path,
                ),
            "audit_report_"
            + str(report_id)
            + ".csv",
        )

    except ValueError as error:

        flash(
            str(error),
            "error",
        )

        return redirect(
            url_for("auditor_page")
        )


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(400)
@app.errorhandler(404)
def client_error(error):

    return (
        render_template(
            "error.html",
            code=error.code,
            message=error.description,
        ),
        error.code,
    )


@app.errorhandler(500)
def server_error(error):

    return (
        render_template(
            "error.html",
            code=500,
            message=(
                "An internal server error occurred. "
                "Please try again."
            ),
        ),
        500,
    )


@app.errorhandler(sqlite3.Error)
def database_error(error):

    return (
        render_template(
            "error.html",
            code=500,
            message=(
                "A database error occurred. "
                "Please try again."
            ),
        ),
        500,
    )


# ============================================================================
# LOCAL DEVELOPMENT
# ============================================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
    )