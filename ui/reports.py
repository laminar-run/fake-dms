"""Reports section — canned dealership reports with fake loading and old-school output."""
import tkinter as tk
from tkinter import messagebox
import datetime
import random
from ui import style
from ui.widgets import (
    w98_button, w98_label, w98_frame, W98Treeview, w98_scrollbar, title_bar,
)
from db.connection import get_connection


REPORT_DEFS = [
    ("inventory_summary", "Inventory Summary", "Counts of vehicles on the lot grouped by status and by make."),
    ("inventory_aging", "Inventory Aging Report", "In-stock vehicles listed oldest model year first."),
    ("sales_by_salesperson", "Sales by Salesperson", "Deal count and gross by salesperson."),
    ("deal_pipeline", "Deal Pipeline", "Open and closed deals grouped by status."),
    ("ro_summary", "RO Summary by Advisor", "Repair order counts per advisor, type, and status."),
    ("open_ros", "Open Repair Order Aging", "Repair orders not yet closed, oldest first."),
    ("upcoming_appts", "Upcoming Appointment Schedule", "Scheduled appointments for the next 30 days."),
    ("customer_activity", "Customer Activity Log", "Most recent repair order per customer."),
]


def _run_inventory_summary():
    conn = get_connection()
    by_status = conn.execute(
        "SELECT status, COUNT(*) cnt FROM vehicles GROUP BY status ORDER BY cnt DESC").fetchall()
    by_make = conn.execute(
        "SELECT make, COUNT(*) cnt FROM vehicles WHERE status='In Stock' GROUP BY make ORDER BY cnt DESC").fetchall()
    conn.close()
    return [
        ("By Status", ["Status", "Count"], [(r["status"], str(r["cnt"])) for r in by_status]),
        ("In Stock by Make", ["Make", "Count"], [(r["make"], str(r["cnt"])) for r in by_make]),
    ]


def _run_inventory_aging():
    conn = get_connection()
    rows = conn.execute(
        "SELECT stock_no, year, make, model, mileage, price FROM vehicles "
        "WHERE status='In Stock' ORDER BY year ASC, mileage DESC").fetchall()
    conn.close()
    data = [(r["stock_no"], str(r["year"]), r["make"], r["model"], str(r["mileage"]), f"${r['price']:,.0f}") for r in rows]
    return [("In-Stock Inventory (oldest model year first)",
             ["Stock #", "Year", "Make", "Model", "Mileage", "Price"], data)]


def _run_sales_by_salesperson():
    conn = get_connection()
    rows = conn.execute(
        "SELECT salesperson, COUNT(*) cnt, SUM(sale_price) gross FROM deals "
        "GROUP BY salesperson ORDER BY gross DESC").fetchall()
    conn.close()
    data = [(r["salesperson"] or "-", str(r["cnt"]), f"${(r['gross'] or 0):,.0f}") for r in rows]
    return [("Deals by Salesperson", ["Salesperson", "# Deals", "Gross"], data)]


def _run_deal_pipeline():
    conn = get_connection()
    rows = conn.execute(
        "SELECT status, COUNT(*) cnt, SUM(sale_price) gross FROM deals GROUP BY status ORDER BY cnt DESC").fetchall()
    conn.close()
    data = [(r["status"], str(r["cnt"]), f"${(r['gross'] or 0):,.0f}") for r in rows]
    return [("Deal Pipeline by Status", ["Status", "# Deals", "Total Value"], data)]


def _run_ro_summary():
    conn = get_connection()
    rows = conn.execute(
        "SELECT advisor, type, status, COUNT(*) cnt FROM repair_orders "
        "GROUP BY advisor, type, status ORDER BY advisor, cnt DESC").fetchall()
    conn.close()
    data = [(r["advisor"] or "-", r["type"], r["status"], str(r["cnt"])) for r in rows]
    return [("Repair Orders by Advisor / Type / Status", ["Advisor", "Type", "Status", "Count"], data)]


def _run_open_ros():
    conn = get_connection()
    rows = conn.execute(
        "SELECT r.date, r.ro_number, c.last_name, c.first_name, r.advisor, r.concern "
        "FROM repair_orders r JOIN customers c ON r.customer_id=c.id "
        "WHERE r.status IN ('Open','In Progress','Awaiting Parts') ORDER BY r.date ASC").fetchall()
    conn.close()
    data = [(r["date"], r["ro_number"], f"{r['last_name']}, {r['first_name']}", r["advisor"], r["concern"]) for r in rows]
    return [("Open Repair Orders (oldest first)", ["Date", "RO #", "Customer", "Advisor", "Concern"], data)]


