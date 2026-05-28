import tkinter as tk
from tkinter import messagebox, ttk
from ui import style
from ui.widgets import (
    w98_button, w98_entry, w98_label, w98_frame, w98_labelframe, w98_combobox, w98_scrollbar, title_bar,
)
from ui.constants import CUSTOMER_TYPES, STATES, SALESPEOPLE
from db.connection import get_connection


def _chaos_event(event_type):
    try:
        from chaos.engine import get_engine
        e = get_engine()
        if e:
            e.on_event(event_type)
    except Exception:
        pass


def _fetch_customers(search=""):
    conn = get_connection()
    if search:
        q = f"%{search}%"
        rows = conn.execute(
            "SELECT * FROM customers WHERE first_name LIKE ? OR last_name LIKE ? "
            "OR customer_no LIKE ? OR phone LIKE ? ORDER BY last_name, first_name",
            (q, q, q, q),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM customers ORDER BY last_name, first_name").fetchall()
    conn.close()
    return rows


class CustomerListPanel(tk.Frame):
    def __init__(self, parent, dashboard):
        super().__init__(parent, bg=style.BG)
        self.dashboard = dashboard
        self._rows = []
        self._build()
        self.refresh()

    def _build(self):
        title_bar(self, "  Customer List").pack(fill=tk.X)

        bar = w98_frame(self)
        bar.pack(fill=tk.X, padx=6, pady=5)
        w98_label(bar, text="Search:").pack(side=tk.LEFT)
        self._search_var = tk.StringVar()
        self._search_entry = w98_entry(bar, textvariable=self._search_var,
                                       name="customer_search", width=34)
        self._search_entry.pack(side=tk.LEFT, padx=4)
        w98_button(bar, "Search", command=self.refresh,
                   name="btn_search_customers", width=8).pack(side=tk.LEFT, padx=2)
        w98_button(bar, "Show All", command=self._clear_search,
                   name="btn_clear_search", width=8).pack(side=tk.LEFT, padx=2)
        self._search_entry.bind("<Return>", lambda e: self.refresh())

        self._count_label = tk.Label(bar, text="", font=style.FONT_BOLD,
                                     bg=style.BG_DARK, fg="white", padx=8, pady=2, relief="sunken")
        self._count_label.pack(side=tk.RIGHT, padx=6)

        list_frame = w98_frame(self, relief="sunken", bd=2)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)

        cols = ("customer_no", "last_name", "first_name", "phone", "city", "customer_type", "salesperson")
        self._tree = ttk.Treeview(list_frame, columns=cols, show="headings",
                                  style="W98.Treeview", name="customer_tree", selectmode="browse")
        for col, heading, w in [
            ("customer_no", "Cust #", 90), ("last_name", "Last Name", 140),
            ("first_name", "First Name", 130), ("phone", "Phone", 130),
            ("city", "City", 110), ("customer_type", "Type", 80), ("salesperson", "Salesperson", 150),
        ]:
            self._tree.heading(col, text=heading, command=lambda c=col: self._sort_by(c))
            self._tree.column(col, width=w, anchor="w", minwidth=60)

        vsb = w98_scrollbar(list_frame, command=self._tree.yview)
        hsb = w98_scrollbar(list_frame, orient=tk.HORIZONTAL, command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        self._tree.bind("<Double-1>", lambda e: self._open_detail())
        self._tree.bind("<<TreeviewSelect>>", lambda e: self._on_select())
        self._sort_col, self._sort_rev = None, False

        btn_bar = w98_frame(self)
        btn_bar.pack(fill=tk.X, padx=6, pady=4)
        w98_button(btn_bar, "Open Record", command=self._open_detail,
                   name="btn_open_customer", width=12).pack(side=tk.LEFT, padx=3)
        w98_button(btn_bar, "Add New Customer", command=self._add_customer,
                   name="btn_add_customer", width=16).pack(side=tk.LEFT, padx=3)
        w98_button(btn_bar, "Edit", command=self._edit_customer,
                   name="btn_edit_customer", width=8).pack(side=tk.LEFT, padx=3)
        w98_button(btn_bar, "Delete", command=self._delete_customer,
                   name="btn_delete_customer", width=8).pack(side=tk.LEFT, padx=3)

        preview_lf = tk.LabelFrame(self, text="Selected Customer", font=style.FONT_BOLD,
                                   bg=style.BG, fg=style.TITLE_BG, relief="groove", bd=2)
        preview_lf.pack(fill=tk.X, padx=6, pady=(0, 4))
        prev_inner = w98_frame(preview_lf)
        prev_inner.pack(fill=tk.X, padx=6, pady=4)
        self._preview_fields = {}
        preview_items = [("Name:", "name"), ("Cust #:", "customer_no"), ("Phone:", "phone"),
                         ("Email:", "email"), ("City:", "city"), ("Type:", "customer_type"),
                         ("Salesperson:", "salesperson")]
        for i, (label, key) in enumerate(preview_items):
            col_offset = i * 2
            tk.Label(prev_inner, text=label, font=style.FONT_BOLD, bg=style.BG, fg=style.ENTRY_FG,
                     anchor="e").grid(row=0, column=col_offset, sticky="e", padx=(8, 2))
            var = tk.StringVar(value="-")
            self._preview_fields[key] = var
            tk.Label(prev_inner, textvariable=var, font=style.FONT, bg=style.ENTRY_BG, fg=style.ENTRY_FG,
                     relief="sunken", bd=1, anchor="w", width=16, padx=4).grid(
                row=0, column=col_offset + 1, sticky="w", padx=(0, 4))

    def refresh(self):
        search = self._search_var.get().strip()
        self._rows = _fetch_customers(search)
        self._tree.delete(*self._tree.get_children())
        for row in self._rows:
            self._tree.insert("", "end", iid=str(row["id"]),
                              values=(row["customer_no"], row["last_name"], row["first_name"],
                                      row["phone"], row["city"], row["customer_type"], row["salesperson"]))
        self._tree.tag_configure("odd", background="#F0F0F8")
        for i, iid in enumerate(self._tree.get_children()):
            if i % 2 == 1:
                self._tree.item(iid, tags=("odd",))
        total = len(self._rows)
        self._count_label.config(text=f"  {total} customer{'s' if total != 1 else ''}  ")
        self.dashboard.status_bar.set(f"Loaded {total} customers")
        self._clear_preview()

    def _sort_by(self, col):
        data = [(self._tree.set(iid, col), iid) for iid in self._tree.get_children()]
        self._sort_rev = not self._sort_rev if self._sort_col == col else False
        self._sort_col = col
        data.sort(reverse=self._sort_rev)
        for i, (_, iid) in enumerate(data):
            self._tree.move(iid, "", i)
        self._tree.tag_configure("odd", background="#F0F0F8")
        for i, iid in enumerate(self._tree.get_children()):
            self._tree.item(iid, tags=("odd",) if i % 2 == 1 else ())

    def _clear_search(self):
        self._search_var.set("")
        self.refresh()

    def _selected_id(self):
        sel = self._tree.selection()
        return int(sel[0]) if sel else None

    def _on_select(self):
        cid = self._selected_id()
        if not cid:
            self._clear_preview()
            return
        conn = get_connection()
        row = conn.execute("SELECT * FROM customers WHERE id=?", (cid,)).fetchone()
        conn.close()
        if row:
            self._preview_fields["name"].set(f"{row['last_name']}, {row['first_name']}")
            self._preview_fields["customer_no"].set(row["customer_no"])
            self._preview_fields["phone"].set(row["phone"] or "-")
            self._preview_fields["email"].set(row["email"] or "-")
            self._preview_fields["city"].set(row["city"] or "-")
            self._preview_fields["customer_type"].set(row["customer_type"] or "-")
            self._preview_fields["salesperson"].set(row["salesperson"] or "-")
            self.dashboard.status_bar.set(
                f"{row['last_name']}, {row['first_name']}  |  {row['customer_no']}  |  {row['phone']}")

    def _clear_preview(self):
        for var in self._preview_fields.values():
            var.set("-")

    def _open_detail(self):
        cid = self._selected_id()
        if not cid:
            messagebox.showinfo("Select Customer", "Please select a customer first.", parent=self)
            return
        _chaos_event("navigate")
        conn = get_connection()
        row = conn.execute("SELECT * FROM customers WHERE id=?", (cid,)).fetchone()
        conn.close()
        from ui.customer_detail import CustomerDetailWindow
        CustomerDetailWindow(self, row, on_close=self.refresh)

    def _add_customer(self):
        CustomerFormDialog(self, None, on_save=self.refresh)

    def _edit_customer(self):
        cid = self._selected_id()
        if not cid:
            messagebox.showinfo("Select Customer", "Please select a customer first.", parent=self)
            return
        conn = get_connection()
        row = conn.execute("SELECT * FROM customers WHERE id=?", (cid,)).fetchone()
        conn.close()
        CustomerFormDialog(self, row, on_save=self.refresh)

    def _delete_customer(self):
        cid = self._selected_id()
        if not cid:
            messagebox.showinfo("Select Customer", "Please select a customer first.", parent=self)
            return
        if messagebox.askyesno("Delete", "Delete this customer and all related records?", parent=self):
            conn = get_connection()
            conn.execute("DELETE FROM customers WHERE id=?", (cid,))
            conn.commit()
            conn.close()
            self.refresh()
            self.dashboard.status_bar.set("Customer deleted.")


class CustomerFormDialog(tk.Toplevel):
    def __init__(self, parent, row, on_save):
        super().__init__(parent)
        self.on_save = on_save
        self._row = row
        is_edit = row is not None
        self.title("Edit Customer" if is_edit else "Add New Customer")
        self.resizable(False, False)
        self.configure(bg=style.BG)
        self.grab_set()
        self._build(is_edit)
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build(self, is_edit):
        title_bar(self, "  Edit Customer" if is_edit else "  Add New Customer").pack(fill=tk.X)
        frm = w98_labelframe(self, text="Customer Information")
        frm.pack(padx=12, pady=8, fill=tk.BOTH, expand=True)

        fields = [
            ("Customer #:", "customer_no", "entry"),
            ("First Name:", "first_name", "entry"),
            ("Last Name:", "last_name", "entry"),
            ("Phone:", "phone", "entry"),
            ("Email:", "email", "entry"),
            ("Address:", "address", "entry"),
            ("City:", "city", "entry"),
            ("State:", "state", "combo"),
            ("ZIP:", "zip", "entry"),
            ("Customer Type:", "customer_type", "combo"),
            ("Salesperson:", "salesperson", "combo"),
        ]
        self._vars = {}
        for i, (label, key, ftype) in enumerate(fields):
            w98_label(frm, text=label).grid(row=i, column=0, sticky="e", padx=6, pady=3)
            var = tk.StringVar(value=self._row[key] if is_edit else "")
            self._vars[key] = var
            if ftype == "combo":
                values = {"state": STATES, "customer_type": CUSTOMER_TYPES, "salesperson": SALESPEOPLE}[key]
                w98_combobox(frm, textvariable=var, values=values, name=f"field_{key}", width=30).grid(
                    row=i, column=1, sticky="w", padx=6, pady=3)
            else:
                w98_entry(frm, textvariable=var, name=f"field_{key}", width=34).grid(
                    row=i, column=1, sticky="w", padx=6, pady=3)

        btn_row = w98_frame(self)
        btn_row.pack(pady=8)
        w98_button(btn_row, "Save", command=self._save, name="btn_save_customer", width=10).pack(side=tk.LEFT, padx=6)
        w98_button(btn_row, "Cancel", command=self.destroy, name="btn_cancel_customer", width=10).pack(side=tk.LEFT, padx=6)

    def _save(self):
        vals = {k: v.get().strip() for k, v in self._vars.items()}
        if not vals["customer_no"] or not vals["first_name"] or not vals["last_name"]:
            messagebox.showerror("Validation", "Customer #, First Name and Last Name are required.", parent=self)
            return
        conn = get_connection()
        if self._row:
            conn.execute(
                "UPDATE customers SET customer_no=?,first_name=?,last_name=?,phone=?,email=?,"
                "address=?,city=?,state=?,zip=?,customer_type=?,salesperson=? WHERE id=?",
                (vals["customer_no"], vals["first_name"], vals["last_name"], vals["phone"], vals["email"],
                 vals["address"], vals["city"], vals["state"], vals["zip"], vals["customer_type"],
                 vals["salesperson"], self._row["id"]))
        else:
            conn.execute(
                "INSERT INTO customers (customer_no,first_name,last_name,phone,email,address,city,state,zip,customer_type,salesperson)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (vals["customer_no"], vals["first_name"], vals["last_name"], vals["phone"], vals["email"],
                 vals["address"], vals["city"], vals["state"], vals["zip"], vals["customer_type"], vals["salesperson"]))
        conn.commit()
        conn.close()
        self.on_save()
        self.destroy()
