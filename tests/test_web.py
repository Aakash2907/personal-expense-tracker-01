"""
Tests for the Flask (web) version.  They are skipped when Flask is not installed.

Run with:  python -m unittest discover -s tests -v
"""

import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    os.environ.setdefault("VERCEL", "1")     # makes app.py keep its database in /tmp
    import app as web
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

import database
import sample_data


@unittest.skipUnless(HAS_FLASK, "Flask is not installed")
class TestWebApp(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        database.DB_PATH = os.path.join(self.folder.name, "web.db")
        database.create_database()
        sample_data.load_sample_data()
        self.client = web.app.test_client()

    def tearDown(self):
        self.folder.cleanup()

    def page(self, path):
        return self.client.get(path, base_url="https://localhost")

    def post(self, path, data, form_page=None):
        """POST a form using the CSRF token found on the page that shows the form."""
        html = self.page(form_page or path).get_data(as_text=True)
        data = dict(data, csrf_token=re.search(r'name="csrf_token" value="([^"]+)"', html).group(1))
        return self.client.post(path, data=data, base_url="https://localhost",
                                follow_redirects=True)

    def login(self, email, password):
        return self.post("/login", {"email": email, "password": password})

    def test_pages_need_login(self):
        self.assertEqual(self.page("/dashboard").status_code, 302)
        self.assertEqual(self.page("/").status_code, 302)

    def test_post_without_csrf_token_is_rejected(self):
        response = self.client.post("/login", base_url="https://localhost",
                                    data={"email": "demo@example.com", "password": "demo123"})
        self.assertEqual(response.status_code, 400)

    def test_login_and_dashboard(self):
        self.assertIn("Invalid email or password",
                      self.login("demo@example.com", "bad").get_data(as_text=True))
        html = self.login("demo@example.com", "demo123").get_data(as_text=True)
        self.assertIn("Total Income", html)
        self.assertIn("Monthly Budget", html)

    def test_add_expense_and_validation(self):
        self.login("demo@example.com", "demo123")
        bad = self.post("/add/expense", {"type": "Expense", "amount": "abc", "category": "Food",
                                         "description": "Lunch", "date": "2026-09-18"})
        self.assertIn("Please enter a valid amount.", bad.get_data(as_text=True))
        good = self.post("/add/expense", {"type": "Expense", "amount": "250", "category": "Food",
                                          "description": "Tea <b>", "date": "2026-09-18"})
        html = good.get_data(as_text=True)
        self.assertIn("Expense saved successfully.", html)
        self.assertIn("Tea &lt;b&gt;", html)                # HTML in user text is escaped

    def test_roles_are_separated(self):
        self.login("demo@example.com", "demo123")
        self.assertEqual(self.page("/admin").status_code, 302)   # user cannot open admin

    def test_admin_and_auditor_screens(self):
        html = self.login("admin@example.com", "admin123").get_data(as_text=True)
        self.assertIn("Manage Accounts", html)
        self.post("/logout", {}, form_page="/admin")
        html = self.login("auditor@example.com", "audit123").get_data(as_text=True)
        self.assertIn("Audit Reports", html)
        self.post("/auditor/generate", {}, form_page="/auditor")
        response = self.page("/auditor/1/download")
        self.assertEqual(response.mimetype, "text/csv")

    def test_csv_export(self):
        self.login("demo@example.com", "demo123")
        response = self.page("/export")
        self.assertTrue(response.data.startswith(b"Date,Type,Category,Description,Amount"))


if __name__ == "__main__":
    unittest.main()
