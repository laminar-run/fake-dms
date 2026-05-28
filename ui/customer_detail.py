"""Tabbed customer detail window: Profile | Vehicles | Repair Orders | Deals | Appointments."""
import tkinter as tk
from tkinter import ttk, messagebox
from ui import style
from ui.widgets import (
    w98_button, w98_entry, w98_label, w98_frame, w98_labelframe, W98Treeview, w98_scrollbar, title_bar,
)
from db.connection import get_connection


def _chaos_event(event_type):
    try:
        from chaos.engine import get_engine
        e = get_engine()
        if e:
            e.on_event(event_type)
    except Exception:
        pass


class CustomerDetailWindow(tk.Toplevel):
    def __init__(self, parent, row, on_close=None):
        super().__init__(parent)
        self._customer = dict(row)
        self._on_close = on_close
        self.title(f"Customer: {row['last_name']}, {row['first_name']} - {row['customer_no']}")
        self.configure(bg=style.BG)
        self.geometry("920x640")
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.grab_set()
        self._build()
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build(self):
        c = self._customer
        title_bar(self, f"  {c['last_name']}, {c['first_name']}  | {c['customer_no']}  "
                        f"| {c.get('phone','')}  | {c.get('city','')}, {c.get('state','')}").pack(fill=tk.X)

        nb = ttk.Notebook(self, name="customer_notebook")
        s = ttk.Style()
        s.theme_use("default")
        s.configure("TNotebook", background=style.BG, borderwidth=1)
        s.configure("TNotebook.Tab", background=style.BG, font=style.FONT, padding=(8, 3))
        s.map("TNotebook.Tab", background=[("selected", style.SELECT_BG)],
              foreground=[("selected", style.SELECT_FG)])
        nb.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        for tab_name, builder in [
            ("Profile", self._build_profile), ("Vehicles", self._build_vehicles),
            ("Repair Orders", self._build_ros), ("Deals", self._build_deals),
            ("Appointments", self._build_appts),
        ]:
            frame = w98_frame(nb)
            nb.add(frame, text=f"  {tab_name}  ")
            builder(frame)

        bot = w98_frame(self)
        bot.pack(fill=tk.X, padx=6, pady=4)
        w98_button(bot, "Close", command=self._close, name="btn_close_detail", width=10).pack(side=tk.RIGHT, padx=4)

    def _sel(self, tree):
        sel = tree.selection()
        return int(sel[0]) if sel else None

    # ── Profile ─────────────────────────────────────────────────────────────
    def _build_profile(self, parent):
        frm = w98_labelframe(parent, text="Customer Information")
        frm.pack(padx=10, pady=8, fill=tk.BOTH, expand=True)
        fields = [("Customer #:", "customer_no"), ("First Name:", "first_name"), ("Last Name:", "last_name"),
                  ("Phone:", "phone"), ("Email:", "email"), ("Address:", "address"), ("City:", "city"),
                  ("State:", "state"), ("ZIP:", "zip"), ("Type:", "customer_type"), ("Salesperson:", "salesperson")]
        self._profile_vars = {}
        for i, (label, key) in enumerate(fields):
            r, cc = divmod(i, 2)
            w98_label(frm, text=label).grid(row=r, column=cc * 2, sticky="e", padx=6, pady=3)
            var = tk.StringVar(value=self._customer.get(key, "") or "")
            self._profile_vars[key] = var
            w98_entry(frm, textvariable=var, name=f"profile_{key}", width=28).grid(
                row=r, column=cc * 2 + 1, sticky="w", padx=6, pady=3)
        btn = w98_frame(frm)
        btn.grid(row=len(fields) // 2 + 1, column=0, columnspan=4, pady=8)
        w98_button(btn, "Save Profile", command=self._save_profile, name="btn_save_profile", width=16).pack(side=tk.LEFT, padx=6)

    def _save_profile(self):
        _chaos_event("save")
        vals = {k: v.get().strip() for k, v in self._profile_vars.items()}
        conn = get_connection()
        conn.execute(
            "UPDATE customers SET customer_no=?,first_name=?,last_name=?,phone=?,email=?,address=?,"
            "city=?,state=?,zip=?,customer_type=?,salesperson=? WHERE id=?",
            (vals["customer_no"], vals["first_name"], vals["last_name"], vals["phone"], vals["email"],
             vals["address"], vals["city"], vals["state"], vals["zip"], vals["customer_type"],
             vals["salesperson"], self._customer["id"]))
        conn.commit()
        conn.close()
        self._customer.update(vals)
        messagebox.showinfo("Saved", "Customer profile updated.", parent=self)

    # ── Vehicles ────────────────────────────────────────────────────────────
    def _build_vehicles(self, parent):
        bar = w98_frame(parent)
        bar.pack(fill=tk.X, padx=6, pady=4)
        w98_button(bar, "Add Vehicle", command=self._add_vehicle, name="btn_add_vehicle", width=12).pack(side=tk.LEFT, padx=3)
        w98_button(bar, "Edit", command=self._edit_vehicle, name="btn_edit_vehicle_cd", width=8).pack(side=tk.LEFT, padx=3)
        w98_button(bar, "Delete", command=self._delete_vehicle, name="btn_delete_vehicle_cd", width=8).pack(side=tk.LEFT, padx=3)
        lf = w98_frame(parent, relief="sunken", bd=2)
        lf.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)
        cols = ("stock_no", "year", "make", "model", "mileage", "status")
        self._veh_tree = W98Treeview(lf, columns=cols, show="headings", name="cust_vehicle_tree", selectmode="browse")
        for c, h, w in [("stock_no", "Stock #", 80), ("year", "Year", 55), ("make", "Make", 90),
                        ("model", "Model", 130), ("mileage", "Mileage", 80), ("status", "Status", 110)]:
            self._veh_tree.heading(c, text=h)
            self._veh_tree.column(c, width=w, anchor="w")
        vsb = w98_scrollbar(lf, command=self._veh_tree.yview)
        self._veh_tree.configure(yscrollcommand=vsb.set)
        self._veh_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        lf.rowconfigure(0, weight=1)
        lf.columnconfigure(0, weight=1)
        self._veh_tree.bind("<Double-1>", lambda e: self._edit_vehicle())
        self._refresh_vehicles()

    def _refresh_vehicles(self):
        conn = get_connection()
        rows = conn.execute("SELECT * FROM vehicles WHERE customer_id=? ORDER BY year DESC",
                            (self._customer["id"],)).fetchall()
        conn.close()
        self._veh_tree.delete(*self._veh_tree.get_children())
        for r in rows:
            self._veh_tree.insert("", "end", iid=str(r["id"]),
                                  values=(r["stock_no"], r["year"], r["make"], r["model"], r["mileage"], r["status"]))

    def _add_vehicle(self):
        from ui.inventory import VehicleFormDialog
        VehicleFormDialog(self, None, on_save=self._refresh_vehicles, preset_customer_id=self._customer["id"])

    def _edit_vehicle(self):
        vid = self._sel(self._veh_tree)
        if not vid:
            messagebox.showinfo("Select", "Select a vehicle first.", parent=self)
            return
        conn = get_connection()
        row = conn.execute("SELECT * FROM vehicles WHERE id=?", (vid,)).fetchone()
        conn.close()
        from ui.inventory import VehicleFormDialog
        VehicleFormDialog(self, row, on_save=self._refresh_vehicles)

    def _delete_vehicle(self):
        vid = self._sel(self._veh_tree)
        if not vid:
            messagebox.showinfo("Select", "Select a vehicle first.", parent=self)
            return
        if messagebox.askyesno("Delete", "Delete this vehicle?", parent=self):
            conn = get_connection()
            conn.execute("DELETE FROM vehicles WHERE id=?", (vid,))
            conn.commit()
            conn.close()
            self._refresh_vehicles()

    # ── Repair Orders ───────────────────────────────────────────────────────
    def _build_ros(self, parent):
        bar = w98_frame(parent)
        bar.pack(fill=tk.X, padx=6, pady=4)
        w98_button(bar, "New Repair Order", command=self._new_ro, name="btn_new_ro_cd", width=16).pack(side=tk.LEFT, padx=3)
        w98_button(bar, "Edit", command=self._edit_ro, name="btn_edit_ro_cd", width=8).pack(side=tk.LEFT, padx=3)
        w98_button(bar, "Delete", command=self._delete_ro, name="btn_delete_ro_cd", width=8).pack(side=tk.LEFT, padx=3)
        lf = w98_frame(parent, relief="sunken", bd=2)
        lf.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)
        cols = ("ro_number", "date", "type", "advisor", "status")
        self._ro_tree = W98Treeview(lf, columns=cols, show="headings", name="cust_ro_tree", selectmode="browse")
        for c, h, w in [("ro_number", "RO #", 90), ("date", "Date", 100), ("type", "Type", 130),
                        ("advisor", "Advisor", 130), ("status", "Status", 100)]:
            self._ro_tree.heading(c, text=h)
            self._ro_tree.column(c, width=w, anchor="w")
        vsb = w98_scrollbar(lf, command=self._ro_tree.yview)
        self._ro_tree.configure(yscrollcommand=vsb.set)
        self._ro_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        lf.rowconfigure(0, weight=1)
        lf.columnconfigure(0, weight=1)
        self._ro_tree.bind("<Double-1>", lambda e: self._edit_ro())
        self._refresh_ros()

    def _refresh_ros(self):
        conn = get_connection()
        rows = conn.execute("SELECT * FROM repair_orders WHERE customer_id=? ORDER BY date DESC",
                            (self._customer["id"],)).fetchall()
        conn.close()
        self._ro_tree.delete(*self._ro_tree.get_children())
        for r in rows:
            self._ro_tree.insert("", "end", iid=str(r["id"]),
                                 values=(r["ro_number"], r["date"], r["type"], r["advisor"], r["status"]))

    def _new_ro(self):
        _chaos_event("new_ro")
        from ui.repair_orders import RepairOrderFormDialog
        RepairOrderFormDialog(self, None, on_save=self._refresh_ros, preset_customer=self._customer)

    def _edit_ro(self):
        rid = self._sel(self._ro_tree)
        if not rid:
            messagebox.showinfo("Select", "Select a repair order first.", parent=self)
            return
        conn = get_connection()
        row = conn.execute("SELECT * FROM repair_orders WHERE id=?", (rid,)).fetchone()
        conn.close()
        from ui.repair_orders import RepairOrderFormDialog
        RepairOrderFormDialog(self, row, on_save=self._refresh_ros, preset_customer=self._customer)

    def _delete_ro(self):
        rid = self._sel(self._ro_tree)
        if not rid:
            messagebox.showinfo("Select", "Select a repair order first.", parent=self)
            return
        if messagebox.askyesno("Delete", "Delete this repair order?", parent=self):
            conn = get_connection()
            conn.execute("DELETE FROM repair_orders WHERE id=?", (rid,))
            conn.commit()
            conn.close()
            self._refresh_ros()

    # ── Deals ───────────────────────────────────────────────────────────────
    def _build_deals(self, parent):
        bar = w98_frame(parent)
        bar.pack(fill=tk.X, padx=6, pady=4)
        w98_button(bar, "New Deal", command=self._new_deal, name="btn_new_deal_cd", width=12).pack(side=tk.LEFT, padx=3)
        w98_button(bar, "Edit", command=self._edit_deal, name="btn_edit_deal_cd", width=8).pack(side=tk.LEFT, padx=3)
        w98_button(bar, "Delete", command=self._delete_deal, name="btn_delete_deal_cd", width=8).pack(side=tk.LEFT, padx=3)
        lf = w98_frame(parent, relief="sunken", bd=2)
        lf.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)
        cols = ("deal_number", "date", "deal_type", "sale_price", "status")
        self._deal_tree = W98Treeview(lf, columns=cols, show="headings", name="cust_deal_tree", selectmode="browse")
        for c, h, w in [("deal_number", "Deal #", 90), ("date", "Date", 100), ("deal_type", "Type", 90),
                        ("sale_price", "Sale Price", 110), ("status", "Status", 100)]:
            self._deal_tree.heading(c, text=h)
            self._deal_tree.column(c, width=w, anchor="w")
        vsb = w98_scrollbar(lf, command=self._deal_tree.yview)
        self._deal_tree.configure(yscrollcommand=vsb.set)
        self._deal_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        lf.rowconfigure(0, weight=1)
        lf.columnconfigure(0, weight=1)
        self._deal_tree.bind("<Double-1>", lambda e: self._edit_deal())
        self._refresh_deals()

    def _refresh_deals(self):
        conn = get_connection()
        rows = conn.execute("SELECT * FROM deals WHERE customer_id=? ORDER BY date DESC",
                            (self._customer["id"],)).fetchall()
        conn.close()
        self._deal_tree.delete(*self._deal_tree.get_children())
        for r in rows:
            self._deal_tree.insert("", "end", iid=str(r["id"]),
                                   values=(r["deal_number"], r["date"], r["deal_type"],
                                           f"${r['sale_price']:,.0f}", r["status"]))

    def _new_deal(self):
        from ui.deals import DealFormDialog
        DealFormDialog(self, None, on_save=self._refresh_deals, preset_customer=self._customer)

    def _edit_deal(self):
        did = self._sel(self._deal_tree)
        if not did:
            messagebox.showinfo("Select", "Select a deal first.", parent=self)
            return
        conn = get_connection()
        row = conn.execute("SELECT * FROM deals WHERE id=?", (did,)).fetchone()
        conn.close()
        from ui.deals import DealFormDialog
        DealFormDialog(self, row, on_save=self._refresh_deals, preset_customer=self._customer)

    def _delete_deal(self):
        did = self._sel(self._deal_tree)
        if not did:
            messagebox.showinfo("Select", "Select a deal first.", parent=self)
            return
        if messagebox.askyesno("Delete", "Delete this deal?", parent=self):
            conn = get_connection()
            conn.execute("DELETE FROM deals WHERE id=?", (did,))
            conn.commit()
            conn.close()
            self._refresh_deals()

    # ── Appointments ────────────────────────────────────────────────────────
    def _build_appts(self, parent):
        bar = w98_frame(parent)
        bar.pack(fill=tk.X, padx=6, pady=4)
        w98_button(bar, "New Appointment", command=self._new_appt, name="btn_new_appt_cd", width=16).pack(side=tk.LEFT, padx=3)
        w98_button(bar, "Edit", command=self._edit_appt, name="btn_edit_appt_cd", width=8).pack(side=tk.LEFT, padx=3)
        w98_button(bar, "Delete", command=self._delete_appt, name="btn_delete_appt_cd", width=8).pack(side=tk.LEFT, padx=3)
        lf = w98_frame(parent, relief="sunken", bd=2)
        lf.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)
        cols = ("datetime", "dept", "advisor", "reason", "status")
        self._appt_tree = W98Treeview(lf, columns=cols, show="headings", name="cust_appt_tree", selectmode="browse")
        for c, h, w in [("datetime", "Date/Time", 140), ("dept", "Dept", 80), ("advisor", "Advisor/Sales", 130),
                        ("reason", "Reason", 160), ("status", "Status", 90)]:
            self._appt_tree.heading(c, text=h)
            self._appt_tree.column(c, width=w, anchor="w")
        vsb = w98_scrollbar(lf, command=self._appt_tree.yview)
        self._appt_tree.configure(yscrollcommand=vsb.set)
        self._appt_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        lf.rowconfigure(0, weight=1)
        lf.columnconfigure(0, weight=1)
        self._appt_tree.bind("<Double-1>", lambda e: self._edit_appt())
        self._refresh_appts()

    def _refresh_appts(self):
        conn = get_connection()
        rows = conn.execute("SELECT * FROM appointments WHERE customer_id=? ORDER BY datetime DESC",
                            (self._customer["id"],)).fetchall()
        conn.close()
        self._appt_tree.delete(*self._appt_tree.get_children())
        for r in rows:
            self._appt_tree.insert("", "end", iid=str(r["id"]),
                                   values=(r["datetime"], r["dept"], r["advisor"], r["reason"], r["status"]))

    def _new_appt(self):
        from ui.appointments import AppointmentFormDialog
        AppointmentFormDialog(self, None, on_save=self._refresh_appts, preset_customer=self._customer)

    def _edit_appt(self):
        aid = self._sel(self._appt_tree)
        if not aid:
            messagebox.showinfo("Select", "Select an appointment first.", parent=self)
            return
        conn = get_connection()
        row = conn.execute("SELECT * FROM appointments WHERE id=?", (aid,)).fetchone()
        conn.close()
        from ui.appointments import AppointmentFormDialog
        AppointmentFormDialog(self, row, on_save=self._refresh_appts, preset_customer=self._customer)

    def _delete_appt(self):
        aid = self._sel(self._appt_tree)
        if not aid:
            messagebox.showinfo("Select", "Select an appointment first.", parent=self)
            return
        if messagebox.askyesno("Delete", "Delete this appointment?", parent=self):
            conn = get_connection()
            conn.execute("DELETE FROM appointments WHERE id=?", (aid,))
            conn.commit()
            conn.close()
            self._refresh_appts()

    def _close(self):
        if self._on_close:
            self._on_close()
        self.destroy()
