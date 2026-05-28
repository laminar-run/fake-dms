"""Hilariously old-school Windows 98 home / welcome screen for DealerDesk 98."""
import tkinter as tk
import datetime
import random
from ui import style
from ui.widgets import w98_frame, w98_label, title_bar
from db.connection import get_connection


TIPS = [
    "TIP: Always log out when leaving your workstation!",
    "TIP: Back up the deal jacket to a floppy disk regularly.",
    "TIP: Use DealerDesk 98 for all your sales and service needs!",
    "TIP: Contact your system administrator if you experience any issues.",
    "TIP: Press F1 at any time for help (F1 key may not be implemented).",
    "TIP: DealerDesk 98 is Y2K compliant!",
    "TIP: For best performance, close all other programs before printing an RO.",
    "TIP: Remember to defragment your hard drive monthly for optimal speed.",
    "TIP: DealerDesk 98 supports up to 640KB of customer records.",
    "TIP: Do NOT share your password with anyone, including the F&I office.",
    "TIP: If the screen freezes, wait 3-10 seconds before calling support.",
    "TIP: Always verify the VIN before finalizing a deal.",
]

NOTICES = [
    "NOTICE: Scheduled maintenance window: Sunday 2:00AM - 2:15AM",
    "NOTICE: New manufacturer incentives loaded. See F&I for floppy disk.",
    "NOTICE: Please do not place coffee on top of the deal printer.",
    "NOTICE: Service drive printer requires 5 minutes warmup time.",
    "NOTICE: DealerDesk 98 Service Pack 2 now available on CD-ROM.",
]

SYSTEM_MODULES = [
    ("Inventory Database", True),
    ("Deal Desk Engine", True),
    ("Service Scheduler", True),
    ("F&I Gateway", False),
    ("DMV / Title Bridge", False),
    ("Credit Bureau Link", False),
    ("Parts Catalog", True),
    ("CRM Sync Service", True),
    ("Manufacturer Warranty Feed", False),
]

MARQUEE_MSG = (
    "  *** WELCOME TO DEALERDESK 98 ***   "
    "  Please do not turn off your computer while deals are being saved.   "
    "  For technical support call 1-800-555-0199 (hold time: approx 45 min)   "
    "  *** Have a productive and profitable day on the lot! ***   "
)


def _get_stats():
    try:
        conn = get_connection()
        customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        in_stock = conn.execute("SELECT COUNT(*) FROM vehicles WHERE status='In Stock'").fetchone()[0]
        open_ros = conn.execute(
            "SELECT COUNT(*) FROM repair_orders WHERE status IN ('Open','In Progress','Awaiting Parts')"
        ).fetchone()[0]
        month = datetime.date.today().strftime("%Y-%m")
        deals_mtd = conn.execute(
            "SELECT COUNT(*) FROM deals WHERE date LIKE ?", (month + "%",)
        ).fetchone()[0]
        conn.close()
        return customers, in_stock, open_ros, deals_mtd
    except Exception:
        return 0, 0, 0, 0


