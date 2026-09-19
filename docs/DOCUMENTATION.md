Personal Expense Tracker – Project Documentation
1. Project Overview
A student-level desktop application written in Python 3 + Tkinter + SQLite. It records income and expenses, calculates the balance, manages a monthly budget with alerts, produces reports with charts, and supports three roles (User, Auditor, Admin) exactly as shown in the use case and class diagrams.
Run with python main.py. Tests: python -m unittest discover -s tests -v.
2. Diagram Analysis
#
Diagram (file in assets/diagrams/)
What it shows
How it was used
1
Use Case (1_use_case_diagram.png)
3 actors. User: Register Account, Login, Delete Expenses (Edit Expense «extend»), Add Expense, View Report («include» Generate Report), Set Budget, Export Data. Auditor: Generate / Download Audit Report. Admin: Admin Dashboard («include» Manage Accounts)
Decides the roles and every feature
2
Flowchart (2_flowchart.png)
Open app → logged in? → login → Dashboard → Select Action: Add Expense (form, validate, save), View Expenses (filters by category/date range, Edit / Delete with confirmation), Settings (Currency, Budget Limit, Notifications), View Reports (Summary, Category Breakdown, Trend Analysis, export PDF/CSV), Logout
Decides the screens, buttons and messages
3
Component (3_component_diagram.png)
User Interface → Authentication, Transaction Management (Expense Tracking, Income Management), Budget Management, Reports & Analytics, Notification Component → Finance Database
Decides the Python modules
4
State (4_state_diagram.png)
Idle → Login → Authenticating → Authenticated{ MainMenu ⇄ AddTransaction/InputTransaction/Saving, ViewTransactions, Settings, GenerateReport, Logout }
Decides navigation: always return to the main menu
5
Data Flow (5_data_flow_diagram.png)
4 processes (1.0 Authentication, 2.0 Manage Expenses, 3.0 Manage Budget, 4.0 Generate Reports) and 3 data stores (D1 User, D2 Expense, D3 Budget DB)
Decides which module reads/writes which table
6
Deployment (6_deployment_diagram.png)
Client (Web/Mobile UI) → REST API + 4 services → Database server
Simplified to layers (see decision 1)
7
Sequence (7_sequence_diagram.png)
Open App → fetch transactions → display; Add transaction → save → confirm → show updated list
The dashboard loads transactions on open and refreshes after every save
8
Simple Flow (8_simple_flow_diagram.png)
User interacts with App; App fetches / saves data in Database
The overall idea of the project
9
Class (9_class_diagram.png)
Abstract SystemUser ← RegularUser, Auditor, Admin; Expense, Budget, Report, AuditReport with attributes, methods and multiplicities
Decides models.py and the table columns
Design decisions (where the brief and diagrams needed a choice)
Tkinter, not Flask/REST. The deployment diagram shows a client, an application server with services, and a database server. The brief says to avoid REST/servers unless required and to prefer Tkinter. So the three tiers became three layers inside one program: ui/ (client) → service modules auth / transactions / budget / reports (application services) → database.py + SQLite (database). The services in the diagram still exist as separate modules.
Income. The class diagram only has Expense, but the component diagram has Income Management, the state diagram says Transaction, and the brief needs Balance = Income − Expenses. So one Transaction class / table stores both, using a type column (Expense or Income). Transaction is the diagram's Expense.
No category management. In the diagrams category is just a string attribute and there is no Category class or use case, so categories are a fixed list in database.py.
Auditor/Admin accounts. Only User can register (use case). Admin and Auditor accounts are created automatically on first run.
Data stores D1/D2/D3 are three tables (users, transactions, budgets) in one SQLite file.
Extra tables: settings (flowchart: currency + notifications), reports (Report class), audit_reports (AuditReport class). Nothing else was added.
SystemUser.login() receives the typed password as a parameter (the diagram shows no parameter).
3. Diagram → Requirement → Code Mapping
Use case / diagram element
Class method
Function
Table
Register Account
RegularUser.register()
auth.register_user()
users
Login
SystemUser.login() via models.login_user()
auth.check_password()
users
Add Expense / Income
Transaction.add()
transactions.add_transaction()
transactions
Edit Expense («extend»)
Transaction.edit()
transactions.update_transaction()
transactions
Delete Expenses
Transaction.delete()
transactions.delete_transaction()
transactions
View Expenses + filters
–
transactions.get_transactions()
transactions
Set Budget
RegularUser.set_budget() → Budget.update_budget()
budget.set_budget()
budgets
Alerts (Notification Component)
–
budget.check_budget_alert()
budgets, settings
Settings: currency, alerts
–
settings.save_settings()
settings
View Report «include» Generate Report
Report.generate_report(), Report.view_report()
reports.generate_report()
reports
Export Data
RegularUser.export_data()
reports.export_transactions_csv()
transactions
Export report PDF / CSV
–
reports.export_report_pdf() / export_report_csv()
–
Generate Audit Report
Auditor.generate_audit_report()
audit.generate_audit_report()
audit_reports
Download Audit Report
Auditor.download_audit_report() → AuditReport.download()
audit.download_audit_report()
audit_reports
Admin Dashboard
Admin.view_dashboard()
admin.get_dashboard_stats()
users, transactions
Manage Accounts
Admin.manage_accounts()
admin.list_users(), set_user_active(), delete_user()
users
Flow mappings
Add Expense (flowchart + sequence diagram)
User clicks [Add Expense] on Dashboard            ui/dashboard.py
   ↓
