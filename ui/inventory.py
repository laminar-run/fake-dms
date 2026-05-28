"""Vehicle inventory list panel + vehicle CRUD form."""
import tkinter as tk
from tkinter import messagebox, ttk
from ui import style
from ui.widgets import (
    w98_button, w98_entry, w98_label, w98_frame, w98_labelframe, w98_combobox, w98_scrollbar, title_bar,
)
from ui.constants import MAKES, VEHICLE_STATUSES
from db.connection import get_connection

STATUS_FILTERS = ["In Stock", "All", "Sold", "Customer-Owned", "In Service"]


def _fetch_vehicles(search="", status="In Stock"):
    conn = get_connection()
    clauses, params = [], []
    if status and status != "All":
        clauses.append("status=?")
        params.append(status)
    if search:
        like = f"%{search}%"
        clauses.append("(stock_no LIKE ? OR vin LIKE ? OR make LIKE ? OR model LIKE ?)")
        params += [like, like, like, like]
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(f"SELECT * FROM vehicles {where} ORDER BY year DESC, make, model", params).fetchall()
    conn.close()
    return rows


class InventoryPanel(tk.Frame):
    def __init__(self, parent, dashboard):
        super().__init__(parent, bg=style.BG)
        self.dashboard = dashboard
        self._build()
        self.refresh()

    def _build(self):
        title_bar(self, "  Vehicle Inventory").pack(fill=tk.X)

        bar = w98_frame(self)
        bar.pack(fill=tk.X, padx=6, pady=5)
        w98_label(bar, text="Search:").pack(side=tk.LEFT)
        self._search_var = tk.StringVar()
        se = w98_entry(bar, textvariable=self._search_var, name="inventory_search", width=26)
        se.pack(side=tk.LEFT, padx=4)
        se.bind("<Return>", lambda e: self.refresh())
        w98_label(bar, text="Status:").pack(side=tk.LEFT, padx=(8, 0))
        self._status_var = tk.StringVar(value="In Stock")
        w98_combobox(bar, textvariable=self._status_var, values=STATUS_FILTERS,
                     name="inventory_status_filter", width=14).pack(side=tk.LEFT, padx=4)
        w98_button(bar, "Search", command=self.refresh, name="btn_search_inventory", width=8).pack(side=tk.LEFT, padx=2)
        w98_button(bar, "Show All", command=self._show_all, name="btn_clear_inventory", width=8).pack(side=tk.LEFT, padx=2)
        self._count_label = tk.Label(bar, text="", font=style.FONT_BOLD, bg=style.BG_DARK, fg="white",
                                     padx=8, pady=2, relief="sunken")
        self._count_label.pack(side=tk.RIGHT, padx=6)

        list_frame = w98_frame(self, relief="sunken", bd=2)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)
        cols = ("stock_no", "year", "make", "model", "trim", "color", "mileage", "price", "status")
        self._tree = ttk.Treeview(list_frame, columns=cols, show="headings", style="W98.Treeview",
                                  name="inventory_tree", selectmode="browse")
        for col, heading, w in [("stock_no", "Stock #", 80), ("year", "Year", 55), ("make", "Make", 90),
                                ("model", "Model", 130), ("trim", "Trim", 90), ("color", "Color", 90),
                                ("mileage", "Mileage", 80), ("price", "Price", 90), ("status", "Status", 110)]:
            self._tree.heading(col, text=heading, command=lambda c=col: self._sort_by(c))
            self._tree.column(col, width=w, anchor="w", minwidth=50)
        vsb = w98_scrollbar(list_frame, command=self._tree.yview)
        hsb = w98_scrollbar(list_frame, orient=tk.HORIZONTAL, command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        self._tree.bind("<Double-1>", lambda e: self._edit_vehicle())
        self._sort_col, self._sort_rev = None, False

        btn = w98_frame(self)
        btn.pack(fill=tk.X, padx=6, pady=4)
        w98_button(btn, "Add Vehicle", command=self._add_vehicle, name="btn_add_vehicle_inv", width=12).pack(side=tk.LEFT, padx=3)
        w98_button(btn, "Edit", command=self._edit_vehicle, name="btn_edit_vehicle_inv", width=8).pack(side=tk.LEFT, padx=3)
        w98_button(btn, "Delete", command=self._delete_vehicle, name="btn_delete_vehicle_inv", width=8).pack(side=tk.LEFT, padx=3)

    def refresh(self):
        rows = _fetch_vehicles(self._search_var.get().strip(), self._status_var.get())
        self._tree.delete(*self._tree.get_children())
        for r in rows:
            self._tree.insert("", "end", iid=str(r["id"]),
                              values=(r["stock_no"], r["year"], r["make"], r["model"], r["trim"],
                                      r["color"], r["mileage"], f"${r['price']:,.0f}", r["status"]))
        self._tree.tag_configure("odd", background="#F0F0F8")
        for i, iid in enumerate(self._tree.get_children()):
            if i % 2 == 1:
                self._tree.item(iid, tags=("odd",))
        self._count_label.config(text=f"  {len(rows)} vehicle{'s' if len(rows) != 1 else ''}  ")
        self.dashboard.status_bar.set(f"Loaded {len(rows)} vehicles")

    def _show_all(self):
        self._search_var.set("")
        self._status_var.set("All")
        self.refresh()

    def _sort_by(self, col):
        data = [(self._tree.set(iid, col), iid) for iid in self._tree.get_children()]
        self._sort_rev = not self._sort_rev if self._sort_col == col else False
        self._sort_col = col

        def conv(v):
            s = v.replace("$", "").replace(",", "")
            try:
                return float(s)
            except ValueError:
                return v.lower()
        data.sort(key=lambda t: conv(t[0]), reverse=self._sort_rev)
        for i, (_, iid) in enumerate(data):
            self._tree.move(iid, "", i)

    def _selected_id(self):
        sel = self._tree.selection()
        return int(sel[0]) if sel else None

    def _add_vehicle(self):
        VehicleFormDialog(self, None, on_save=self.refresh)

    def _edit_vehicle(self):
        vid = self._selected_id()
        if not vid:
            messagebox.showinfo("Select", "Select a vehicle first.", parent=self)
            return
        conn = get_connection()
        row = conn.execute("SELECT * FROM vehicles WHERE id=?", (vid,)).fetchone()
        conn.close()
        VehicleFormDialog(self, row, on_save=self.refresh)

    def _delete_vehicle(self):
        vid = self._selected_id()
        if not vid:
            messagebox.showinfo("Select", "Select a vehicle first.", parent=self)
            return
        if messagebox.askyesno("Delete", "Delete this vehicle?", parent=self):
            conn = get_connection()
            conn.execute("DELETE FROM vehicles WHERE id=?", (vid,))
            conn.commit()
            conn.close()
            self.refresh()


class VehicleFormDialog(tk.Toplevel):
    def __init__(self, parent, row, on_save, preset_customer_id=None):
        super().__init__(parent)
        self.on_save = on_save
        self._row = row
        self._preset_customer_id = preset_customer_id
        is_edit = row is not None
        self.title("Edit Vehicle" if is_edit else "Add Vehicle")
        self.resizable(False, False)
        self.configure(bg=style.BG)
        self.grab_set()
        self._build(is_edit)
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build(self, is_edit):
        title_bar(self, "  Vehicle Details").pack(fill=tk.X)
        frm = w98_labelframe(self, text="Vehicle Information")
        frm.pack(padx=12, pady=8, fill=tk.BOTH, expand=True)
        default_status = "Customer-Owned" if self._preset_customer_id else "In Stock"
        fields = [("Stock #:", "stock_no", "entry"), ("VIN:", "vin", "entry"), ("Year:", "year", "entry"),
                  ("Make:", "make", "combo"), ("Model:", "model", "entry"), ("Trim:", "trim", "entry"),
                  ("Color:", "color", "entry"), ("Mileage:", "mileage", "entry"), ("Price:", "price", "entry"),
                  ("Status:", "status", "combo")]
        self._vars = {}
        for i, (label, key, ftype) in enumerate(fields):
            w98_label(frm, text=label).grid(row=i, column=0, sticky="e", padx=6, pady=3)
            if is_edit:
                default = self._row[key]
            elif key == "status":
                default = default_status
            else:
                default = ""
            var = tk.StringVar(value=default)
            self._vars[key] = var
            if ftype == "combo":
                values = MAKES if key == "make" else VEHICLE_STATUSES
                w98_combobox(frm, textvariable=var, values=values, name=f"veh_{key}", width=30).grid(
                    row=i, column=1, sticky="w", padx=6, pady=3)
            else:
                w98_entry(frm, textvariable=var, name=f"veh_{key}", width=34).grid(
                    row=i, column=1, sticky="w", padx=6, pady=3)

        btn = w98_frame(self)
        btn.pack(pady=8)
        w98_button(btn, "Save", command=self._save, name="btn_save_vehicle", width=10).pack(side=tk.LEFT, padx=6)
        w98_button(btn, "Cancel", command=self.destroy, name="btn_cancel_vehicle", width=10).pack(side=tk.LEFT, padx=6)

    def _save(self):
        vals = {k: v.get().strip() for k, v in self._vars.items()}
        if not vals["stock_no"] or not vals["vin"] or not vals["make"] or not vals["model"]:
            messagebox.showerror("Validation", "Stock #, VIN, Make and Model are required.", parent=self)
            return

        def to_int(x):
            try:
                return int(float(str(x).replace(",", "")))
            except ValueError:
                return 0

        def to_float(x):
            try:
                return float(str(x).replace("$", "").replace(",", ""))
            except ValueError:
                return 0.0

        year, mileage, price = to_int(vals["year"]), to_int(vals["mileage"]), to_float(vals["price"])
        conn = get_connection()
        if self._row:
            conn.execute(
                "UPDATE vehicles SET stock_no=?,vin=?,year=?,make=?,model=?,trim=?,color=?,mileage=?,price=?,status=?,customer_id=? WHERE id=?",
                (vals["stock_no"], vals["vin"], year, vals["make"], vals["model"], vals["trim"], vals["color"],
                 mileage, price, vals["status"], self._row["customer_id"], self._row["id"]))
        else:
            conn.execute(
                "INSERT INTO vehicles (stock_no,vin,year,make,model,trim,color,mileage,price,status,customer_id)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (vals["stock_no"], vals["vin"], year, vals["make"], vals["model"], vals["trim"], vals["color"],
                 mileage, price, vals["status"], self._preset_customer_id))
        conn.commit()
        conn.close()
        self.on_save()
        self.destroy()
