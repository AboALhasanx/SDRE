from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from src.models.inlines import InlineCode, InlineLtr, InlineMath, InlineNode, InlineText


class InlineEditor(ctk.CTkFrame):
    """Simple list-based inline editor for paragraph and other inline arrays."""

    def __init__(self, master, nodes: list[InlineNode], on_change, **kwargs):
        super().__init__(master, **kwargs)
        self._nodes = nodes
        self._on_change = on_change

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        bar = ctk.CTkFrame(self)
        bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        for i in range(10):
            bar.grid_columnconfigure(i, weight=0)
        bar.grid_columnconfigure(99, weight=1)

        self.btn_add = ctk.CTkButton(bar, text="Add", width=80, command=self._add)
        self.btn_add.grid(row=0, column=0, padx=(0, 6), pady=6)
        self.btn_edit = ctk.CTkButton(bar, text="Edit", width=80, command=self._edit)
        self.btn_edit.grid(row=0, column=1, padx=(0, 6), pady=6)
        self.btn_del = ctk.CTkButton(bar, text="Delete", width=80, command=self._delete)
        self.btn_del.grid(row=0, column=2, padx=(0, 6), pady=6)
        self.btn_up = ctk.CTkButton(bar, text="Up", width=60, command=lambda: self._move(-1))
        self.btn_up.grid(row=0, column=3, padx=(0, 6), pady=6)
        self.btn_dn = ctk.CTkButton(bar, text="Down", width=60, command=lambda: self._move(1))
        self.btn_dn.grid(row=0, column=4, padx=(0, 6), pady=6)

        body = ctk.CTkFrame(self)
        body.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(body, columns=["type", "value", "style/lang"], show="headings", height=6)
        self.tree.heading("type", text="type")
        self.tree.heading("value", text="value")
        self.tree.heading("style/lang", text="style/lang")
        self.tree.column("type", width=110, stretch=False)
        self.tree.column("value", width=360, stretch=True)
        self.tree.column("style/lang", width=120, stretch=False)
        self.tree.grid(row=0, column=0, sticky="nsew")

        y = ttk.Scrollbar(body, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=y.set)
        y.grid(row=0, column=1, sticky="ns")

        self._refresh()

    def _refresh(self) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for i, n in enumerate(self._nodes):
            if isinstance(n, InlineText):
                extra = ""
                val = n.value
                typ = n.type
            elif isinstance(n, InlineLtr):
                extra = n.style or ""
                val = n.value
                typ = n.type
            elif isinstance(n, InlineMath):
                extra = ""
                val = n.value
                typ = n.type
            elif isinstance(n, InlineCode):
                extra = n.lang or ""
                val = n.value
                typ = n.type
            else:
                extra = ""
                val = ""
                typ = type(n).__name__
            self.tree.insert("", "end", iid=str(i), values=(typ, val, extra))

    def _selected_index(self) -> int | None:
        sel = self.tree.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except ValueError:
            return None

    def _commit(self) -> None:
        self._refresh()
        self._on_change()

    def _move(self, delta: int) -> None:
        i = self._selected_index()
        if i is None:
            return
        j = i + delta
        if j < 0 or j >= len(self._nodes):
            return
        self._nodes[i], self._nodes[j] = self._nodes[j], self._nodes[i]
        self._commit()
        self.tree.selection_set(str(j))

    def _delete(self) -> None:
        i = self._selected_index()
        if i is None:
            return
        del self._nodes[i]
        if not self._nodes:
            self._nodes.append(InlineText(type="text", value=""))
        self._commit()

    def _add(self) -> None:
        _InlineNodeDialog(self, title="Add Inline Node", initial=None, on_ok=self._add_node)

    def _add_node(self, node: InlineNode) -> None:
        self._nodes.append(node)
        self._commit()

    def _edit(self) -> None:
        i = self._selected_index()
        if i is None:
            return
        _InlineNodeDialog(self, title="Edit Inline Node", initial=self._nodes[i], on_ok=lambda n: self._set_node(i, n))

    def _set_node(self, idx: int, node: InlineNode) -> None:
        self._nodes[idx] = node
        self._commit()


