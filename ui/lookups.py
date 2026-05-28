"""Reusable Customer and Vehicle lookup popups (used by deals, repair orders, appointments)."""
import tkinter as tk
from ui import style
from ui.widgets import (
    w98_button, w98_entry, w98_label, w98_frame, W98Treeview, w98_scrollbar, title_bar,
)
from db.connection import get_connection


class CustomerLookupDialog(tk.Toplevel):
    def __init__(self, parent, on_select):
        super().__init__(parent)
        self.on_select = on_select
        self.title("Customer Lookup")
        self.configure(bg=style.BG)
        self.geometry("520x380")
        self.grab_set()
        self._rows = {}
        self._build()

    def _build(self):
        title_bar(self, "  Customer Lookup").pack(fill=tk.X)
        bar = w98_frame(self)
        bar.pack(fill=tk.X, padx=6, pady=4)
        w98_label(bar, text="Search:").pack(side=tk.LEFT)
        self._sv = tk.StringVar()
        se = w98_entry(bar, textvariable=self._sv, name="cust_lookup_search", width=28)
        se.pack(side=tk.LEFT, padx=4)
        w98_button(bar, "Go", command=self._search, name="btn_cust_lookup_go", width=6).pack(side=tk.LEFT)
        se.bind("<Return>", lambda e: self._search())

        list_f = w98_frame(self, relief="sunken", bd=2)
        list_f.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)
        cols = ("customer_no", "last_name", "first_name", "phone", "city")
        self._tree = W98Treeview(list_f, columns=cols, show="headings",
                                 name="cust_lookup_tree", selectmode="browse")
        for c, h, w in [("customer_no", "Cust #", 80), ("last_name", "Last", 110),
                        ("first_name", "First", 100), ("phone", "Phone", 110), ("city", "City", 90)]:
            self._tree.heading(c, text=h)
            self._tree.column(c, width=w)
        vsb = w98_scrollbar(list_f, command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        list_f.rowconfigure(0, weight=1)
        list_f.columnconfigure(0, weight=1)
        self._tree.bind("<Double-1>", lambda e: self._select())

        btn = w98_frame(self)
        btn.pack(pady=6)
        w98_button(btn, "Select", command=self._select, name="btn_cust_lookup_select", width=10).pack(side=tk.LEFT, padx=6)
        w98_button(btn, "Cancel", command=self.destroy, name="btn_cust_lookup_cancel", width=10).pack(side=tk.LEFT, padx=6)
        self._search()
        se.focus_set()

    def _search(self):
        q = self._sv.get().strip()
        conn = get_connection()
        if q:
            like = f"%{q}%"
            rows = conn.execute(
                "SELECT * FROM customers WHERE first_name LIKE ? OR last_name LIKE ? "
                "OR customer_no LIKE ? OR phone LIKE ? ORDER BY last_name",
                (like, like, like, like)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM customers ORDER BY last_name").fetchall()
        conn.close()
        self._tree.delete(*self._tree.get_children())
        self._rows = {}
        for r in rows:
            self._tree.insert("", "end", iid=str(r["id"]),
                              values=(r["customer_no"], r["last_name"], r["first_name"], r["phone"], r["city"]))
            self._rows[r["id"]] = dict(r)

    def _select(self):
        sel = self._tree.selection()
        if not sel:
            return
        self.on_select(self._rows[int(sel[0])])
        self.destroy()


class VehicleLookupDialog(tk.Toplevel):
    def __init__(self, parent, on_select, where_status=None, customer_id=None):
        super().__init__(parent)
        self.on_select = on_select
        self._where_status = where_status
        self._customer_id = customer_id
        self.title("Vehicle Lookup")
        self.configure(bg=style.BG)
        self.geometry("640x380")
        self.grab_set()
        self._rows = {}
        self._build()

    def _build(self):
        title_bar(self, "  Vehicle Lookup").pack(fill=tk.X)
        bar = w98_frame(self)
        bar.pack(fill=tk.X, padx=6, pady=4)
        w98_label(bar, text="Search:").pack(side=tk.LEFT)
        self._sv = tk.StringVar()
        se = w98_entry(bar, textvariable=self._sv, name="veh_lookup_search", width=30)
        se.pack(side=tk.LEFT, padx=4)
        w98_button(bar, "Go", command=self._search, name="btn_veh_lookup_go", width=6).pack(side=tk.LEFT)
        se.bind("<Return>", lambda e: self._search())

        list_f = w98_frame(self, relief="sunken", bd=2)
        list_f.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)
        cols = ("stock_no", "year", "make", "model", "color", "mileage", "status")
        self._tree = W98Treeview(list_f, columns=cols, show="headings",
                                 name="veh_lookup_tree", selectmode="browse")
        for c, h, w in [("stock_no", "Stock #", 80), ("year", "Year", 50), ("make", "Make", 80),
                        ("model", "Model", 120), ("color", "Color", 80),
                        ("mileage", "Mileage", 70), ("status", "Status", 100)]:
            self._tree.heading(c, text=h)
            self._tree.column(c, width=w)
        vsb = w98_scrollbar(list_f, command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        list_f.rowconfigure(0, weight=1)
        list_f.columnconfigure(0, weight=1)
        self._tree.bind("<Double-1>", lambda e: self._select())

        btn = w98_frame(self)
        btn.pack(pady=6)
        w98_button(btn, "Select", command=self._select, name="btn_veh_lookup_select", width=10).pack(side=tk.LEFT, padx=6)
        w98_button(btn, "Cancel", command=self.destroy, name="btn_veh_lookup_cancel", width=10).pack(side=tk.LEFT, padx=6)
        self._search()
        se.focus_set()

    def _search(self):
        q = self._sv.get().strip()
        conn = get_connection()
        clauses, params = [], []
        if self._where_status:
            clauses.append("status=?")
            params.append(self._where_status)
        if self._customer_id:
            clauses.append("customer_id=?")
            params.append(self._customer_id)
        if q:
            like = f"%{q}%"
            clauses.append("(stock_no LIKE ? OR vin LIKE ? OR make LIKE ? OR model LIKE ?)")
            params += [like, like, like, like]
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM vehicles {where} ORDER BY year DESC, make", params).fetchall()
        conn.close()
        self._tree.delete(*self._tree.get_children())
        self._rows = {}
        for r in rows:
            self._tree.insert("", "end", iid=str(r["id"]),
                              values=(r["stock_no"], r["year"], r["make"], r["model"],
                                      r["color"], r["mileage"], r["status"]))
            self._rows[r["id"]] = dict(r)

    def _select(self):
        sel = self._tree.selection()
        if not sel:
            return
        self.on_select(self._rows[int(sel[0])])
        self.destroy()
