"""Repair Orders - the primary service-department RPA flow (analogous to the EMR SOAP encounter)."""
import tkinter as tk
from tkinter import messagebox
import random
import datetime
from ui import style
from ui.widgets import (
    w98_button, w98_entry, w98_label, w98_frame, w98_labelframe, w98_combobox, w98_text,
    W98Treeview, w98_scrollbar, title_bar,
)
from ui.constants import RO_TYPES, RO_STATUSES, ADVISORS
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


def _show_ro_saved(parent, vals, ro_number, is_new):
    """Massive W98-style success modal after saving a repair order."""
    tx_id = "RO-" + "".join(random.choices("0123456789ABCDEF", k=10))
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    action = "OPENED" if is_new else "UPDATED"

    detail_text = (
        f"  Transaction ID  :  {tx_id}\n"
        f"  RO Number       :  {ro_number}\n"
        f"  Timestamp       :  {now}\n"
        f"  Action          :  REPAIR ORDER {action}\n"
        f"  RO Date         :  {vals.get('date', 'N/A')}\n"
        f"  Type            :  {vals.get('type', 'N/A')}\n"
        f"  Advisor         :  {vals.get('advisor', 'N/A')}\n"
        f"  Status          :  {vals.get('status', 'N/A')}\n"
        f"  Odometer        :  {vals.get('mileage', 'N/A')} mi\n\n"
        f"  Service write-up sections saved:\n"
        f"    [1] Concern         - {len(vals.get('concern',''))} characters\n"
        f"    [2] Cause           - {len(vals.get('cause',''))} characters\n"
        f"    [3] Correction      - {len(vals.get('correction',''))} characters\n"
        f"    [4] Recommendations - {len(vals.get('recommendations',''))} characters\n\n"
        f"  Record written to:  \\\\DMSERVER\\SVCDB\\REPAIR_ORDERS\\\n"
        f"  Backup copy sent to:  \\\\DMSERVER\\BACKUP\\{tx_id}.bak\n"
        f"  Warranty claim queued for transmission.\n\n"
        f"  This repair order has been saved to the customer record.\n"
        f"  Please retain transaction ID {tx_id} for your records.\n"
        f"  If you experience any issues, contact your system administrator."
    )

    win = tk.Toplevel(parent)
    win.title("DealerDesk 98 - Repair Order Saved Successfully")
    win.configure(bg="#C0C0C0")
    win.resizable(False, False)
    win.attributes("-topmost", True)
    win.grab_set()

    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    w, h = 560, 420
    win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    title_f = tk.Frame(win, bg="#005500", pady=6)
    title_f.pack(fill=tk.X)
    tk.Label(title_f, text="OK  REPAIR ORDER SAVED SUCCESSFULLY",
             font=("MS Sans Serif", 11, "bold"), bg="#005500", fg="#FFFFFF", padx=10).pack(side=tk.LEFT)

    top_row = tk.Frame(win, bg="#C0C0C0", pady=8)
    top_row.pack(fill=tk.X, padx=10)
    tk.Label(top_row, text="OK", font=("MS Sans Serif", 28, "bold"),
             bg="#005500", fg="#FFFFFF", padx=12, pady=4, relief="raised", bd=3).pack(side=tk.LEFT)
    msg_frame = tk.Frame(top_row, bg="#C0C0C0")
    msg_frame.pack(side=tk.LEFT, padx=12)
    tk.Label(msg_frame, text=f"Repair Order {action}", font=("MS Sans Serif", 12, "bold"),
             bg="#C0C0C0", fg="#005500").pack(anchor="w")
    tk.Label(msg_frame, text="The repair order has been committed to the service database.",
             font=("MS Sans Serif", 8), bg="#C0C0C0", fg="#333333").pack(anchor="w")
    tk.Label(msg_frame, text=f"RO: {ro_number}   Transaction: {tx_id}",
             font=("Courier New", 8, "bold"), bg="#C0C0C0", fg="#005500").pack(anchor="w", pady=(4, 0))

    tk.Frame(win, bg="#808080", height=2).pack(fill=tk.X, padx=6, pady=2)

    txt_frame = tk.Frame(win, bg="#C0C0C0")
    txt_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
    txt = tk.Text(txt_frame, font=("Courier New", 8), bg="#001A00", fg="#00FF66",
                  relief="sunken", bd=2, wrap="word", height=12)
    vsb = tk.Scrollbar(txt_frame, command=txt.yview, bg="#C0C0C0")
    txt.configure(yscrollcommand=vsb.set)
    txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    txt.insert("1.0", detail_text)
    txt.configure(state="disabled")

    tk.Frame(win, bg="#808080", height=2).pack(fill=tk.X, padx=6, pady=2)

    btn_row = tk.Frame(win, bg="#C0C0C0", pady=8)
    btn_row.pack(fill=tk.X)

    def _fake_print():
        messagebox.showinfo(
            "Print",
            "Sending to printer: \\\\DMSERVER\\HP_LaserJet_4\n\n"
            f"Job ID: {random.randint(1000,9999)}\n"
            f"Document: Repair Order {ro_number}\n"
            "Please collect the RO hard copy from the service drive printer.",
            parent=win)

    for text, cmd, w_val in [("Print", _fake_print, 8), ("OK", win.destroy, 10)]:
        tk.Button(btn_row, text=text, command=cmd, font=("MS Sans Serif", 8),
                  bg="#C0C0C0", relief="raised", bd=2, width=w_val).pack(side=tk.LEFT, padx=8)