Form opens: amount, category, date, description   ui/transaction_window.py  (TransactionForm)
   ↓
Validate Input?  ── Invalid ──► error message, back to form   validation.py
   ↓ Valid
Transaction.add() → add_transaction()             models.py → transactions.py
   ↓
INSERT into SQLite (transactions table)           database.py
   ↓
Success message → budget alert check              budget.check_budget_alert()
   ↓
Dashboard refresh: totals, budget, recent list    DashboardScreen.refresh()
Login (flowchart + state diagram)
Idle → LoginScreen → login_user(email, password) → find_user() → check_password()
   valid   → role? user → Dashboard | admin → Admin screen | auditor → Auditor screen
   invalid → "Login Failed" message → back to Login
View Reports (flowchart)
Reports button → choose type (Summary / Category Breakdown / Trend Analysis)
   → Report.generate_report() → totals, category and month queries
   → text + Matplotlib chart on screen → Export? → PDF or CSV file
Delete (flowchart)
View Transactions → select row → [Delete Selected] → "Are you sure...?"
   No  → back to list
   Yes → Transaction.delete() → DELETE from SQLite → success message → list + dashboard refresh
4. Final Project Structure
PersonalExpenseTracker/
├── main.py  database.py  validation.py  auth.py  models.py
├── transactions.py  budget.py  settings.py  reports.py  audit.py  admin.py  sample_data.py
├── ui/ widgets.py  login.py  dashboard.py  transaction_window.py
│       reports_window.py  settings_window.py  admin_screen.py  auditor_screen.py
├── tests/test_expense_tracker.py
├── database/expense_tracker.db      (created automatically)
├── assets/diagrams/                 (9 diagrams)
├── docs/DOCUMENTATION.md
├── requirements.txt   README.md
Each source file starts with a header comment that answers: what it does, why it is needed, which modules it talks to, which diagram element it implements.
5. Module Summary (short viva answers)
Module
What / Why
Talks to
Diagram
database.py
Creates tables, gives query/insert/execute helpers
all modules
Finance Database, D1–D3
validation.py
Checks amount, date, text, email
transactions, auth, budget, reports
"Validate Input?"
auth.py
Register, password hash, find user
models, database
1.0 User Authentication
transactions.py
Add/view/edit/delete, totals, filters
models, budget, reports
2.0 Manage Expenses
budget.py
Monthly budget, status, alerts
settings, transactions
3.0 Manage Budget, Notification
settings.py
Currency, alerts flag, money format
budget, reports, ui
Settings branch
reports.py
Reports, charts, exports
transactions, settings
4.0 Generate Reports
audit.py / admin.py
Auditor and Admin functions
models
Auditor / Admin use cases
models.py
Classes from the class diagram
all service modules, ui
Class diagram
ui/*
Tkinter screens
models + service modules
User Interface component
main.py
Starts app, switches screens
ui, database
Flowchart start/end
6. Database Schema
users          (user_id PK, username, email UNIQUE, password [salted hash], role, is_active)
transactions   (transaction_id PK, user_id FK, type, amount, category, description, date)
budgets        (budget_id PK, user_id FK UNIQUE, amount, start_date, end_date)
settings       (user_id PK/FK, currency, alerts_enabled)
reports        (report_id PK, user_id FK, report_type, generated_date)
audit_reports  (audit_report_id PK, auditor_id FK, generated_date, status, content)
Relationships (from the class diagram): one user → many transactions; one user → 0..1 budget; one user → many reports; one auditor → many audit reports. Deleting a user also deletes their data (ON DELETE CASCADE). Dates are stored as YYYY-MM-DD (sorts correctly) and shown as DD-MM-YYYY.
7. How to Run
pip install -r requirements-desktop.txt   # matplotlib (desktop version)
python main.py                            # Tkinter desktop app

pip install -r requirements.txt           # flask (web version)
python app.py                             # browser version (also used on Vercel)
python -m unittest discover -s tests -v
Ubuntu/Debian may need sudo apt install python3-tk. Demo logins: demo@example.com / demo123, admin@example.com / admin123, auditor@example.com / audit123.
8. Sample Input / Output
Dashboard (demo user)
Total Income   : ₹90,000.00
Total Expenses : ₹33,900.00
Current Balance: ₹56,100.00
Budget ₹12,000.00 | Spent ₹11,300.00 | Remaining ₹700.00 (94% used)
Warning: you have used 94% of your monthly budget.
Add expense – Amount 250, Category Food, Description Lunch, Date 18-09-2026 → "Expense saved successfully." The row appears in the table and the totals change.
Invalid input – Amount abc → "Please enter a valid amount." (also -100, 0 and empty are rejected).
Trend Analysis report
=== TREND ANALYSIS REPORT ===
Total Income   : ₹90,000.00
Total Expenses : ₹33,900.00
Balance        : ₹56,100.00

Category-wise expenses
  Education           ₹9,000.00   26.5%
  Shopping            ₹7,500.00   22.1%
  ...
Monthly trend
  2026-07  Income ₹30,000.00  Expenses ₹10,170.00
  2026-08  Income ₹30,000.00  Expenses ₹12,430.00
9. Test Cases (tests/test_expense_tracker.py, 36 tests)
Area
Tests
Transactions
add expense, add income, totals and balance, update, change type, delete, missing record, users cannot touch each other's data, search and filters
Validation
invalid amounts (abc, -100, 0, empty, nan, inf), valid amounts, invalid dates, empty description/category, error message text
Users
password not stored as plain text, register + login, wrong password, duplicate email, abstract SystemUser, roles
Budget / settings
budget status, alerts at 80% and 100%, alerts can be disabled, invalid budget, currency settings
Reports
summary, date range, category breakdown, trend, history, CSV/PDF export, charts
Admin / Auditor
dashboard numbers, disabled user cannot login, delete rules, audit report generate + download (totals only)
Sample data
loads once, demo user has data
The tests use a temporary database, so your real data is never changed.
10. Diagram Consistency Check
Actors: User, Auditor, Admin implemented (RegularUser, Auditor, Admin)
Use cases: Register, Login, Add / Edit / Delete Expense, View + Generate Report, Set Budget, Export Data, Generate + Download Audit Report, Admin Dashboard, Manage Accounts
Flowchart: login check, dashboard, add form with validation, view with filters, edit, delete with confirmation, settings (currency, budget, notifications), reports (3 types, charts, PDF/CSV export), logout
Component diagram: Authentication, Transaction Management (expense + income), Budget Management, Reports & Analytics, Notification (alerts), Database
State diagram: Login → Authenticated → main menu and back after every action; Logout ends the session
DFD: 4 processes, 3 data stores (as tables)
Sequence diagram: transactions shown on open; list refreshed after saving
Class diagram: all classes, attributes, methods, inheritance and multiplicities (see models.py)
[~] Deployment diagram: implemented as layers in one program (decision 1)
Removed as unnecessary: category management screens, a separate Income class, REST API.
11. How the Project Works
User
 ↓
Login screen  (or Register)             → wrong details: error, try again
 ↓
Role check → User: Dashboard | Admin: Admin screen | Auditor: Auditor screen
 ↓
Dashboard shows totals, budget, recent transactions   (Fetch + Display)
 ↓
Add Income / Add Expense / Edit / Delete
 ↓
Validate Input                          → invalid: message, back to form
 ↓
Save to SQLite
 ↓
Check budget alert → Refresh dashboard  (Show Updated Transactions)
 ↓
Reports / Export / Settings   (all return to the Dashboard)
 ↓
Logout → Login screen
12. Web Version (Flask) and Vercel
app.py + templates/ is a browser version of the same project. The deployment diagram (client → application server → database) fits this version: browser = client, Flask routes = application server, SQLite = database. All service modules and models.py are reused unchanged; only the screens are new. On Vercel the SQLite file lives in /tmp (temporary) because the project folder is read-only.
13. Viva Questions and Answers
Why SQLite? It needs no server – the whole database is one file, and Python has it built in (sqlite3).
Why are SQL queries written with ?? Parameterized queries stop SQL injection: user input is never joined into the SQL text.
How are passwords protected? We store salt$hash created with PBKDF2-SHA256 (hashlib). The real password is never saved; login hashes the typed password with the same salt and compares.
What is the abstract class here? SystemUser (from the class diagram). It has an abstract method get_role(), so it cannot be created directly; RegularUser, Auditor and Admin inherit from it and implement it (inheritance + polymorphism – main.py calls get_role() to choose the home screen).
Why is there a Transaction class instead of Expense? The diagram's Expense and income have the same fields, so one class with a type avoids duplicate code.
How is the balance calculated? Balance = Total Income − Total Expenses, using SELECT SUM(amount) filtered by type (transactions.get_balance()).
How does the budget alert work? budget.get_budget_status() adds up this month's expenses and compares them with the budget. At 80% or more (check_budget_alert()) a warning is shown if alerts are enabled in Settings.
How does the app avoid crashes on bad input? validation.py raises ValueError with a friendly message; the screens catch it with try/except and show a message box. Database errors are caught with except sqlite3.Error.
Why are dates stored as YYYY-MM-DD? Text in that form sorts and compares correctly in SQL (date >= ?), while the user sees DD-MM-YYYY.
What Python concepts are shown? Variables, conditions, loops, functions, lists, dictionaries, classes and inheritance, abstract classes, exceptions, file handling (CSV), SQL, GUI programming, unit testing.
How would you extend it? Add recurring transactions, an Excel export, or move the service modules behind a Flask REST API (the layered structure already matches the deployment diagram).