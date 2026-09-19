"""
Unit tests for the Personal Expense Tracker (standard library "unittest").

Run from the project folder with:
    python -m unittest discover -s tests -v

Every test uses a fresh temporary database, so your real data is never touched.
"""

import csv
import os
import sys
import tempfile
import unittest
from datetime import date

# allow "import database" etc. when the tests are run from any folder
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import admin
import audit
import auth
import budget
import database
import models
import reports
import sample_data
import settings
import transactions


class BaseTest(unittest.TestCase):
    """Creates an empty temporary database and one user before every test."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        database.DB_PATH = os.path.join(self.folder.name, "test.db")
        database.create_database()
        self.user_id = auth.register_user("Asha", "asha@example.com", "pass1234")

    def tearDown(self):
        self.folder.cleanup()

    def today(self):
        return date.today().strftime("%d-%m-%Y")


class TestTransactions(BaseTest):
    def test_add_expense(self):
        new_id = transactions.add_expense(self.user_id, "250", "Food", "Lunch", "18-09-2026")
        saved = transactions.get_transaction(self.user_id, new_id)
        self.assertEqual(saved["type"], "Expense")
        self.assertEqual(saved["amount"], 250.0)
        self.assertEqual(saved["date"], "2026-09-18")      # stored as YYYY-MM-DD

    def test_add_income(self):
        new_id = transactions.add_income(self.user_id, "20,000", "Salary",
                                         "Monthly salary", "01-09-2026")
        saved = transactions.get_transaction(self.user_id, new_id)
        self.assertEqual(saved["type"], "Income")
        self.assertEqual(saved["amount"], 20000.0)

    def test_totals_and_balance(self):
        transactions.add_income(self.user_id, 30000, "Salary", "Salary", "01-09-2026")
        transactions.add_expense(self.user_id, 2000, "Food", "Food", "02-09-2026")
        transactions.add_expense(self.user_id, 1000, "Transport", "Bus", "03-09-2026")
        self.assertEqual(transactions.get_total_income(self.user_id), 30000)
        self.assertEqual(transactions.get_total_expenses(self.user_id), 3000)
        self.assertEqual(transactions.get_balance(self.user_id), 27000)

    def test_update_transaction(self):
        new_id = transactions.add_expense(self.user_id, 100, "Food", "Snack", "01-09-2026")
        transactions.update_transaction(self.user_id, new_id, "Expense", "150.50",
                                        "Shopping", "Gift", "02-09-2026")
        saved = transactions.get_transaction(self.user_id, new_id)
        self.assertEqual(saved["amount"], 150.5)
        self.assertEqual(saved["category"], "Shopping")
        self.assertEqual(saved["description"], "Gift")
        self.assertEqual(saved["date"], "2026-09-02")

    def test_change_type_when_updating(self):
        new_id = transactions.add_expense(self.user_id, 100, "Other", "Mistake", "01-09-2026")
        transactions.update_transaction(self.user_id, new_id, "Income", 100,
                                        "Gift", "Actually a gift", "01-09-2026")
        self.assertEqual(transactions.get_total_income(self.user_id), 100)
        self.assertEqual(transactions.get_total_expenses(self.user_id), 0)

    def test_delete_transaction(self):
        new_id = transactions.add_expense(self.user_id, 100, "Food", "Snack", "01-09-2026")
        transactions.delete_transaction(self.user_id, new_id)
        self.assertIsNone(transactions.get_transaction(self.user_id, new_id))
        with self.assertRaises(ValueError):           # already gone
            transactions.delete_transaction(self.user_id, new_id)

    def test_update_missing_transaction(self):
        with self.assertRaises(ValueError):
            transactions.update_transaction(self.user_id, 999, "Expense", 10,
                                            "Food", "x", "01-09-2026")

    def test_users_cannot_touch_each_others_data(self):
        other = auth.register_user("Ravi", "ravi@example.com", "pass1234")
        new_id = transactions.add_expense(self.user_id, 100, "Food", "Mine", "01-09-2026")
        with self.assertRaises(ValueError):
            transactions.delete_transaction(other, new_id)
        self.assertEqual(transactions.get_transactions(other), [])

    def test_search_and_filters(self):
        transactions.add_expense(self.user_id, 100, "Food", "Pizza", "01-09-2026")
        transactions.add_expense(self.user_id, 50, "Transport", "Auto", "10-09-2026")
        transactions.add_income(self.user_id, 500, "Gift", "Birthday", "15-09-2026")

        self.assertEqual(len(transactions.get_transactions(self.user_id, search="Food")), 1)
        self.assertEqual(len(transactions.get_transactions(self.user_id, search="pizza")), 1)
        self.assertEqual(len(transactions.get_transactions(self.user_id, type_="Income")), 1)
        self.assertEqual(len(transactions.get_transactions(self.user_id, category="Transport")), 1)
        self.assertEqual(len(transactions.get_transactions(
            self.user_id, date_from="05-09-2026", date_to="12-09-2026")), 1)
        self.assertEqual(len(transactions.get_transactions(self.user_id, type_="All")), 3)
        # newest first
        self.assertEqual(transactions.get_transactions(self.user_id)[0]["description"], "Birthday")


class TestValidation(BaseTest):
    def test_invalid_amounts(self):
        for bad in ["abc", "-100", "0", "", "   ", "nan", "inf"]:
            with self.assertRaises(ValueError, msg="amount " + repr(bad)):
                transactions.add_expense(self.user_id, bad, "Food", "Lunch", "01-09-2026")
        self.assertEqual(transactions.get_transactions(self.user_id), [])   # nothing saved

    def test_valid_amounts(self):
        for good in ["100", "250.50", "5000", 75]:
            transactions.add_expense(self.user_id, good, "Food", "Lunch", "01-09-2026")
        self.assertEqual(len(transactions.get_transactions(self.user_id)), 4)

    def test_invalid_dates(self):
        for bad in ["2026-09-18", "31-02-2026", "abc", "", "18/09/2026"]:
            with self.assertRaises(ValueError, msg="date " + repr(bad)):
                transactions.add_expense(self.user_id, 10, "Food", "Lunch", bad)

    def test_empty_description_and_category(self):
        with self.assertRaises(ValueError):
            transactions.add_expense(self.user_id, 10, "Food", "   ", "01-09-2026")
        with self.assertRaises(ValueError):
            transactions.add_expense(self.user_id, 10, "", "Lunch", "01-09-2026")

    def test_error_message_text(self):
        with self.assertRaises(ValueError) as caught:
            transactions.add_expense(self.user_id, "abc", "Food", "Lunch", "01-09-2026")
        self.assertEqual(str(caught.exception), "Please enter a valid amount.")


class TestUsersAndLogin(BaseTest):
    def test_password_is_not_stored_as_plain_text(self):
        row = auth.find_user("asha@example.com")
        self.assertNotIn("pass1234", row["password"])

    def test_register_and_login(self):
        user = models.RegularUser(None, "Meera", "Meera@Example.com", "secret1")
        self.assertTrue(user.register())
        self.assertIsNotNone(user.user_id)
        logged_in = models.login_user("meera@example.com", "secret1")
        self.assertIsInstance(logged_in, models.RegularUser)
        self.assertEqual(logged_in.get_role(), "user")

    def test_wrong_password_and_unknown_email(self):
        with self.assertRaises(ValueError):
            models.login_user("asha@example.com", "wrong")
        with self.assertRaises(ValueError):
            models.login_user("nobody@example.com", "pass1234")

    def test_duplicate_email_and_bad_input(self):
        with self.assertRaises(ValueError):
            auth.register_user("Copy", "asha@example.com", "pass1234")
        with self.assertRaises(ValueError):
            auth.register_user("X", "not-an-email", "pass1234")
        with self.assertRaises(ValueError):
            auth.register_user("X", "x@example.com", "12")
        with self.assertRaises(ValueError):
            auth.register_user("  ", "x@example.com", "pass1234")

    def test_roles_and_abstract_class(self):
        auth.create_default_accounts()
        self.assertIsInstance(models.login_user("admin@example.com", "admin123"), models.Admin)
        self.assertIsInstance(models.login_user("auditor@example.com", "audit123"), models.Auditor)
        with self.assertRaises(TypeError):               # SystemUser is abstract
            models.SystemUser(1, "a", "a@a.com", "x")


class TestBudgetAndSettings(BaseTest):
    def test_budget_status(self):
        self.assertIsNone(budget.get_budget_status(self.user_id))      # not set yet
        models.RegularUser(self.user_id, "Asha", "asha@example.com", "").set_budget("1000")
        transactions.add_expense(self.user_id, 250, "Food", "Lunch", self.today())
        status = budget.get_budget_status(self.user_id)
        self.assertEqual(status["spent"], 250)
        self.assertEqual(status["remaining"], 750)
        self.assertEqual(status["percent"], 25)

    def test_budget_alerts(self):
        budget.set_budget(self.user_id, 1000)
        transactions.add_expense(self.user_id, 500, "Food", "Half", self.today())
        self.assertIsNone(budget.check_budget_alert(self.user_id))
        transactions.add_expense(self.user_id, 350, "Food", "More", self.today())
        self.assertIn("85%", budget.check_budget_alert(self.user_id))
        transactions.add_expense(self.user_id, 300, "Food", "Over", self.today())
        self.assertIn("exceeded", budget.check_budget_alert(self.user_id))

    def test_alerts_can_be_disabled(self):
        budget.set_budget(self.user_id, 100)
        transactions.add_expense(self.user_id, 500, "Food", "Big", self.today())
        settings.save_settings(self.user_id, "₹", False)
        self.assertIsNone(budget.check_budget_alert(self.user_id))

    def test_invalid_budget(self):
        with self.assertRaises(ValueError):
            budget.set_budget(self.user_id, "-5")

    def test_settings(self):
        self.assertEqual(settings.get_settings(self.user_id),
                         {"currency": "₹", "alerts_enabled": True})
        settings.save_settings(self.user_id, "$", False)
        self.assertEqual(settings.get_settings(self.user_id),
                         {"currency": "$", "alerts_enabled": False})
        with self.assertRaises(ValueError):
            settings.save_settings(self.user_id, "XYZ", True)
        self.assertEqual(settings.format_money(20000, "₹"), "₹20,000.00")


class TestReports(BaseTest):
    def setUp(self):
        super().setUp()
        transactions.add_income(self.user_id, 30000, "Salary", "Salary", "01-08-2026")
        transactions.add_income(self.user_id, 30000, "Salary", "Salary", "01-09-2026")
        transactions.add_expense(self.user_id, 3000, "Food", "Food", "05-08-2026")
        transactions.add_expense(self.user_id, 1000, "Food", "Food", "05-09-2026")
        transactions.add_expense(self.user_id, 1000, "Bills", "Bill", "06-09-2026")

    def test_summary_report(self):
        report = reports.generate_report(self.user_id, "Summary")
        self.assertEqual(report["summary"]["total_income"], 60000)
        self.assertEqual(report["summary"]["total_expenses"], 5000)
        self.assertEqual(report["summary"]["balance"], 55000)

    def test_report_with_date_range(self):
        report = reports.generate_report(self.user_id, "Summary", "01-09-2026", "30-09-2026")
        self.assertEqual(report["summary"]["total_expenses"], 2000)
        with self.assertRaises(ValueError):
            reports.generate_report(self.user_id, "Summary", "30-09-2026", "01-09-2026")

    def test_category_breakdown(self):
        report = reports.generate_report(self.user_id, "Category Breakdown")
        self.assertEqual(report["categories"][0]["category"], "Food")
        self.assertEqual(report["categories"][0]["total"], 4000)
        self.assertEqual(report["categories"][0]["percent"], 80.0)

    def test_trend_analysis(self):
        report = reports.generate_report(self.user_id, "Trend Analysis")
        self.assertEqual([m["month"] for m in report["trend"]], ["2026-08", "2026-09"])
        self.assertEqual(report["trend"][0]["expenses"], 3000)

    def test_report_history_and_class(self):
        report = models.Report(self.user_id, "Summary")
        text = report.view_report()
        self.assertIn("Total Income", text)
        self.assertEqual(len(reports.get_report_history(self.user_id)), 1)
        with self.assertRaises(ValueError):
            reports.generate_report(self.user_id, "Unknown")

    def test_export_files(self):
        folder = self.folder.name
        user = models.RegularUser(self.user_id, "Asha", "asha@example.com", "")
        path = user.export_data(os.path.join(folder, "data.csv"))
        with open(path, newline="", encoding="utf-8") as file:
            rows = list(csv.reader(file))
        self.assertEqual(rows[0], ["Date", "Type", "Category", "Description", "Amount"])
        self.assertEqual(len(rows), 6)                        # header + 5 transactions

        report = reports.generate_report(self.user_id, "Trend Analysis")
        reports.export_report_csv(report, os.path.join(folder, "report.csv"))
        self.assertTrue(os.path.getsize(os.path.join(folder, "report.csv")) > 0)

        try:
            import matplotlib                                   # noqa: F401
        except ImportError:
            self.skipTest("matplotlib not installed (PDF export skipped)")
        pdf_path = reports.export_report_pdf(report, os.path.join(folder, "report.pdf"))
        with open(pdf_path, "rb") as file:
            self.assertEqual(file.read(4), b"%PDF")

    def test_charts_are_created(self):
        try:
            import matplotlib                                   # noqa: F401
        except ImportError:
            self.skipTest("matplotlib not installed")
        for report_type in reports.REPORT_TYPES:
            figure = reports.make_figure(reports.generate_report(self.user_id, report_type))
            self.assertEqual(len(figure.axes), 1)


class TestAdminAndAuditor(BaseTest):
    def setUp(self):
        super().setUp()
        auth.create_default_accounts()
        self.admin = models.login_user("admin@example.com", "admin123")
        self.auditor = models.login_user("auditor@example.com", "audit123")
        transactions.add_income(self.user_id, 1000, "Salary", "Pay", "01-09-2026")
        transactions.add_expense(self.user_id, 400, "Food", "Secret lunch", "02-09-2026")

    def test_admin_dashboard_and_accounts(self):
        stats = self.admin.view_dashboard()
        self.assertEqual(stats["regular_users"], 1)
        self.assertEqual(stats["transactions"], 2)
        self.assertEqual(len(self.admin.manage_accounts()), 3)

    def test_disabled_user_cannot_login(self):
        self.admin.set_account_active(self.user_id, False)
        with self.assertRaises(ValueError):
            models.login_user("asha@example.com", "pass1234")
        self.admin.set_account_active(self.user_id, True)
        self.assertIsNotNone(models.login_user("asha@example.com", "pass1234"))

    def test_admin_delete_rules(self):
        with self.assertRaises(ValueError):
            self.admin.delete_account(self.admin.user_id)       # not yourself
        self.admin.delete_account(self.user_id)
        self.assertEqual(transactions.get_transactions(self.user_id), [])   # data removed too
        self.assertEqual(self.admin.view_dashboard()["regular_users"], 0)

    def test_audit_report_generate_and_download(self):
        audit_report = self.auditor.generate_audit_report()
        self.assertEqual(audit_report.status, "Generated")
        path = os.path.join(self.folder.name, "audit.csv")
        self.auditor.download_audit_report(audit_report.audit_report_id, path)
        with open(path, newline="", encoding="utf-8") as file:
            text = file.read()
        self.assertIn("asha@example.com", text)
        self.assertNotIn("Secret lunch", text)               # auditors only see totals
        self.assertEqual(audit.get_audit_reports()[0]["status"], "Downloaded")
        with self.assertRaises(ValueError):
            audit.download_audit_report(999, path)


class TestSampleData(BaseTest):
    def test_sample_data_loads_once(self):
        # start again with an EMPTY database (BaseTest already added a user)
        database.DB_PATH = os.path.join(self.folder.name, "sample.db")
        database.create_database()
        sample_data.load_sample_data()
        sample_data.load_sample_data()                       # second call does nothing
        demo = models.login_user("demo@example.com", "demo123")
        self.assertGreater(transactions.get_total_income(demo.user_id), 0)
        self.assertGreater(transactions.get_total_expenses(demo.user_id), 0)
        self.assertIsNotNone(budget.get_budget_status(demo.user_id))
        self.assertEqual(len(admin.list_users()), 3)


if __name__ == "__main__":
    unittest.main()