def _fetch_ros(advisor="", status=""):
    conn = get_connection()
    clauses, params = [], []
    if advisor:
        clauses.append("r.advisor=?")
        params.append(advisor)
    if status:
        clauses.append("r.status=?")
        params.append(status)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(
        f"""SELECT r.*, c.first_name, c.last_name, c.customer_no,
                   v.year AS v_year, v.make AS v_make, v.model AS v_model
            FROM repair_orders r
            JOIN customers c ON r.customer_id = c.id
            LEFT JOIN vehicles v ON r.vehicle_id = v.id
            {where} ORDER BY r.date DESC""", params).fetchall()
    conn.close()
    return rows


def _veh_text(r):
    if r["v_make"]:
        return f"{r['v_year']} {r['v_make']} {r['v_model']}"
    return "-"


class RepairOrderListPanel(tk.Frame):
    def __init__(self, parent, dashboard):
        super().__init__(parent, bg=style.BG)
        self.dashboard = dashboard
        self._build()
        self.refresh()

    def _build(self):
        title_bar(self, "  Repair Orders").pack(fill=tk.X)

        bar = w98_frame(self)
        bar.pack(fill=tk.X, padx=6, pady=4)
        w98_label(bar, text="Advisor:").pack(side=tk.LEFT)
        self._adv_var = tk.StringVar()
        w98_combobox(bar, textvariable=self._adv_var, values=[""] + ADVISORS,
                     name="ro_filter_advisor", width=18).pack(side=tk.LEFT, padx=4)
        w98_label(bar, text="Status:").pack(side=tk.LEFT, padx=(8, 0))
        self._status_var = tk.StringVar()
        w98_combobox(bar, textvariable=self._status_var, values=[""] + RO_STATUSES,
                     name="ro_filter_status", width=14).pack(side=tk.LEFT, padx=4)
        w98_button(bar, "Filter", command=self.refresh, name="btn_filter_ros", width=8).pack(side=tk.LEFT, padx=2)
        w98_button(bar, "Clear", command=self._clear_filter, name="btn_clear_ros", width=6).pack(side=tk.LEFT, padx=2)

        list_f = w98_frame(self, relief="sunken", bd=2)
        list_f.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)
        cols = ("ro_number", "date", "customer", "vehicle", "advisor", "type", "status")
        self._tree = W98Treeview(list_f, columns=cols, show="headings", name="ro_tree", selectmode="browse")
        for col, heading, w in [("ro_number", "RO #", 80), ("date", "Date", 90),
                                ("customer", "Customer", 140), ("vehicle", "Vehicle", 160),
                                ("advisor", "Advisor", 130), ("type", "Type", 120), ("status", "Status", 100)]:
            self._tree.heading(col, text=heading)
            self._tree.column(col, width=w, anchor="w")
        vsb = w98_scrollbar(list_f, command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        list_f.rowconfigure(0, weight=1)
        list_f.columnconfigure(0, weight=1)
        self._tree.bind("<Double-1>", lambda e: self._edit_ro())

        btn_bar = w98_frame(self)
        btn_bar.pack(fill=tk.X, padx=6, pady=4)
        w98_button(btn_bar, "New Repair Order", command=self._new_ro, name="btn_new_ro", width=16).pack(side=tk.LEFT, padx=3)
        w98_button(btn_bar, "Edit", command=self._edit_ro, name="btn_edit_ro", width=8).pack(side=tk.LEFT, padx=3)
        w98_button(btn_bar, "Delete", command=self._delete_ro, name="btn_delete_ro", width=8).pack(side=tk.LEFT, padx=3)
        self._count_label = w98_label(btn_bar, text="")
        self._count_label.pack(side=tk.RIGHT, padx=6)

    def refresh(self):
        rows = _fetch_ros(self._adv_var.get(), self._status_var.get())
        self._tree.delete(*self._tree.get_children())
        for r in rows:
            self._tree.insert("", "end", iid=str(r["id"]),
                              values=(r["ro_number"], r["date"], f"{r['last_name']}, {r['first_name']}",
                                      _veh_text(r), r["advisor"], r["type"], r["status"]))
        self._count_label.config(text=f"{len(rows)} repair orders")
        self.dashboard.status_bar.set(f"Loaded {len(rows)} repair orders")

    def _clear_filter(self):
        self._adv_var.set("")
        self._status_var.set("")
        self.refresh()

    def _selected_id(self):
        sel = self._tree.selection()
        return int(sel[0]) if sel else None

    def _new_ro(self):
        _chaos_event("navigate")
        RepairOrderFormDialog(self, None, on_save=self.refresh)

    def _edit_ro(self):
        rid = self._selected_id()
        if not rid:
            messagebox.showinfo("Select", "Select a repair order first.", parent=self)
            return
        conn = get_connection()
        row = conn.execute("SELECT * FROM repair_orders WHERE id=?", (rid,)).fetchone()
        conn.close()
        RepairOrderFormDialog(self, row, on_save=self.refresh)

    def _delete_ro(self):
        rid = self._selected_id()
        if not rid:
            messagebox.showinfo("Select", "Select a repair order first.", parent=self)
            return
        if messagebox.askyesno("Delete", "Delete this repair order?", parent=self):
            conn = get_connection()
            conn.execute("DELETE FROM repair_orders WHERE id=?", (rid,))
            conn.commit()
            conn.close()
            self.refresh()


class RepairOrderFormDialog(tk.Toplevel):
    def __init__(self, parent, row, on_save, preset_customer=None):
        super().__init__(parent)
        self._row = row
        self.on_save = on_save
        is_edit = row is not None
        self.title("Edit Repair Order" if is_edit else "New Repair Order")
        self.configure(bg=style.BG)
        self.geometry("720x660")
        self.grab_set()
        self._resolved_cid = None
        self._resolved_vid = None
        self._build(is_edit, preset_customer)
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build(self, is_edit, preset_customer):
        title_bar(self, "  Repair Order - Service Write-Up").pack(fill=tk.X)
        outer = w98_frame(self)
        outer.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        # Customer + vehicle pickers
        pick = w98_labelframe(outer, text="Customer & Vehicle")
        pick.pack(fill=tk.X, pady=(0, 6))
        crow = w98_frame(pick)
        crow.pack(fill=tk.X, padx=6, pady=3)
        w98_label(crow, text="Customer:", width=10, anchor="e").pack(side=tk.LEFT)
        self._customer_var = tk.StringVar()
        w98_entry(crow, textvariable=self._customer_var, name="ro_customer", width=34).pack(side=tk.LEFT, padx=4)
        w98_button(crow, "Lookup", command=self._lookup_customer, name="btn_ro_lookup_customer", width=8).pack(side=tk.LEFT, padx=2)
        vrow = w98_frame(pick)
        vrow.pack(fill=tk.X, padx=6, pady=3)
        w98_label(vrow, text="Vehicle:", width=10, anchor="e").pack(side=tk.LEFT)
        self._vehicle_var = tk.StringVar()
        w98_entry(vrow, textvariable=self._vehicle_var, name="ro_vehicle", width=34).pack(side=tk.LEFT, padx=4)
        w98_button(vrow, "Lookup", command=self._lookup_vehicle, name="btn_ro_lookup_vehicle", width=8).pack(side=tk.LEFT, padx=2)

        # Header
        hdr = w98_labelframe(outer, text="RO Header")
        hdr.pack(fill=tk.X, pady=(0, 6))
        row0 = w98_frame(hdr)
        row0.pack(fill=tk.X, padx=6, pady=4)
        self._vars = {}

        w98_label(row0, text="Date:").pack(side=tk.LEFT)
        self._vars["date"] = tk.StringVar(value=self._row["date"] if is_edit else "")
        w98_entry(row0, textvariable=self._vars["date"], name="ro_date", width=12).pack(side=tk.LEFT, padx=4)

        w98_label(row0, text="Type:").pack(side=tk.LEFT, padx=(8, 0))
        self._vars["type"] = tk.StringVar(value=self._row["type"] if is_edit else "Maintenance")
        w98_combobox(row0, textvariable=self._vars["type"], values=RO_TYPES, name="ro_type", width=16).pack(side=tk.LEFT, padx=4)

        w98_label(row0, text="Status:").pack(side=tk.LEFT, padx=(8, 0))
        self._vars["status"] = tk.StringVar(value=self._row["status"] if is_edit else "Open")
        w98_combobox(row0, textvariable=self._vars["status"], values=RO_STATUSES, name="ro_status", width=14).pack(side=tk.LEFT, padx=4)

        row1 = w98_frame(hdr)
        row1.pack(fill=tk.X, padx=6, pady=4)
        w98_label(row1, text="Advisor:").pack(side=tk.LEFT)
        self._vars["advisor"] = tk.StringVar(value=self._row["advisor"] if is_edit else "")
        w98_combobox(row1, textvariable=self._vars["advisor"], values=ADVISORS, name="ro_advisor", width=16).pack(side=tk.LEFT, padx=4)
        w98_label(row1, text="Odometer:").pack(side=tk.LEFT, padx=(8, 0))
        self._vars["mileage"] = tk.StringVar(value=str(self._row["mileage"]) if (is_edit and self._row["mileage"] is not None) else "")
        w98_entry(row1, textvariable=self._vars["mileage"], name="ro_mileage", width=12).pack(side=tk.LEFT, padx=4)

        # The 3 C's + recommendations
        soap_frame = w98_frame(outer)
        soap_frame.pack(fill=tk.BOTH, expand=True)
        sections = [
            ("concern", "Concern (customer states)", "ro_concern"),
            ("cause", "Cause (technician findings)", "ro_cause"),
            ("correction", "Correction (work performed)", "ro_correction"),
            ("recommendations", "Recommendations", "ro_recommendations"),
        ]
        for key, label, wname in sections:
            lf = w98_labelframe(soap_frame, text=label)
            lf.pack(fill=tk.BOTH, expand=True, pady=2)
            txt = w98_text(lf, name=wname, width=80, height=3)
            vsb = w98_scrollbar(lf, command=txt.yview)
            txt.configure(yscrollcommand=vsb.set)
            txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)
            vsb.pack(side=tk.RIGHT, fill=tk.Y)
            if is_edit and self._row[key]:
                txt.insert("1.0", self._row[key])
            self._vars[key] = txt

        btn_row = w98_frame(self)
        btn_row.pack(fill=tk.X, padx=8, pady=6)
        w98_button(btn_row, "Save Repair Order", command=self._save, name="btn_save_ro", width=18).pack(side=tk.LEFT, padx=6)
        w98_button(btn_row, "Cancel", command=self.destroy, name="btn_cancel_ro", width=10).pack(side=tk.LEFT, padx=6)

        if preset_customer:
            self._resolved_cid = preset_customer["id"]
            self._customer_var.set(f"{preset_customer['last_name']}, {preset_customer['first_name']} ({preset_customer['customer_no']})")
        if is_edit:
            self._prefill_refs()

    def _prefill_refs(self):
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

    def _lookup_customer(self):
        CustomerLookupDialog(self, on_select=self._on_customer)

    def _on_customer(self, c):
        self._resolved_cid = c["id"]
        self._customer_var.set(f"{c['last_name']}, {c['first_name']} ({c['customer_no']})")

    def _lookup_vehicle(self):
        VehicleLookupDialog(self, on_select=self._on_vehicle, customer_id=self._resolved_cid)

    def _on_vehicle(self, v):
        self._resolved_vid = v["id"]
        self._vehicle_var.set(f"{v['stock_no']} - {v['year']} {v['make']} {v['model']}")

    def _save(self):
        if not self._resolved_cid:
            messagebox.showerror("Validation", "Please select a customer.", parent=self)
            return

        def getv(key):
            v = self._vars[key]
            if isinstance(v, tk.StringVar):
                return v.get().strip()
            return v.get("1.0", "end-1c").strip()

        vals = {k: getv(k) for k in ("date", "type", "advisor", "status", "mileage",
                                     "concern", "cause", "correction", "recommendations")}
        if not vals["date"]:
            messagebox.showerror("Validation", "Date is required (YYYY-MM-DD).", parent=self)
            return
        try:
            mileage = int(float(vals["mileage"].replace(",", ""))) if vals["mileage"] else None
        except ValueError:
            messagebox.showerror("Validation", "Odometer must be a number.", parent=self)
            return

        _chaos_event("save")

        conn = get_connection()
        if self._row:
            ro_number = self._row["ro_number"]
            conn.execute(
                "UPDATE repair_orders SET customer_id=?,vehicle_id=?,date=?,type=?,advisor=?,mileage=?,"
                "status=?,concern=?,cause=?,correction=?,recommendations=? WHERE id=?",
                (self._resolved_cid, self._resolved_vid, vals["date"], vals["type"], vals["advisor"], mileage,
                 vals["status"], vals["concern"], vals["cause"], vals["correction"], vals["recommendations"],
                 self._row["id"]))
        else:
            ro_number = "RO" + str(50000 + (conn.execute("SELECT COUNT(*) FROM repair_orders").fetchone()[0] + 1))
            conn.execute(
                "INSERT INTO repair_orders (ro_number,customer_id,vehicle_id,date,type,advisor,mileage,status,concern,cause,correction,recommendations)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (ro_number, self._resolved_cid, self._resolved_vid, vals["date"], vals["type"], vals["advisor"],
                 mileage, vals["status"], vals["concern"], vals["cause"], vals["correction"], vals["recommendations"]))
        conn.commit()
        conn.close()
        self.on_save()
        _show_ro_saved(self.master, vals, ro_number, is_new=self._row is None)
        self.destroy()
