from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def make_treeview(master, columns: list[str], *, show: str = "tree") -> ttk.Treeview:
    tv = ttk.Treeview(master, columns=columns, show=show, selectmode="browse")
    for c in columns:
        tv.heading(c, text=c)
        tv.column(c, width=140, stretch=True)
    return tv


def add_scrollbars(master, widget: ttk.Treeview):
    y = ttk.Scrollbar(master, orient=tk.VERTICAL, command=widget.yview)
    widget.configure(yscrollcommand=y.set)
    return y

