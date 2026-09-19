"""
main.py  -  Start the Personal Expense Tracker.   Run:  python main.py

What it does : creates the database (if needed), loads the demo data on the
               first run, opens the window and switches between screens
               (Login -> Dashboard / Admin / Auditor -> Logout -> Login).
Why needed   : it is the single starting point of the whole project.
Talks to     : database.py, auth.py, sample_data.py and all screens in ui/.
Diagram      : Flowchart -> "User Opens App" > "User Logged In?" > Display
               Dashboard ... Logout > End Session
               State diagram -> Idle > Login > Authenticated > Logout
"""

import sys

try:
    import tkinter as tk
except ImportError:
    print("Tkinter is not installed.")
    print("Windows/macOS: reinstall Python from python.org (tick 'tcl/tk').")
    print("Ubuntu/Debian: sudo apt install python3-tk")
    sys.exit(1)

import database
import sample_data
from ui.admin_screen import AdminScreen
from ui.auditor_screen import AuditorScreen
from ui.dashboard import DashboardScreen
from ui.login import LoginScreen


class App(tk.Tk):
    """The main window. It shows ONE screen (frame) at a time."""

    def __init__(self):
        super().__init__()
        self.title("Personal Expense Tracker")
        self.geometry("960x680")
        self.minsize(900, 640)
        self.current_user = None       # set after a successful login
        self.screen = None
        self.show_login()

    def switch_screen(self, screen_class):
        """Remove the old screen and show a new one."""
        if self.screen is not None:
            self.screen.destroy()
        self.screen = screen_class(self, self)
        self.screen.pack(fill="both", expand=True)

    def show_login(self):
        self.current_user = None
        self.switch_screen(LoginScreen)

    def show_home(self, user):
        """After login: each role gets its own home screen."""
        self.current_user = user
        role = user.get_role()
        if role == "admin":
            self.switch_screen(AdminScreen)
        elif role == "auditor":
            self.switch_screen(AuditorScreen)
        else:
            self.switch_screen(DashboardScreen)

    def logout(self):
        """Flowchart: Logout > End Session (back to the login screen)."""
        self.show_login()


def main():
    database.create_database()        # creates database/expense_tracker.db
    sample_data.load_sample_data()    # only does something on the very first run
    App().mainloop()


if __name__ == "__main__":
    main()