class HomePanel(tk.Frame):
    def __init__(self, parent, dashboard):
        super().__init__(parent, bg=style.BG)
        self.dashboard = dashboard
        self._marquee_offset = 0
        self._blink_state = True
        self._build()
        self._start_clock()
        self._start_marquee()
        self._start_blink()

    def _build(self):
        title_bar(self, "  DealerDesk 98 — Home").pack(fill=tk.X)

        marquee_frame = tk.Frame(self, bg="#000080", pady=2)
        marquee_frame.pack(fill=tk.X)
        self._marquee_lbl = tk.Label(
            marquee_frame, text="", font=("Courier New", 8), bg="#000080", fg="yellow",
            anchor="w", padx=4,
        )
        self._marquee_lbl.pack(fill=tk.X)

        body = w98_frame(self)
        body.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        col1 = w98_frame(body)
        col1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        col2 = w98_frame(body)
        col2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
        col3 = w98_frame(body)
        col3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))

        # Col 1: banner + clock + stats
        banner_frame = tk.Frame(col1, bg="#000080", relief="ridge", bd=3)
        banner_frame.pack(fill=tk.X, pady=(0, 6))
        tk.Label(banner_frame, text="DealerDesk", font=("MS Sans Serif", 22, "bold"),
                 bg="#000080", fg="#FFFFFF", pady=4).pack()
        tk.Label(banner_frame, text="98", font=("MS Sans Serif", 18, "bold"),
                 bg="#000080", fg="#FFFF00").pack()
        tk.Label(banner_frame, text="Dealership Management System", font=("MS Sans Serif", 7),
                 bg="#000080", fg="#C0C0C0", pady=2).pack()

        self._blink_lbl = tk.Label(col1, text="*  WELCOME  *", font=("MS Sans Serif", 10, "bold"),
                                   bg=style.BG, fg="#FF0000", pady=4)
        self._blink_lbl.pack()

        clock_lf = tk.LabelFrame(col1, text="System Clock", font=style.FONT_BOLD,
                                 bg=style.BG, fg=style.ENTRY_FG, relief="groove", bd=2)
        clock_lf.pack(fill=tk.X, pady=6)
        self._clock_lbl = tk.Label(clock_lf, text="", font=("Courier New", 14, "bold"),
                                   bg="#000000", fg="#00FF00", pady=6)
        self._clock_lbl.pack(fill=tk.X, padx=4, pady=4)
        self._date_lbl = tk.Label(clock_lf, text="", font=("Courier New", 8),
                                  bg="#000000", fg="#00CC00")
        self._date_lbl.pack(fill=tk.X, padx=4, pady=(0, 4))

        stats_lf = tk.LabelFrame(col1, text="Quick Statistics", font=style.FONT_BOLD,
                                 bg=style.BG, fg=style.ENTRY_FG, relief="groove", bd=2)
        stats_lf.pack(fill=tk.X, pady=6)
        customers, in_stock, open_ros, deals_mtd = _get_stats()
        stats = [
            ("Total Customers:", str(customers)),
            ("Vehicles In Stock:", str(in_stock)),
            ("Open Repair Orders:", str(open_ros)),
            ("Deals This Month:", str(deals_mtd)),
            ("DB Status:", "ONLINE"),
            ("License:", "REGISTERED"),
            ("Version:", "3.2.0 (Build 9812)"),
        ]
        for label, value in stats:
            row = w98_frame(stats_lf)
            row.pack(fill=tk.X, padx=6, pady=1)
            tk.Label(row, text=label, font=style.FONT, bg=style.BG, anchor="w", width=18).pack(side=tk.LEFT)
            color = "#008000" if value in ("ONLINE", "REGISTERED") else style.ENTRY_FG
            tk.Label(row, text=value, font=style.FONT_BOLD, bg=style.BG, fg=color, anchor="w").pack(side=tk.LEFT)

        # Col 2: module status + perf
        modules_lf = tk.LabelFrame(col2, text="System Module Status", font=style.FONT_BOLD,
                                   bg=style.BG, fg=style.ENTRY_FG, relief="groove", bd=2)
        modules_lf.pack(fill=tk.X, pady=(0, 6))
        for module, online in SYSTEM_MODULES:
            row = w98_frame(modules_lf)
            row.pack(fill=tk.X, padx=6, pady=2)
            tk.Label(row, text="*", font=("Courier New", 10), bg=style.BG,
                     fg="#00CC00" if online else "#CC0000").pack(side=tk.LEFT)
            tk.Label(row, text=f" [{'ONLINE ' if online else 'OFFLINE'}]", font=("Courier New", 8),
                     bg=style.BG, fg="#00CC00" if online else "#CC0000", width=10, anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=module, font=style.FONT, bg=style.BG, anchor="w").pack(side=tk.LEFT)

        perf_lf = tk.LabelFrame(col2, text="Server Performance", font=style.FONT_BOLD,
                                bg=style.BG, fg=style.ENTRY_FG, relief="groove", bd=2)
        perf_lf.pack(fill=tk.X, pady=6)
        for label, pct, color in [("CPU Usage:", 23, "#00CC00"), ("Memory:", 67, "#FFCC00"),
                                  ("Disk I/O:", 12, "#00CC00"), ("Network:", 8, "#00CC00"),
                                  ("DB Connections:", 3, "#00CC00")]:
            row = w98_frame(perf_lf)
            row.pack(fill=tk.X, padx=6, pady=2)
            tk.Label(row, text=label, font=style.FONT_SMALL, bg=style.BG, width=16, anchor="e").pack(side=tk.LEFT)
            bar_bg = tk.Frame(row, bg="#000000", width=120, height=12, relief="sunken", bd=1)
            bar_bg.pack(side=tk.LEFT, padx=4)
            bar_bg.pack_propagate(False)
            tk.Frame(bar_bg, bg=color, width=max(2, int(120 * pct / 100)), height=12).place(x=0, y=0)
            tk.Label(row, text=f"{pct}%", font=style.FONT_SMALL, bg=style.BG, width=4).pack(side=tk.LEFT)

        # Col 3: notices + tips + recent
        notice_lf = tk.LabelFrame(col3, text="System Notices", font=style.FONT_BOLD,
                                  bg="#FFFFC0", fg="#CC0000", relief="groove", bd=2)
        notice_lf.pack(fill=tk.X, pady=(0, 6))
        for notice in NOTICES:
            tk.Label(notice_lf, text=notice, font=style.FONT_SMALL, bg="#FFFFC0", fg="#333333",
                     anchor="w", wraplength=220, justify="left", pady=1, padx=4).pack(fill=tk.X)

        tip_lf = tk.LabelFrame(col3, text="Tip of the Day", font=style.FONT_BOLD,
                               bg="#E0FFE0", fg="#006600", relief="groove", bd=2)
        tip_lf.pack(fill=tk.X, pady=6)
        self._tip_lbl = tk.Label(tip_lf, text=random.choice(TIPS), font=style.FONT,
                                 bg="#E0FFE0", fg="#004400", wraplength=220, justify="left", padx=6, pady=6)
        self._tip_lbl.pack(fill=tk.X)
        from ui.widgets import w98_button
        w98_button(tip_lf, "Next Tip >>", command=self._next_tip, name="btn_next_tip", width=12).pack(pady=(0, 6))

        activity_lf = tk.LabelFrame(col3, text="Recent Service Activity", font=style.FONT_BOLD,
                                    bg=style.BG, fg=style.ENTRY_FG, relief="groove", bd=2)
        activity_lf.pack(fill=tk.BOTH, expand=True, pady=6)
        try:
            conn = get_connection()
            recent = conn.execute(
                "SELECT c.last_name, c.first_name, r.date, r.type FROM repair_orders r "
                "JOIN customers c ON r.customer_id=c.id ORDER BY r.date DESC LIMIT 6"
            ).fetchall()
            conn.close()
            for r in recent:
                txt = f"{r['date']}  {r['last_name']}, {r['first_name'][:1]}.  [{r['type']}]"
                tk.Label(activity_lf, text=txt, font=style.FONT_SMALL, bg=style.BG,
                         anchor="w", padx=6).pack(fill=tk.X)
        except Exception:
            pass

        strip = tk.Frame(self, bg="#808080", pady=3)
        strip.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Label(strip,
                 text="  DealerDesk 98  |  (c) 1998 AutoSoft Systems Inc.  |  All Rights Reserved  "
                      "|  Unauthorized access is prohibited and will be prosecuted  ",
                 font=("MS Sans Serif", 7), bg="#808080", fg="white").pack(side=tk.LEFT)

    def _start_clock(self):
        def _tick():
            if not self.winfo_exists():
                return
            now = datetime.datetime.now()
            self._clock_lbl.config(text=now.strftime(" %H:%M:%S "))
            self._date_lbl.config(text=now.strftime(" %A, %B %d, %Y "))
            self.after(1000, _tick)
        _tick()

    def _start_marquee(self):
        msg = MARQUEE_MSG * 3
        width = 80

        def _scroll():
            if not self.winfo_exists():
                return
            self._marquee_offset = (self._marquee_offset + 1) % len(MARQUEE_MSG)
            display = (msg + msg)[self._marquee_offset:self._marquee_offset + width]
            self._marquee_lbl.config(text=display)
            self.after(80, _scroll)
        _scroll()

    def _start_blink(self):
        def _blink():
            if not self.winfo_exists():
                return
            self._blink_state = not self._blink_state
            self._blink_lbl.config(fg="#FF0000" if self._blink_state else style.BG)
            self.after(600, _blink)
        _blink()

    def _next_tip(self):
        self._tip_lbl.config(text=random.choice(TIPS))