class _InlineNodeDialog(ctk.CTkToplevel):
    def __init__(self, master, *, title: str, initial: InlineNode | None, on_ok):
        super().__init__(master)
        self.title(title)
        self.geometry("520x240")
        self.resizable(False, False)
        self._on_ok = on_ok

        self.grid_columnconfigure(1, weight=1)

        self.type_var = ctk.StringVar(value="text")
        self.value_var = ctk.StringVar(value="")
        self.style_var = ctk.StringVar(value="plain")
        self.lang_var = ctk.StringVar(value="")

        if initial is not None:
            self.type_var.set(initial.type)
            if isinstance(initial, InlineText):
                self.value_var.set(initial.value)
            elif isinstance(initial, InlineLtr):
                self.value_var.set(initial.value)
                self.style_var.set(initial.style or "plain")
            elif isinstance(initial, InlineMath):
                self.value_var.set(initial.value)
            elif isinstance(initial, InlineCode):
                self.value_var.set(initial.value)
                self.lang_var.set(initial.lang or "")

        ctk.CTkLabel(self, text="type").grid(row=0, column=0, padx=12, pady=(12, 6), sticky="w")
        self.type_menu = ctk.CTkOptionMenu(
            self,
            values=["text", "ltr", "inline_math", "inline_code"],
            variable=self.type_var,
            command=lambda _: self._sync_visibility(),
        )
        self.type_menu.grid(row=0, column=1, padx=12, pady=(12, 6), sticky="ew")

        ctk.CTkLabel(self, text="value").grid(row=1, column=0, padx=12, pady=6, sticky="w")
        self.value_entry = ctk.CTkEntry(self, textvariable=self.value_var)
        self.value_entry.grid(row=1, column=1, padx=12, pady=6, sticky="ew")

        self.style_label = ctk.CTkLabel(self, text="style")
        self.style_menu = ctk.CTkOptionMenu(self, values=["plain", "boxed", "mono"], variable=self.style_var)
        self.lang_label = ctk.CTkLabel(self, text="lang")
        self.lang_entry = ctk.CTkEntry(self, textvariable=self.lang_var)

        btns = ctk.CTkFrame(self)
        btns.grid(row=99, column=0, columnspan=2, sticky="ew", padx=12, pady=12)
        btns.grid_columnconfigure(0, weight=1)
        btns.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(btns, text="Cancel", command=self.destroy).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(btns, text="OK", command=self._ok).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self._sync_visibility()
        self.grab_set()
        self.value_entry.focus_set()

    def _sync_visibility(self) -> None:
        for w in (self.style_label, self.style_menu, self.lang_label, self.lang_entry):
            w.grid_forget()

        t = self.type_var.get()
        if t == "ltr":
            self.style_label.grid(row=2, column=0, padx=12, pady=6, sticky="w")
            self.style_menu.grid(row=2, column=1, padx=12, pady=6, sticky="ew")
        elif t == "inline_code":
            self.lang_label.grid(row=2, column=0, padx=12, pady=6, sticky="w")
            self.lang_entry.grid(row=2, column=1, padx=12, pady=6, sticky="ew")

    def _ok(self) -> None:
        t = self.type_var.get()
        v = self.value_var.get()
        if t in ("text", "ltr", "inline_math", "inline_code") and v is None:
            v = ""

        if t in ("ltr", "inline_math", "inline_code") and not v.strip():
            messagebox.showerror("Invalid", "value is required for this inline type.")
            return

        if t == "text":
            node: InlineNode = InlineText(type="text", value=v)
        elif t == "ltr":
            node = InlineLtr(type="ltr", value=v, style=self.style_var.get())
        elif t == "inline_math":
            node = InlineMath(type="inline_math", value=v)
        elif t == "inline_code":
            lang = self.lang_var.get().strip() or None
            node = InlineCode(type="inline_code", value=v, lang=lang)
        else:
            messagebox.showerror("Invalid", "Unknown inline type.")
            return

        self._on_ok(node)
        self.destroy()