def _run_upcoming_appts():
    conn = get_connection()
    today = datetime.date.today().isoformat()
    future = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
    rows = conn.execute(
        "SELECT a.datetime, c.last_name, c.first_name, a.dept, a.advisor, a.reason "
        "FROM appointments a JOIN customers c ON a.customer_id=c.id "
        "WHERE a.datetime >= ? AND a.datetime <= ? AND a.status='Scheduled' ORDER BY a.datetime",
        (today, future + "T23:59")).fetchall()
    conn.close()
    data = [(r["datetime"][:16], f"{r['last_name']}, {r['first_name']}", r["dept"], r["advisor"], r["reason"]) for r in rows]
    return [("Scheduled Appointments - Next 30 Days",
             ["Date/Time", "Customer", "Dept", "Advisor/Sales", "Reason"], data)]


def _run_customer_activity():
    conn = get_connection()
    rows = conn.execute(
        "SELECT c.customer_no, c.first_name, c.last_name, c.salesperson, MAX(r.date) last_ro "
        "FROM customers c LEFT JOIN repair_orders r ON r.customer_id=c.id "
        "GROUP BY c.id ORDER BY last_ro DESC LIMIT 30").fetchall()
    conn.close()
    data = [(r["customer_no"], f"{r['last_name']}, {r['first_name']}", r["salesperson"], r["last_ro"] or "None") for r in rows]
    return [("Customer Activity (Most Recent RO)", ["Cust #", "Customer", "Salesperson", "Last RO"], data)]


RUNNERS = {
    "inventory_summary": _run_inventory_summary,
    "inventory_aging": _run_inventory_aging,
    "sales_by_salesperson": _run_sales_by_salesperson,
    "deal_pipeline": _run_deal_pipeline,
    "ro_summary": _run_ro_summary,
    "open_ros": _run_open_ros,
    "upcoming_appts": _run_upcoming_appts,
    "customer_activity": _run_customer_activity,
}


