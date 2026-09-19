# Personal Expense Tracker

A simple and user-friendly desktop application developed in Python for managing personal income, expenses, budgets, and financial reports. The application provides authentication, transaction management, budget tracking, graphical reports, CSV export, administrative controls, and auditing features.

## 📌 Project Description

Managing personal finances manually can make it difficult to track spending patterns, monitor budgets, and understand overall financial status.

The **Personal Expense Tracker** provides a centralized desktop application where users can record their income and expenses, organize transactions into categories, set monthly budgets, analyze their financial activity, and generate reports.

The application also provides separate **Admin** and **Auditor** functionalities for account management, system monitoring, and audit reporting.

## ✨ Features

### 👤 User Authentication

- User registration
- User login
- Password hashing with salt
- Account activation/deactivation
- Role-based access
- Secure authentication validation

### 💰 Expense Management

Users can:

- Add expenses
- Edit expenses
- Delete expenses
- View expense history
- Search transactions
- Filter transactions
- Categorize expenses
- Filter transactions by date range

Supported expense categories include:

- Food
- Transport
- Education
- Shopping
- Entertainment
- Bills
- Medical
- Other

### 💵 Income Management

Users can record different sources of income, including:

- Salary
- Pocket Money
- Scholarship
- Gift
- Other

The application maintains income and expense records together and calculates the user's current financial balance.

### 📊 Dashboard

The dashboard provides an overview of the user's financial information, including:

- Total income
- Total expenses
- Current balance
- Monthly budget
- Amount spent
- Remaining budget
- Budget utilization

The balance is calculated using:

```text
Balance = Total Income - Total Expenses


