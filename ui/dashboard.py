import tkinter as tk
from ui import style
from ui.widgets import w98_button, w98_label, w98_frame, title_bar, StatusBar


_SECTION_HOME = "home"
_SECTION_CUSTOMERS = "customers"
_SECTION_INVENTORY = "inventory"
_SECTION_DEALS = "deals"
_SECTION_REPAIR_ORDERS = "repair_orders"
_SECTION_APPOINTMENTS = "appointments"
_SECTION_REPORTS = "reports"
_SECTION_SETTINGS = "settings"


class DashboardWindow(tk.Toplevel):
    """Main application window after login."""

    def __init__(self, master, user: dict, on_logout):
        super().__init__(master)
        self.user = user
        self.on_logout = on_logout
        self.title("DealerDesk 98")
        self.configure(bg=style.BG)
        self.state("zoomed")
        self.protocol("WM_DELETE_WINDOW", self._confirm_exit)

        self._content_frame = None
        self._active_section = None

        self._build()
        self.navigate(_SECTION_HOME)

    def _build(self):
        bar = title_bar(self, "  DealerDesk 98 - Dealership Management System")
        bar.pack(fill=tk.X)

        info_strip = tk.Frame(self, bg="#808080", pady=2)
        info_strip.pack(fill=tk.X)
        w98_label(info_strip,
                  text=f"  Logged in as: {self.user['username']} ({self.user['role'].title()})  ",
                  bg="#808080", fg="white").pack(side=tk.LEFT)
        w98_button(info_strip, "Log Out", command=self._logout,
                   name="btn_logout", width=8).pack(side=tk.RIGHT, padx=4, pady=1)

        body = w98_frame(self)
        body.pack(fill=tk.BOTH, expand=True)

        sidebar = tk.Frame(body, bg=style.BG_DARK, width=160, relief="sunken", bd=2)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="Navigation", font=style.FONT_BOLD,
                 bg=style.BG_DARK, fg="white", pady=6).pack(fill=tk.X)
        tk.Frame(sidebar, bg=style.BG, height=1).pack(fill=tk.X)

        self._nav_btns = {}
        nav_items = [
            ("[H]  Home",          _SECTION_HOME,          "btn_nav_home"),
            ("[C]  Customers",     _SECTION_CUSTOMERS,     "btn_nav_customers"),
            ("[I]  Inventory",     _SECTION_INVENTORY,     "btn_nav_inventory"),
            ("[$]  Deals",         _SECTION_DEALS,         "btn_nav_deals"),
            ("[R]  Repair Orders", _SECTION_REPAIR_ORDERS, "btn_nav_repair_orders"),
            ("[A]  Appointments",  _SECTION_APPOINTMENTS,  "btn_nav_appointments"),
            ("[P]  Reports",       _SECTION_REPORTS,       "btn_nav_reports"),
            ("[*]  Settings",      _SECTION_SETTINGS,      "btn_nav_settings"),
        ]
        for label, section, wname in nav_items:
            btn = tk.Button(
                sidebar, text=label, font=style.FONT,
                bg=style.BG, relief="flat", bd=0,
                anchor="w", padx=10, cursor="arrow",
                activebackground=style.SELECT_BG,
                activeforeground=style.SELECT_FG,
                name=wname,
                command=lambda s=section: self.navigate(s),
            )
            btn.pack(fill=tk.X, pady=1)
            self._nav_btns[section] = btn

        self._content_frame = w98_frame(body, relief="sunken", bd=2)
        self._content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.status_bar = StatusBar(self)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def navigate(self, section: str):
        if self._active_section == section:
            return
        self._active_section = section

        for sec, btn in self._nav_btns.items():
            if sec == section:
                btn.config(bg=style.SELECT_BG, fg=style.SELECT_FG)
            else:
                btn.config(bg=style.BG, fg=style.ENTRY_FG)

        for child in self._content_frame.winfo_children():
            child.destroy()

        if section == _SECTION_HOME:
            from ui.home import HomePanel
            HomePanel(self._content_frame, self).pack(fill=tk.BOTH, expand=True)
            self.status_bar.set("Welcome to DealerDesk 98")

        elif section == _SECTION_CUSTOMERS:
            from ui.customers import CustomerListPanel
            CustomerListPanel(self._content_frame, self).pack(fill=tk.BOTH, expand=True)
            self.status_bar.set("Customers - search or select a record")

        elif section == _SECTION_INVENTORY:
            from ui.inventory import InventoryPanel
            InventoryPanel(self._content_frame, self).pack(fill=tk.BOTH, expand=True)
            self.status_bar.set("Inventory - vehicles on the lot")

        elif section == _SECTION_DEALS:
            from ui.deals import DealListPanel
            DealListPanel(self._content_frame, self).pack(fill=tk.BOTH, expand=True)
            self.status_bar.set("Deals - sales transactions")

        elif section == _SECTION_REPAIR_ORDERS:
            from ui.repair_orders import RepairOrderListPanel
            RepairOrderListPanel(self._content_frame, self).pack(fill=tk.BOTH, expand=True)
            self.status_bar.set("Repair Orders - service department")

        elif section == _SECTION_APPOINTMENTS:
            from ui.appointments import AppointmentListPanel
            AppointmentListPanel(self._content_frame, self).pack(fill=tk.BOTH, expand=True)
            self.status_bar.set("Appointments - service and sales")

        elif section == _SECTION_REPORTS:
            from ui.reports import ReportsPanel
            ReportsPanel(self._content_frame, self).pack(fill=tk.BOTH, expand=True)
            self.status_bar.set("Reports")

        elif section == _SECTION_SETTINGS:
            from ui.settings import SettingsPanel
            SettingsPanel(self._content_frame, self).pack(fill=tk.BOTH, expand=True)
            self.status_bar.set("Settings - chaos engine configuration")

    def _logout(self):
        self.destroy()
        self.on_logout()

    def _confirm_exit(self):
        from tkinter import messagebox
        if messagebox.askyesno("Exit", "Exit DealerDesk 98?", parent=self):
            self.master.destroy()
