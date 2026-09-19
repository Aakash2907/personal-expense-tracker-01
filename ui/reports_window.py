"""
ui/reports_window.py  -  View reports, charts and export them.

What it does : the user chooses Summary, Category Breakdown or Trend Analysis
               (and an optional date range), sees the report text and a
               Matplotlib chart, and can export it as PDF or CSV.
Why needed   : "View Report", "Generate Report" and "Export Data" in the
               use case diagram; "Generate Reports > Select Report Type >
               Display Report & Charts > Export Report?" in the flowchart.
Talks to     : models.py (Report class), reports.py (charts + export),
               matplotlib (only for drawing the chart on screen).
Diagram      : Flowchart -> View Reports branch
               State diagram -> GenerateReport > GeneratingReport
               Use case -> View Report <<include>> Generate Report
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from models import Report
from reports import REPORT_TYPES, export_report_csv, export_report_pdf, make_figure
from ui.widgets import center_window

try:                                    # charts need matplotlib
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    CHARTS_AVAILABLE = True
except ImportError:
    CHARTS_AVAILABLE = False


class ReportsWindow(tk.Toplevel):
    def __init__(self, parent, user):
        super().__init__(parent)
        self.user = user
        self.report = None              # the last generated report (dictionary)
        self.canvas = None              # the chart currently on screen
        self.title("Reports")
        center_window(self, 1000, 600)

        self.type_var = tk.StringVar(value=REPORT_TYPES[0])
        self.from_var = tk.StringVar()
        self.to_var = tk.StringVar()

        # ---- top row: choose report ----
        controls = ttk.Frame(self, padding=8)
        controls.pack(fill="x")
        ttk.Label(controls, text="Report type:").pack(side="left")
        ttk.Combobox(controls, textvariable=self.type_var, values=REPORT_TYPES,
                     width=18, state="readonly").pack(side="left", padx=(4, 12))
        ttk.Label(controls, text="From (DD-MM-YYYY):").pack(side="left")
        ttk.Entry(controls, textvariable=self.from_var, width=12).pack(side="left", padx=(4, 8))
        ttk.Label(controls, text="To:").pack(side="left")
        ttk.Entry(controls, textvariable=self.to_var, width=12).pack(side="left", padx=(4, 12))
        ttk.Button(controls, text="Generate Report", command=self.generate).pack(side="left", padx=4)
        self.pdf_button = ttk.Button(controls, text="Export PDF", state="disabled",
                                     command=lambda: self.export("pdf"))
        self.pdf_button.pack(side="left", padx=4)
        self.csv_button = ttk.Button(controls, text="Export CSV", state="disabled",
                                     command=lambda: self.export("csv"))
        self.csv_button.pack(side="left", padx=4)

        # ---- report text (left) and chart (right) ----
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.text_box = tk.Text(body, width=52, font=("Courier", 10), state="disabled")
        self.text_box.pack(side="left", fill="y")
        self.chart_frame = ttk.Frame(body)
        self.chart_frame.pack(side="left", fill="both", expand=True, padx=(8, 0))

        self.generate()                 # show the Summary report straight away

    def generate(self):
        """Create the report, show the text and draw the chart."""
        report = Report(self.user.user_id, self.type_var.get(),
                        self.from_var.get(), self.to_var.get())
        try:
            report.generate_report()
        except ValueError as error:     # e.g. invalid date
            messagebox.showerror("Report Error", str(error), parent=self)
            return
        self.report = report.data
        self.show_text(report.view_report())
        self.show_chart()
        self.pdf_button.config(state="normal")
        self.csv_button.config(state="normal")

    def show_text(self, text):
        self.text_box.config(state="normal")
        self.text_box.delete("1.0", "end")
        self.text_box.insert("end", text)
        self.text_box.config(state="disabled")

    def show_chart(self):
        for widget in self.chart_frame.winfo_children():  # remove the old chart
            widget.destroy()
        self.canvas = None
        if not CHARTS_AVAILABLE:
            ttk.Label(self.chart_frame,
                      text="Install matplotlib to see charts:\npip install matplotlib").pack()
            return
        self.canvas = FigureCanvasTkAgg(make_figure(self.report), master=self.chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def export(self, kind):
        """Export Report? Yes -> save as PDF or CSV."""
        if self.report is None:
            return
        path = filedialog.asksaveasfilename(
            parent=self, title="Export Report", defaultextension="." + kind,
            filetypes=[(kind.upper() + " files", "*." + kind)],
            initialfile="report." + kind)
        if not path:
            return
        try:
            if kind == "pdf":
                export_report_pdf(self.report, path)
            else:
                export_report_csv(self.report, path)
        except (OSError, ImportError):
            messagebox.showerror("Export Failed", "The report could not be saved.", parent=self)
            return
        messagebox.showinfo("Export Successful", "Report saved to:\n" + path, parent=self)
