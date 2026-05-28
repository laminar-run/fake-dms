"""Appointments (service + sales) list panel + appointment CRUD form."""
import tkinter as tk
from tkinter import messagebox
from ui import style
from ui.widgets import (
    w98_button, w98_entry, w98_label, w98_frame, w98_labelframe, w98_combobox, w98_text,
    W98Treeview, w98_scrollbar, title_bar,
)
from ui.constants import STAFF, APPT_DEPTS, APPT_STATUSES, SERVICE_REASONS, SALES_REASONS
from ui.lookups import CustomerLookupDialog
from db.connection import get_connection


def _chaos_event(event_type):
    try:
        from chaos.engine import get_engine
        e = get_engine()
        if e:
            e.on_event(event_type)
    except Exception:
        pass


def _fetch_appointments(dept="", status=""):
    conn = get_connection()
    clauses, params = [], []
    if dept:
        clauses.append("a.dept=?")
        params.append(dept)
    if status:
        clauses.append("a.status=?")
        params.append(status)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(
        f"""SELECT a.*, c.first_name, c.last_name, c.customer_no
            FROM appointments a JOIN customers c ON a.customer_id = c.id
            {where} ORDER BY a.datetime DESC""", params).fetchall()
    conn.close()
    return rows


class AppointmentListPanel(tk.Frame):
    def __init__(self, parent, dashboard):
        super().__init__(parent, bg=style.BG)
        self.dashboard = dashboard
        self._build()
        self.refresh()

    def _build(self):
        title_bar(self, "  Appointments").pack(fill=tk.X)

        bar = w98_frame(self)
        bar.pack(fill=tk.X, padx=6, pady=4)
        w98_label(bar, text="Dept:").pack(side=tk.LEFT)
        self._dept_var = tk.StringVar()
        w98_combobox(bar, textvariable=self._dept_var, values=[""] + APPT_DEPTS,
                     name="appt_filter_dept", width=12).pack(side=tk.LEFT, padx=4)
        w98_label(bar, text="Status:").pack(side=tk.LEFT, padx=(8, 0))
        self._status_var = tk.StringVar()
        w98_combobox(bar, textvariable=self._status_var, values=[""] + APPT_STATUSES,
                     name="appt_filter_status", width=14).pack(side=tk.LEFT, padx=4)
        w98_button(bar, "Filter", command=self.refresh, name="btn_filter_appts", width=8).pack(side=tk.LEFT, padx=2)
        w98_button(bar, "Clear", command=self._clear_filter, name="btn_clear_appts", width=6).pack(side=tk.LEFT, padx=2)

        list_f = w98_frame(self, relief="sunken", bd=2)
        list_f.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)
        cols = ("datetime", "customer", "customer_no", "dept", "advisor", "reason", "status")
        self._tree = W98Treeview(list_f, columns=cols, show="headings", name="appt_tree", selectmode="browse")
        for col, heading, w in [("datetime", "Date/Time", 140), ("customer", "Customer", 140),
                                ("customer_no", "Cust #", 80), ("dept", "Dept", 70),
                                ("advisor", "Advisor/Sales", 130), ("reason", "Reason", 160), ("status", "Status", 90)]:
            self._tree.heading(col, text=heading)
            self._tree.column(col, width=w, anchor="w")
        vsb = w98_scrollbar(list_f, command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        list_f.rowconfigure(0, weight=1)
        list_f.columnconfigure(0, weight=1)
        self._tree.bind("<Double-1>", lambda e: self._edit_appt())

        btn_bar = w98_frame(self)
        btn_bar.pack(fill=tk.X, padx=6, pady=4)
        w98_button(btn_bar, "New Appointment", command=self._new_appt, name="btn_new_appt", width=16).pack(side=tk.LEFT, padx=3)
        w98_button(btn_bar, "Edit", command=self._edit_appt, name="btn_edit_appt", width=8).pack(side=tk.LEFT, padx=3)
        w98_button(btn_bar, "Delete", command=self._delete_appt, name="btn_delete_appt", width=8).pack(side=tk.LEFT, padx=3)
        self._count_label = w98_label(btn_bar, text="")
        self._count_label.pack(side=tk.RIGHT, padx=6)

    def refresh(self):
        rows = _fetch_appointments(self._dept_var.get(), self._status_var.get())
        self._tree.delete(*self._tree.get_children())
        for r in rows:
            self._tree.insert("", "end", iid=str(r["id"]),
                              values=(r["datetime"], f"{r['last_name']}, {r['first_name']}", r["customer_no"],
                                      r["dept"], r["advisor"], r["reason"], r["status"]))
        self._count_label.config(text=f"{len(rows)} appointments")
        self.dashboard.status_bar.set(f"Loaded {len(rows)} appointments")

    def _clear_filter(self):
        self._dept_var.set("")
        self._status_var.set("")
        self.refresh()

    def _selected_id(self):
        sel = self._tree.selection()
        return int(sel[0]) if sel else None

    def _new_appt(self):
        AppointmentFormDialog(self, None, on_save=self.refresh)

    def _edit_appt(self):
        aid = self._selected_id()
        if not aid:
            messagebox.showinfo("Select", "Select an appointment first.", parent=self)
            return
        conn = get_connection()
        row = conn.execute("SELECT * FROM appointments WHERE id=?", (aid,)).fetchone()
        conn.close()
        AppointmentFormDialog(self, row, on_save=self.refresh)

    def _delete_appt(self):
        aid = self._selected_id()
        if not aid:
            messagebox.showinfo("Select", "Select an appointment first.", parent=self)
            return
        if messagebox.askyesno("Delete", "Delete this appointment?", parent=self):
            conn = get_connection()
            conn.execute("DELETE FROM appointments WHERE id=?", (aid,))
            conn.commit()
            conn.close()
            self.refresh()


class AppointmentFormDialog(tk.Toplevel):
    def __init__(self, parent, row, on_save, preset_customer=None):
        super().__init__(parent)
        self._row = row
        self.on_save = on_save
        is_edit = row is not None
        self.title("Edit Appointment" if is_edit else "New Appointment")
        self.resizable(False, False)
        self.configure(bg=style.BG)
        self.grab_set()
        self._resolved_cid = None
        self._build(is_edit, preset_customer)
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build(self, is_edit, preset_customer):
        title_bar(self, "  Appointment").pack(fill=tk.X)
        frm = w98_labelframe(self, text="Appointment Details")
        frm.pack(padx=12, pady=8, fill=tk.BOTH, expand=True)

        crow = w98_frame(frm)
        crow.pack(fill=tk.X, padx=6, pady=3)
        w98_label(crow, text="Customer:", width=22, anchor="e").pack(side=tk.LEFT)
        self._customer_var = tk.StringVar()
        w98_entry(crow, textvariable=self._customer_var, name="appt_customer", width=30).pack(side=tk.LEFT, padx=4)
        w98_button(crow, "Lookup", command=self._lookup_customer, name="btn_appt_lookup_customer", width=8).pack(side=tk.LEFT, padx=2)

        self._vars = {}
        fields = [("Date/Time (YYYY-MM-DD HH:MM):", "datetime", "entry", "appt_datetime"),
                  ("Department:", "dept", "combo", "appt_dept"),
                  ("Advisor / Salesperson:", "advisor", "combo", "appt_advisor"),
                  ("Reason:", "reason", "combo", "appt_reason"),
                  ("Status:", "status", "combo", "appt_status")]
        for label, key, ftype, wname in fields:
            row_f = w98_frame(frm)
            row_f.pack(fill=tk.X, padx=6, pady=3)
            w98_label(row_f, text=label, width=22, anchor="e").pack(side=tk.LEFT)
            default = self._row[key] if is_edit else ("Service" if key == "dept" else ("Scheduled" if key == "status" else ""))
            var = tk.StringVar(value=default)
            self._vars[key] = var
            if ftype == "combo":
                values = {"dept": APPT_DEPTS, "advisor": STAFF,
                          "reason": SERVICE_REASONS + SALES_REASONS, "status": APPT_STATUSES}[key]
                w98_combobox(row_f, textvariable=var, values=values, name=wname, width=28).pack(side=tk.LEFT, padx=4)
            else:
                w98_entry(row_f, textvariable=var, name=wname, width=32).pack(side=tk.LEFT, padx=4)

        notes_f = w98_frame(frm)
        notes_f.pack(fill=tk.X, padx=6, pady=3)
        w98_label(notes_f, text="Notes:").pack(anchor="nw")
        self._notes_txt = w98_text(notes_f, name="appt_notes", width=50, height=3)
        self._notes_txt.pack(fill=tk.X, pady=2)

        btn_row = w98_frame(self)
        btn_row.pack(pady=8)
        w98_button(btn_row, "Save", command=self._save, name="btn_save_appt", width=10).pack(side=tk.LEFT, padx=6)
        w98_button(btn_row, "Cancel", command=self.destroy, name="btn_cancel_appt", width=10).pack(side=tk.LEFT, padx=6)

        if preset_customer:
            self._resolved_cid = preset_customer["id"]
            self._customer_var.set(f"{preset_customer['last_name']}, {preset_customer['first_name']} ({preset_customer['customer_no']})")
        if is_edit:
            conn = get_connection()
            c = conn.execute("SELECT * FROM customers WHERE id=?", (self._row["customer_id"],)).fetchone()
            conn.close()
            if c:
                self._resolved_cid = c["id"]
                self._customer_var.set(f"{c['last_name']}, {c['first_name']} ({c['customer_no']})")
            if self._row["notes"]:
                self._notes_txt.insert("1.0", self._row["notes"])

    def _lookup_customer(self):
        CustomerLookupDialog(self, on_select=self._on_customer)

    def _on_customer(self, c):
        self._resolved_cid = c["id"]
        self._customer_var.set(f"{c['last_name']}, {c['first_name']} ({c['customer_no']})")

    def _save(self):
        if not self._resolved_cid:
            messagebox.showerror("Validation", "Please select a customer.", parent=self)
            return
        vals = {k: v.get().strip() for k, v in self._vars.items()}
        vals["notes"] = self._notes_txt.get("1.0", "end-1c").strip()
        if not vals["datetime"]:
            messagebox.showerror("Validation", "Date/Time is required.", parent=self)
            return

        _chaos_event("save")

        conn = get_connection()
        if self._row:
            conn.execute(
                "UPDATE appointments SET customer_id=?,datetime=?,advisor=?,reason=?,dept=?,status=?,notes=? WHERE id=?",
                (self._resolved_cid, vals["datetime"], vals["advisor"], vals["reason"], vals["dept"],
                 vals["status"], vals["notes"], self._row["id"]))
        else:
            conn.execute(
                "INSERT INTO appointments (customer_id,datetime,advisor,reason,dept,status,notes) VALUES (?,?,?,?,?,?,?)",
                (self._resolved_cid, vals["datetime"], vals["advisor"], vals["reason"], vals["dept"],
                 vals["status"], vals["notes"]))
        conn.commit()
        conn.close()
        self.on_save()
        self.destroy()
