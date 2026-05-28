"""Deals (sales) list panel + deal CRUD form with customer & vehicle lookup."""
import tkinter as tk
from tkinter import messagebox
from ui import style
from ui.widgets import (
    w98_button, w98_entry, w98_label, w98_frame, w98_labelframe, w98_combobox, w98_text,
    W98Treeview, w98_scrollbar, title_bar,
)
from ui.constants import SALESPEOPLE, DEAL_TYPES, DEAL_STATUSES
from ui.lookups import CustomerLookupDialog, VehicleLookupDialog
from db.connection import get_connection


def _chaos_event(event_type):
    try:
        from chaos.engine import get_engine
        e = get_engine()
        if e:
            e.on_event(event_type)
    except Exception:
        pass


def _fetch_deals(salesperson="", status=""):
    conn = get_connection()
    clauses, params = [], []
    if salesperson:
        clauses.append("d.salesperson=?")
        params.append(salesperson)
    if status:
        clauses.append("d.status=?")
        params.append(status)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(
        f"""SELECT d.*, c.first_name, c.last_name, c.customer_no,
                   v.year AS v_year, v.make AS v_make, v.model AS v_model
            FROM deals d
            JOIN customers c ON d.customer_id = c.id
            LEFT JOIN vehicles v ON d.vehicle_id = v.id
            {where} ORDER BY d.date DESC""", params).fetchall()
    conn.close()
    return rows


def _veh_text(r):
    if r["v_make"]:
        return f"{r['v_year']} {r['v_make']} {r['v_model']}"
    return "-"


