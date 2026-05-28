"""Reusable Windows 98-styled widget primitives."""
import tkinter as tk
from tkinter import ttk
from ui import style


def _w98_button(parent, text, command=None, name=None, width=10, **kw):
    kwargs = dict(
        text=text,
        command=command,
        font=style.FONT,
        bg=style.BUTTON_BG,
        relief=style.RELIEF_BUTTON,
        bd=style.BORDER,
        cursor="arrow",
        activebackground=style.BG_DARK,
        activeforeground=style.TITLE_FG,
        width=width,
    )
    kwargs.update(kw)
    if name:
        return tk.Button(parent, name=name, **kwargs)
    return tk.Button(parent, **kwargs)


def w98_button(parent, text, command=None, name=None, width=10, **kw):
    btn = _w98_button(parent, text, command, name, width, **kw)
    return btn


def w98_label(parent, text="", name=None, bold=False, fg=None, **kw):
    kwargs = dict(
        text=text,
        font=style.FONT_BOLD if bold else style.FONT,
        bg=style.BG,
        fg=fg or style.ENTRY_FG,
    )
    kwargs.update(kw)
    if name:
        return tk.Label(parent, name=name, **kwargs)
    return tk.Label(parent, **kwargs)


def w98_entry(parent, textvariable=None, name=None, width=20, show=None, **kw):
    kwargs = dict(
        font=style.FONT,
        bg=style.ENTRY_BG,
        fg=style.ENTRY_FG,
        relief=style.RELIEF_ENTRY,
        bd=style.BORDER,
        width=width,
    )
    if textvariable:
        kwargs["textvariable"] = textvariable
    if show:
        kwargs["show"] = show
    kwargs.update(kw)
    if name:
        return tk.Entry(parent, name=name, **kwargs)
    return tk.Entry(parent, **kwargs)


def w98_text(parent, name=None, width=40, height=6, **kw):
    kwargs = dict(
        font=style.FONT_MONO,
        bg=style.ENTRY_BG,
        fg=style.ENTRY_FG,
        relief=style.RELIEF_ENTRY,
        bd=style.BORDER,
        width=width,
        height=height,
        wrap=tk.WORD,
    )
    kwargs.update(kw)
    if name:
        return tk.Text(parent, name=name, **kwargs)
    return tk.Text(parent, **kwargs)


def w98_combobox(parent, textvariable=None, values=None, name=None, width=18, **kw):
    style_obj = ttk.Style()
    style_obj.theme_use("default")
    style_obj.configure("W98.TCombobox",
                        fieldbackground=style.ENTRY_BG,
                        background=style.BUTTON_BG,
                        foreground=style.ENTRY_FG,
                        font=style.FONT)
    kwargs = dict(
        style="W98.TCombobox",
        width=width,
        font=style.FONT,
    )
    if textvariable:
        kwargs["textvariable"] = textvariable
    if values:
        kwargs["values"] = values
    kwargs.update(kw)
    if name:
        return ttk.Combobox(parent, name=name, **kwargs)
    return ttk.Combobox(parent, **kwargs)


def w98_listbox(parent, name=None, width=40, height=15, **kw):
    kwargs = dict(
        font=style.FONT,
        bg=style.ENTRY_BG,
        fg=style.ENTRY_FG,
        selectbackground=style.SELECT_BG,
        selectforeground=style.SELECT_FG,
        relief=style.RELIEF_ENTRY,
        bd=style.BORDER,
        width=width,
        height=height,
        activestyle="none",
    )
    kwargs.update(kw)
    if name:
        return tk.Listbox(parent, name=name, **kwargs)
    return tk.Listbox(parent, **kwargs)


def w98_scrollbar(parent, orient=tk.VERTICAL, **kw):
    return tk.Scrollbar(parent, orient=orient, bg=style.BG, troughcolor=style.BG_DARK, **kw)


def w98_frame(parent, relief=None, bd=None, **kw):
    return tk.Frame(parent, bg=style.BG, relief=relief or "flat", bd=bd or 0, **kw)


def w98_labelframe(parent, text="", **kw):
    return tk.LabelFrame(
        parent, text=text, font=style.FONT_BOLD, bg=style.BG,
        fg=style.ENTRY_FG, relief="groove", bd=style.BORDER, **kw
    )


def title_bar(parent, text, **kw):
    bar = tk.Label(
        parent, text=text, font=style.FONT_TITLE,
        bg=style.TITLE_BG, fg=style.TITLE_FG,
        anchor="w", padx=6, pady=3, **kw
    )
    return bar


class StatusBar(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=style.STATUS_BG, relief="sunken", bd=1, **kw)
        self._var = tk.StringVar(value="Ready")
        self._label = tk.Label(
            self, textvariable=self._var,
            font=style.FONT_SMALL, bg=style.STATUS_BG, anchor="w", padx=4
        )
        self._label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def set(self, msg: str):
        self._var.set(msg)
        self.update_idletasks()


class W98Treeview(ttk.Treeview):
    """Treeview with minimal W98-ish styling."""
    def __init__(self, parent, **kw):
        s = ttk.Style()
        s.theme_use("default")
        s.configure("W98.Treeview",
                    background=style.ENTRY_BG,
                    foreground=style.ENTRY_FG,
                    fieldbackground=style.ENTRY_BG,
                    font=style.FONT,
                    rowheight=18)
        s.configure("W98.Treeview.Heading",
                    background=style.BG,
                    foreground=style.ENTRY_FG,
                    font=style.FONT_BOLD,
                    relief="raised")
        s.map("W98.Treeview",
              background=[("selected", style.SELECT_BG)],
              foreground=[("selected", style.SELECT_FG)])
        kw.setdefault("style", "W98.Treeview")
        super().__init__(parent, **kw)
