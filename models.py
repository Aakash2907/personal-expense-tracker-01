"""
models.py  -  The classes from the CLASS DIAGRAM.

What it does : defines SystemUser (abstract), RegularUser, Auditor, Admin,
               Transaction (the diagram's "Expense"), Budget, Report and
               AuditReport.  Each method is short and simply calls the
               matching function in another module.
Why needed   : it keeps the object-oriented design of the class diagram and
               shows inheritance, abstract classes and encapsulation.
Talks to     : auth.py, transactions.py, budget.py, reports.py, audit.py,
               admin.py (they do the real work) and the ui/ screens (which
               create these objects).
Diagram      : Class diagram (all classes and relationships).

Relationships from the diagram
  RegularUser  --manages-->  many Expense   (Transaction objects)
  RegularUser  --sets----->  0..1 Budget
  RegularUser  --views---->  many Report
  Expense      --included in--> Report
  Auditor      --generates--> many AuditReport
  Admin        --manages--->  many SystemUser
"""

from abc import ABC, abstractmethod

import admin as admin_module
import audit as audit_module
import auth
import budget as budget_module
import reports as reports_module
import transactions as transactions_module


# ===========================================================================
# Users  (inheritance:  SystemUser  <-  RegularUser / Auditor / Admin)
# ===========================================================================
class SystemUser(ABC):
    """Abstract parent class. It cannot be used directly (see get_role)."""

    def __init__(self, user_id, username, email, password, is_active=True):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.password = password        # the stored HASH (never plain text)
        self.is_active = is_active

    @abstractmethod
    def get_role(self):
        """Each child class returns its own role name."""

    def login(self, typed_password):
        """True if the typed password is correct."""
        return auth.check_password(typed_password, self.password)


class RegularUser(SystemUser):
    def get_role(self):
        return "user"

    def register(self):
        """Save this new user in the database. Here 'password' holds the plain
        text the person typed; the database only receives the hash."""
        self.user_id = auth.register_user(self.username, self.email, self.password)
        self.password = ""              # forget the plain password
        return True

    def set_budget(self, amount):
        """A user sets 0..1 Budget."""
        return Budget(self.user_id, amount).update_budget()

    def export_data(self, filepath):
        """Save all transactions in a CSV file and return the file path."""
        return reports_module.export_transactions_csv(self.user_id, filepath)


class Auditor(SystemUser):
    def get_role(self):
        return "auditor"

    def generate_audit_report(self):
        """Create a new audit report and return it as an AuditReport object."""
        new_id = audit_module.generate_audit_report(self.user_id)
        return AuditReport(new_id, status="Generated")

    def download_audit_report(self, report_id, filepath):
        return AuditReport(report_id).download(filepath)


class Admin(SystemUser):
    def get_role(self):
        return "admin"

    def view_dashboard(self):
        """Numbers for the Admin Dashboard."""
        return admin_module.get_dashboard_stats()

    def manage_accounts(self):
        """List of all accounts (the screen then lets the admin change them)."""
        return admin_module.list_users()

    def set_account_active(self, user_id, active):
        admin_module.set_user_active(user_id, active, self.user_id)

    def delete_account(self, user_id):
        admin_module.delete_user(user_id, self.user_id)


# ===========================================================================
# Finance classes
# ===========================================================================
class Transaction:
    """The diagram's "Expense" class.  The same class also stores Income:
    type is either "Expense" or "Income".  Values are kept exactly as typed
    (text) and are validated when add() or edit() is called."""

    def __init__(self, user_id, type_="Expense", amount="", category="",
                 description="", date="", transaction_id=None):
        self.transaction_id = transaction_id      # expenseId in the diagram
        self.user_id = user_id
        self.type = type_
        self.amount = amount
        self.category = category
        self.description = description
        self.date = date                           # DD-MM-YYYY

    def add(self):                                 # addExpense()
        self.transaction_id = transactions_module.add_transaction(
            self.user_id, self.type, self.amount, self.category,
            self.description, self.date)
        return True

    def edit(self):                                # editExpense()
        transactions_module.update_transaction(
            self.user_id, self.transaction_id, self.type, self.amount,
            self.category, self.description, self.date)
        return True

    def delete(self):                              # deleteExpense()
        transactions_module.delete_transaction(self.user_id, self.transaction_id)
        return True


class Budget:
    def __init__(self, user_id, amount, budget_id=None, start_date=None, end_date=None):
        self.budget_id = budget_id
        self.user_id = user_id
        self.amount = amount
        self.start_date = start_date
        self.end_date = end_date

    def update_budget(self):                       # updateBudget()
        return budget_module.set_budget(self.user_id, self.amount)


class Report:
    def __init__(self, user_id, report_type="Summary", start="", end=""):
        self.report_id = None
        self.user_id = user_id
        self.report_type = report_type
        self.start = start
        self.end = end
        self.generated_date = None
        self.data = None                           # filled by generate_report()

    def generate_report(self):                     # generateReport()
        self.data = reports_module.generate_report(
            self.user_id, self.report_type, self.start, self.end)
        self.generated_date = self.data["generated_date"]

    def view_report(self):                         # viewReport()
        if self.data is None:
            self.generate_report()
        return reports_module.report_to_text(self.data)


class AuditReport:
    def __init__(self, audit_report_id, generated_date="", status="Generated"):
        self.audit_report_id = audit_report_id
        self.generated_date = generated_date
        self.status = status

    def download(self, filepath):                  # download()
        audit_module.download_audit_report(self.audit_report_id, filepath)
        self.status = "Downloaded"
        return filepath


# ===========================================================================
# Login helpers
# ===========================================================================
def create_user(row):
    """Turn a database row into a RegularUser, Auditor or Admin object."""
    classes = {"user": RegularUser, "auditor": Auditor, "admin": Admin}
    return classes[row["role"]](row["user_id"], row["username"], row["email"],
                                row["password"], bool(row["is_active"]))


def login_user(email, password):
    """Check the credentials and return the matching user object.
    Raises ValueError with a friendly message when login fails."""
    row = auth.find_user(email)
    if row is None:
        raise ValueError("Invalid email or password.")
    user = create_user(row)
    if not user.login(password):
        raise ValueError("Invalid email or password.")
    if not user.is_active:
        raise ValueError("This account is disabled. Please contact the admin.")
    return user