class DealListPanel(tk.Frame):
    def __init__(self, parent, dashboard):
        super().__init__(parent, bg=style.BG)
        self.dashboard = dashboard
        self._build()
        self.refresh()

    def _build(self):
        title_bar(self, "  Deals").pack(fill=tk.X)

        bar = w98_frame(self)
        bar.pack(fill=tk.X, padx=6, pady=4)
        w98_label(bar, text="Salesperson:").pack(side=tk.LEFT)
        self._sp_var = tk.StringVar()
        w98_combobox(bar, textvariable=self._sp_var, values=[""] + SALESPEOPLE,
                     name="deal_filter_salesperson", width=18).pack(side=tk.LEFT, padx=4)
        w98_label(bar, text="Status:").pack(side=tk.LEFT, padx=(8, 0))
        self._status_var = tk.StringVar()
        w98_combobox(bar, textvariable=self._status_var, values=[""] + DEAL_STATUSES,
                     name="deal_filter_status", width=14).pack(side=tk.LEFT, padx=4)
        w98_button(bar, "Filter", command=self.refresh, name="btn_filter_deals", width=8).pack(side=tk.LEFT, padx=2)
        w98_button(bar, "Clear", command=self._clear_filter, name="btn_clear_deals", width=6).pack(side=tk.LEFT, padx=2)

        list_f = w98_frame(self, relief="sunken", bd=2)
        list_f.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)
        cols = ("deal_number", "date", "customer", "vehicle", "salesperson", "deal_type", "sale_price", "status")
        self._tree = W98Treeview(list_f, columns=cols, show="headings", name="deal_tree", selectmode="browse")
        for col, heading, w in [("deal_number", "Deal #", 80), ("date", "Date", 90),
                                ("customer", "Customer", 140), ("vehicle", "Vehicle", 170),
                                ("salesperson", "Salesperson", 130), ("deal_type", "Type", 80),
                                ("sale_price", "Sale Price", 100), ("status", "Status", 90)]:
            self._tree.heading(col, text=heading)
            self._tree.column(col, width=w, anchor="w")
        vsb = w98_scrollbar(list_f, command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        list_f.rowconfigure(0, weight=1)
        list_f.columnconfigure(0, weight=1)
        self._tree.bind("<Double-1>", lambda e: self._edit_deal())

        btn_bar = w98_frame(self)
        btn_bar.pack(fill=tk.X, padx=6, pady=4)
        w98_button(btn_bar, "New Deal", command=self._new_deal, name="btn_new_deal", width=12).pack(side=tk.LEFT, padx=3)
        w98_button(btn_bar, "Edit", command=self._edit_deal, name="btn_edit_deal", width=8).pack(side=tk.LEFT, padx=3)
        w98_button(btn_bar, "Delete", command=self._delete_deal, name="btn_delete_deal", width=8).pack(side=tk.LEFT, padx=3)
        self._count_label = w98_label(btn_bar, text="")
        self._count_label.pack(side=tk.RIGHT, padx=6)

    def refresh(self):
        rows = _fetch_deals(self._sp_var.get(), self._status_var.get())
        self._tree.delete(*self._tree.get_children())
        for r in rows:
            self._tree.insert("", "end", iid=str(r["id"]),
                              values=(r["deal_number"], r["date"], f"{r['last_name']}, {r['first_name']}",
                                      _veh_text(r), r["salesperson"], r["deal_type"],
                                      f"${r['sale_price']:,.0f}", r["status"]))
        self._count_label.config(text=f"{len(rows)} deals")
        self.dashboard.status_bar.set(f"Loaded {len(rows)} deals")

    def _clear_filter(self):
        self._sp_var.set("")
        self._status_var.set("")
        self.refresh()

    def _selected_id(self):
        sel = self._tree.selection()
        return int(sel[0]) if sel else None

    def _new_deal(self):
        DealFormDialog(self, None, on_save=self.refresh)

    def _edit_deal(self):
        did = self._selected_id()
        if not did:
            messagebox.showinfo("Select", "Select a deal first.", parent=self)
            return
        conn = get_connection()
        row = conn.execute("SELECT * FROM deals WHERE id=?", (did,)).fetchone()
        conn.close()
        DealFormDialog(self, row, on_save=self.refresh)

    def _delete_deal(self):
        did = self._selected_id()
        if not did:
            messagebox.showinfo("Select", "Select a deal first.", parent=self)
            return
        if messagebox.askyesno("Delete", "Delete this deal?", parent=self):
            conn = get_connection()
            conn.execute("DELETE FROM deals WHERE id=?", (did,))
            conn.commit()
            conn.close()
            self.refresh()


class DealFormDialog(tk.Toplevel):
    def __init__(self, parent, row, on_save, preset_customer=None):
        super().__init__(parent)
        self._row = row
        self.on_save = on_save
        is_edit = row is not None
        self.title("Edit Deal" if is_edit else "New Deal")
        self.resizable(False, False)
        self.configure(bg=style.BG)
        self.grab_set()
        self._resolved_cid = None
        self._resolved_vid = None
        self._build(is_edit, preset_customer)
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build(self, is_edit, preset_customer):
        title_bar(self, "  Deal Worksheet").pack(fill=tk.X)
        frm = w98_labelframe(self, text="Deal Details")
        frm.pack(padx=12, pady=8, fill=tk.BOTH, expand=True)

        # Customer row
        crow = w98_frame(frm)
        crow.pack(fill=tk.X, padx=6, pady=3)
        w98_label(crow, text="Customer:", width=14, anchor="e").pack(side=tk.LEFT)
        self._customer_var = tk.StringVar()
        w98_entry(crow, textvariable=self._customer_var, name="deal_customer", width=34).pack(side=tk.LEFT, padx=4)
        w98_button(crow, "Lookup", command=self._lookup_customer, name="btn_deal_lookup_customer", width=8).pack(side=tk.LEFT, padx=2)

        # Vehicle row
        vrow = w98_frame(frm)
        vrow.pack(fill=tk.X, padx=6, pady=3)
        w98_label(vrow, text="Vehicle:", width=14, anchor="e").pack(side=tk.LEFT)
        self._vehicle_var = tk.StringVar()
        w98_entry(vrow, textvariable=self._vehicle_var, name="deal_vehicle", width=34).pack(side=tk.LEFT, padx=4)
        w98_button(vrow, "Lookup", command=self._lookup_vehicle, name="btn_deal_lookup_vehicle", width=8).pack(side=tk.LEFT, padx=2)

        self._vars = {}
        fields = [("Date (YYYY-MM-DD):", "date", "entry", "deal_date"),
                  ("Salesperson:", "salesperson", "combo", "deal_salesperson"),
                  ("Deal Type:", "deal_type", "combo", "deal_type"),
                  ("Sale Price:", "sale_price", "entry", "deal_sale_price"),
                  ("Trade-In:", "trade_in", "entry", "deal_trade_in"),
                  ("Status:", "status", "combo", "deal_status")]
        for label, key, ftype, wname in fields:
            row_f = w98_frame(frm)
            row_f.pack(fill=tk.X, padx=6, pady=3)
            w98_label(row_f, text=label, width=14, anchor="e").pack(side=tk.LEFT)
            var = tk.StringVar(value=self._row[key] if is_edit else ("Quote" if key == "status" else ("Finance" if key == "deal_type" else "")))
            self._vars[key] = var
            if ftype == "combo":
                values = {"salesperson": SALESPEOPLE, "deal_type": DEAL_TYPES, "status": DEAL_STATUSES}[key]
                w98_combobox(row_f, textvariable=var, values=values, name=wname, width=30).pack(side=tk.LEFT, padx=4)
            else:
                w98_entry(row_f, textvariable=var, name=wname, width=32).pack(side=tk.LEFT, padx=4)

        notes_f = w98_frame(frm)
        notes_f.pack(fill=tk.X, padx=6, pady=3)
        w98_label(notes_f, text="Notes:").pack(anchor="nw")
        self._notes_txt = w98_text(notes_f, name="deal_notes", width=50, height=3)
        self._notes_txt.pack(fill=tk.X, pady=2)

        btn_row = w98_frame(self)
        btn_row.pack(pady=8)
        w98_button(btn_row, "Save Deal", command=self._save, name="btn_save_deal", width=12).pack(side=tk.LEFT, padx=6)
        w98_button(btn_row, "Cancel", command=self.destroy, name="btn_cancel_deal", width=10).pack(side=tk.LEFT, padx=6)

        # Pre-fill
        if preset_customer:
            self._resolved_cid = preset_customer["id"]
            self._customer_var.set(f"{preset_customer['last_name']}, {preset_customer['first_name']} ({preset_customer['customer_no']})")
        if is_edit:
            self._prefill_from_row()

    def _prefill_from_row(self):
        conn = get_connection()
        c = conn.execute("SELECT * FROM customers WHERE id=?", (self._row["customer_id"],)).fetchone()
        if c:
            self._resolved_cid = c["id"]
            self._customer_var.set(f"{c['last_name']}, {c['first_name']} ({c['customer_no']})")
        if self._row["vehicle_id"]:
            v = conn.execute("SELECT * FROM vehicles WHERE id=?", (self._row["vehicle_id"],)).fetchone()
            if v:
                self._resolved_vid = v["id"]
                self._vehicle_var.set(f"{v['stock_no']} - {v['year']} {v['make']} {v['model']}")
        conn.close()
        if self._row["notes"]:
            self._notes_txt.insert("1.0", self._row["notes"])

    def _lookup_customer(self):
        CustomerLookupDialog(self, on_select=self._on_customer)

    def _on_customer(self, c):
        self._resolved_cid = c["id"]
        self._customer_var.set(f"{c['last_name']}, {c['first_name']} ({c['customer_no']})")

    def _lookup_vehicle(self):
        status = None if self._row else "In Stock"
        VehicleLookupDialog(self, on_select=self._on_vehicle, where_status=status)

    def _on_vehicle(self, v):
        self._resolved_vid = v["id"]
        self._vehicle_var.set(f"{v['stock_no']} - {v['year']} {v['make']} {v['model']}")

    def _save(self):
        if not self._resolved_cid:
            messagebox.showerror("Validation", "Please select a customer.", parent=self)
            return
        vals = {k: v.get().strip() for k, v in self._vars.items()}
        vals["notes"] = self._notes_txt.get("1.0", "end-1c").strip()
        if not vals["date"]:
            messagebox.showerror("Validation", "Date is required (YYYY-MM-DD).", parent=self)
            return
        try:
            price = float(vals["sale_price"].replace("$", "").replace(",", "")) if vals["sale_price"] else 0.0
        except ValueError:
            messagebox.showerror("Validation", "Sale Price must be a number.", parent=self)
            return

        _chaos_event("save")

        conn = get_connection()
        if self._row:
            conn.execute(
                "UPDATE deals SET customer_id=?,vehicle_id=?,date=?,salesperson=?,deal_type=?,sale_price=?,trade_in=?,status=?,notes=? WHERE id=?",
                (self._resolved_cid, self._resolved_vid, vals["date"], vals["salesperson"], vals["deal_type"],
                 price, vals["trade_in"], vals["status"], vals["notes"], self._row["id"]))
        else:
            deal_no = "D" + str(8000 + (conn.execute("SELECT COUNT(*) FROM deals").fetchone()[0] + 1))
            conn.execute(
                "INSERT INTO deals (deal_number,customer_id,vehicle_id,date,salesperson,deal_type,sale_price,trade_in,status,notes)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (deal_no, self._resolved_cid, self._resolved_vid, vals["date"], vals["salesperson"],
                 vals["deal_type"], price, vals["trade_in"], vals["status"], vals["notes"]))
        # If sold/delivered, take the vehicle off the lot
        if self._resolved_vid and vals["status"] in ("Sold", "Delivered"):
            conn.execute("UPDATE vehicles SET status='Sold', customer_id=? WHERE id=?",
                         (self._resolved_cid, self._resolved_vid))
        conn.commit()
        conn.close()
        self.on_save()
        messagebox.showinfo("Deal Saved", "The deal has been saved successfully.", parent=self.master)
        self.destroy()
