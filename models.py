"""
models.py

Object-oriented model layer for the Personal Expense Tracker.
"""

from abc import (
    ABC,
    abstractmethod,
)

import admin as admin_module
import audit as audit_module
import auth
import budget as budget_module
import reports as reports_module
import transactions as transactions_module


class SystemUser(ABC):

    def __init__(
        self,
        user_id,
        username,
        email,
        password,
        is_active=True,
    ):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.password = password
        self.is_active = is_active

    @abstractmethod
    def get_role(self):
        pass

    def login(self, typed_password):
        return auth.check_password(
            typed_password,
            self.password,
        )


class RegularUser(SystemUser):

    def get_role(self):
        return "user"

    def register(self):

        self.user_id = auth.register_user(
            self.username,
            self.email,
            self.password,
        )

        self.password = ""

        return True

    def set_budget(self, amount):
        return budget_module.set_budget(
            self.user_id,
            amount,
        )

    def export_data(self, filepath):
        return reports_module.export_transactions_csv(
            self.user_id,
            filepath,
        )


class Auditor(SystemUser):

    def get_role(self):
        return "auditor"

    def generate_audit_report(self):

        new_id = (
            audit_module.generate_audit_report(
                self.user_id
            )
        )

        return AuditReport(
            new_id,
            status="Generated",
        )

    def download_audit_report(
        self,
        report_id,
        filepath,
    ):
        return AuditReport(
            report_id
        ).download(
            filepath,
            self.user_id,
        )


class Admin(SystemUser):

    def get_role(self):
        return "admin"

    def view_dashboard(self):
        return admin_module.get_dashboard_stats()

    def manage_accounts(self):
        return admin_module.list_users()

    def set_account_active(
        self,
        user_id,
        active,
    ):
        admin_module.set_user_active(
            user_id,
            active,
            self.user_id,
        )

    def delete_account(
        self,
        user_id,
    ):
        admin_module.delete_user(
            user_id,
            self.user_id,
        )


class Transaction:

    def __init__(
        self,
        user_id,
        type_="Expense",
        amount="",
        category="",
        description="",
        date="",
        transaction_id=None,
    ):
        self.transaction_id = transaction_id
        self.user_id = user_id
        self.type = type_
        self.amount = amount
        self.category = category
        self.description = description
        self.date = date

    def add(self):

        self.transaction_id = (
            transactions_module.add_transaction(
                self.user_id,
                self.type,
                self.amount,
                self.category,
                self.description,
                self.date,
            )
        )

        return True

    def edit(self):

        transactions_module.update_transaction(
            self.user_id,
            self.transaction_id,
            self.type,
            self.amount,
            self.category,
            self.description,
            self.date,
        )

        return True

    def delete(self):

        transactions_module.delete_transaction(
            self.user_id,
            self.transaction_id,
        )

        return True


class Budget:

    def __init__(
        self,
        user_id,
        amount,
        budget_id=None,
        start_date=None,
        end_date=None,
    ):
        self.budget_id = budget_id
        self.user_id = user_id
        self.amount = amount
        self.start_date = start_date
        self.end_date = end_date

    def update_budget(self):
        return budget_module.set_budget(
            self.user_id,
            self.amount,
        )


class Report:

    def __init__(
        self,
        user_id,
        report_type="Summary",
        start="",
        end="",
    ):
        self.report_id = None
        self.user_id = user_id
        self.report_type = report_type
        self.start = start
        self.end = end
        self.generated_date = None
        self.data = None

    def generate_report(self):

        self.data = reports_module.generate_report(
            self.user_id,
            self.report_type,
            self.start,
            self.end,
        )

        self.generated_date = (
            self.data["generated_date"]
        )

    def view_report(self):

        if self.data is None:
            self.generate_report()

        return reports_module.report_to_text(
            self.data
        )


class AuditReport:

    def __init__(
        self,
        audit_report_id,
        generated_date="",
        status="Generated",
    ):
        self.audit_report_id = audit_report_id
        self.generated_date = generated_date
        self.status = status

    def download(
        self,
        filepath,
        auditor_id=None,
    ):

        audit_module.download_audit_report(
            self.audit_report_id,
            filepath,
            auditor_id,
        )

        self.status = "Downloaded"

        return filepath


def create_user(row):
    """Convert a DB row to the correct user class."""

    classes = {
        "user": RegularUser,
        "auditor": Auditor,
        "admin": Admin,
    }

    role = row["role"]

    if role not in classes:
        raise ValueError(
            "Invalid user role."
        )

    return classes[
        role
    ](
        row["user_id"],
        row["username"],
        row["email"],
        row["password"],
        bool(row["is_active"]),
    )


def login_user(
    email,
    password,
):
    """Authenticate a user."""

    row = auth.find_user(
        email
    )

    if row is None:
        raise ValueError(
            "Invalid email or password."
        )

    user = create_user(
        row
    )

    if not user.login(
        password
    ):
        raise ValueError(
            "Invalid email or password."
        )

    if not user.is_active:
        raise ValueError(
            "This account is disabled. "
            "Please contact the admin."
        )

    return user