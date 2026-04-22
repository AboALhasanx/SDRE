from __future__ import annotations

import customtkinter as ctk


class LogPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.status_var = ctk.StringVar(value="Ready")
        self.status = ctk.CTkLabel(self, textvariable=self.status_var, anchor="w")
        self.status.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))

        self.text = ctk.CTkTextbox(self, height=140)
        self.text.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.text.configure(state="disabled")

    def set_status(self, msg: str) -> None:
        self.status_var.set(msg)

    def clear(self) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")

    def append(self, msg: str) -> None:
        self.text.configure(state="normal")
        self.text.insert("end", msg)
        if not msg.endswith("\n"):
            self.text.insert("end", "\n")
        self.text.see("end")
        self.text.configure(state="disabled")