class ReportsPanel(tk.Frame):
    def __init__(self, parent, dashboard):
        super().__init__(parent, bg=style.BG)
        self.dashboard = dashboard
        self._build()

    def _build(self):
        title_bar(self, "  Reports").pack(fill=tk.X)
        outer = w98_frame(self)
        outer.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        left = w98_frame(outer)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        left.pack_propagate(False)
        left.config(width=270)
        tk.Label(left, text="Available Reports", font=style.FONT_BOLD, bg=style.TITLE_BG,
                 fg="white", pady=4, anchor="w", padx=8).pack(fill=tk.X)
        for key, name, desc in REPORT_DEFS:
            btn_frame = tk.Frame(left, bg=style.BG, relief="groove", bd=1)
            btn_frame.pack(fill=tk.X, padx=4, pady=2)
            tk.Label(btn_frame, text=name, font=style.FONT_BOLD, bg=style.BG, anchor="w", padx=6, pady=2).pack(fill=tk.X)
            tk.Label(btn_frame, text=desc, font=style.FONT_SMALL, bg=style.BG, fg=style.DISABLED_FG,
                     anchor="w", padx=6, wraplength=240, justify="left").pack(fill=tk.X)
            w98_button(btn_frame, "Run Report >", command=lambda k=key, n=name: self._run_report(k, n),
                       name=f"btn_report_{key}", width=14).pack(anchor="e", padx=6, pady=4)

        right = w98_frame(outer)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._output_title = tk.Label(right, text="Select a report from the left panel",
                                      font=style.FONT_TITLE, bg=style.TITLE_BG, fg="white",
                                      anchor="w", padx=8, pady=6)
        self._output_title.pack(fill=tk.X)
        self._meta_lbl = w98_label(right, text="", fg=style.DISABLED_FG)
        self._meta_lbl.pack(anchor="w", padx=6, pady=2)
        self._progress_frame = w98_frame(right)
        self._progress_frame.pack(fill=tk.X, padx=6, pady=4)
        self._notebook_frame = w98_frame(right)
        self._notebook_frame.pack(fill=tk.BOTH, expand=True)

        btn_bar = w98_frame(right)
        btn_bar.pack(fill=tk.X, padx=6, pady=4)
        w98_button(btn_bar, "Print Report", command=self._fake_print, name="btn_print_report", width=13).pack(side=tk.LEFT, padx=3)
        w98_button(btn_bar, "Export to CSV", command=self._fake_export, name="btn_export_report", width=14).pack(side=tk.LEFT, padx=3)
        self._row_count_lbl = w98_label(btn_bar, text="")
        self._row_count_lbl.pack(side=tk.RIGHT, padx=6)
        self._current_report_key = None

    def _run_report(self, key, name):
        self._current_report_key = key
        self._output_title.config(text=f"  {name}")
        self._meta_lbl.config(text="")
        self._row_count_lbl.config(text="")
        for w in self._notebook_frame.winfo_children():
            w.destroy()
        for w in self._progress_frame.winfo_children():
            w.destroy()

        tk.Label(self._progress_frame, text="Generating report, please wait...",
                 font=style.FONT, bg=style.BG).pack(anchor="w")
        bar_bg = tk.Frame(self._progress_frame, bg="#000000", relief="sunken", bd=1, height=14)
        bar_bg.pack(fill=tk.X, pady=2)
        bar_fill = tk.Frame(bar_bg, bg="#000080", height=14, width=0)
        bar_fill.place(x=0, y=0)
        self.dashboard.status_bar.set(f"Running report: {name}...")
        self.update_idletasks()

        def _animate(step=0):
            if step > 20:
                for w in self._progress_frame.winfo_children():
                    w.destroy()
                self._render_report(key)
                return
            total_w = bar_bg.winfo_width() or 400
            bar_fill.config(width=int(total_w * step / 20))
            self._progress_frame.after(40 + random.randint(0, 60), lambda: _animate(step + 1))

        self._progress_frame.after(100, lambda: _animate(0))

    def _render_report(self, key):
        runner = RUNNERS.get(key)
        if not runner:
            return
        sections = runner()
        total_rows = 0
        from tkinter import ttk
        nb = ttk.Notebook(self._notebook_frame, name="report_notebook")
        s = ttk.Style()
        s.configure("TNotebook", background=style.BG)
        s.configure("TNotebook.Tab", background=style.BG, font=style.FONT)
        s.map("TNotebook.Tab", background=[("selected", style.SELECT_BG)], foreground=[("selected", style.SELECT_FG)])
        nb.pack(fill=tk.BOTH, expand=True)

        for section_title, columns, data in sections:
            tab_frame = w98_frame(nb)
            nb.add(tab_frame, text=f"  {section_title[:30]}  ")
            list_f = w98_frame(tab_frame, relief="sunken", bd=2)
            list_f.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
            tree = W98Treeview(list_f, columns=columns, show="headings", selectmode="browse")
            col_w = max(70, 520 // max(len(columns), 1))
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=col_w, anchor="w")
            vsb = w98_scrollbar(list_f, command=tree.yview)
            hsb = w98_scrollbar(list_f, orient=tk.HORIZONTAL, command=tree.xview)
            tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
            tree.grid(row=0, column=0, sticky="nsew")
            vsb.grid(row=0, column=1, sticky="ns")
            hsb.grid(row=1, column=0, sticky="ew")
            list_f.rowconfigure(0, weight=1)
            list_f.columnconfigure(0, weight=1)
            for row_data in data:
                tree.insert("", "end", values=row_data)
                total_rows += 1
            tree.tag_configure("odd", background="#F0F0F8")
            for i, iid in enumerate(tree.get_children()):
                if i % 2 == 1:
                    tree.item(iid, tags=("odd",))

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._meta_lbl.config(text=f"Report generated: {now}   |   {total_rows} total row(s)", fg=style.DISABLED_FG)
        self._row_count_lbl.config(text=f"{total_rows} rows")
        self.dashboard.status_bar.set(f"Report complete - {total_rows} records")

    def _fake_print(self):
        if not self._current_report_key:
            messagebox.showinfo("Print", "Please run a report first.", parent=self)
            return
        messagebox.showinfo("Print",
                            "Sending to printer: \\\\DMSERVER\\HP_LaserJet_4\n\n"
                            "Job queued. Estimated completion: 3-5 minutes.\n"
                            "Please collect your printout from the back office printer.", parent=self)

    def _fake_export(self):
        if not self._current_report_key:
            messagebox.showinfo("Export", "Please run a report first.", parent=self)
            return
        messagebox.showinfo("Export to CSV",
                            "Export complete!\n\n"
                            r"File saved to: C:\DEALERDESK\REPORTS\EXPORT_001.CSV"
                            "\n\nNote: File may be opened with Microsoft Excel 97.", parent=self)
