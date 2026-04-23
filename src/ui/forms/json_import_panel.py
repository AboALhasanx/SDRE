from __future__ import annotations

import json
from typing import Callable

import customtkinter as ctk
from tkinter import ttk

from src.validation.report import ValidationReport


LoadJsonCallback = Callable[[], tuple[str, str] | None]
ValidateJsonCallback = Callable[[str], ValidationReport]
ImportJsonCallback = Callable[[str], ValidationReport]


class JsonImportPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        *,
        on_validate: ValidateJsonCallback,
        on_import: ImportJsonCallback,
        on_load_file: LoadJsonCallback,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._on_validate = on_validate
        self._on_import = on_import
        self._on_load_file = on_load_file

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=3)
        self.grid_rowconfigure(3, weight=2)

        self.editor = ctk.CTkTextbox(self)
        self.editor.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 6))

        btns = ctk.CTkFrame(self)
        btns.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))
        ctk.CTkButton(btns, text="Validate JSON", width=120, command=self._validate_clicked).grid(row=0, column=0, padx=(0, 6), pady=6)
        ctk.CTkButton(btns, text="Import JSON", width=120, command=self._import_clicked).grid(row=0, column=1, padx=(0, 6), pady=6)
        ctk.CTkButton(btns, text="Pretty Format JSON", width=140, command=self._pretty_format_clicked).grid(
            row=0, column=2, padx=(0, 6), pady=6
        )
        ctk.CTkButton(btns, text="Clear", width=90, command=self._clear_clicked).grid(row=0, column=3, padx=(0, 6), pady=6)
        ctk.CTkButton(btns, text="Load JSON From File", width=150, command=self._load_clicked).grid(row=0, column=4, pady=6)

        self.summary_var = ctk.StringVar(value="Validation status: -")
        ctk.CTkLabel(self, textvariable=self.summary_var, anchor="w").grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 4))

        table_frame = ctk.CTkFrame(self)
        table_frame.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 8))
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        self.results = ttk.Treeview(
            table_frame,
            columns=["status", "stage", "line", "column", "path", "message", "hint"],
            show="headings",
            height=8,
        )
        self.results.heading("status", text="status")
        self.results.heading("stage", text="stage")
        self.results.heading("line", text="line")
        self.results.heading("column", text="column")
        self.results.heading("path", text="path")
        self.results.heading("message", text="message")
        self.results.heading("hint", text="hint")
        self.results.column("status", width=90, stretch=False, anchor="center")
        self.results.column("stage", width=110, stretch=False)
        self.results.column("line", width=65, stretch=False, anchor="center")
        self.results.column("column", width=65, stretch=False, anchor="center")
        self.results.column("path", width=220, stretch=False)
        self.results.column("message", width=420, stretch=True)
        self.results.column("hint", width=320, stretch=True)
        self.results.grid(row=0, column=0, sticky="nsew")

        y = ttk.Scrollbar(table_frame, orient="vertical", command=self.results.yview)
        self.results.configure(yscrollcommand=y.set)
        y.grid(row=0, column=1, sticky="ns")

    def get_text(self) -> str:
        return self.editor.get("1.0", "end-1c")

    def set_text(self, text: str) -> None:
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", text)

    def _clear_results(self) -> None:
        for iid in self.results.get_children():
            self.results.delete(iid)

    def _show_report(self, report: ValidationReport, *, imported: bool = False) -> None:
        self._clear_results()
        if report.ok:
            summary = f"Validation status: ok | stage={report.stage}"
            if imported:
                summary += " | imported into project state"
            self.summary_var.set(summary)
            self.results.insert("", "end", values=("ok", report.stage, "", "", "/", "Validation passed", ""))
            return

        self.summary_var.set(f"Validation status: failed | stage={report.stage} | errors={len(report.errors)}")
        for err in report.errors:
            self.results.insert(
                "",
                "end",
                values=(
                    "failed",
                    report.stage,
                    str(err.line) if err.line is not None else "",
                    str(err.column) if err.column is not None else "",
                    err.path,
                    err.message,
                    err.hint,
                ),
            )

    def _validate_clicked(self) -> None:
        report = self._on_validate(self.get_text())
        self._show_report(report)

    def _import_clicked(self) -> None:
        report = self._on_import(self.get_text())
        self._show_report(report, imported=report.ok)

    def _pretty_format_clicked(self) -> None:
        raw = self.get_text()
        if not raw.strip():
            self.summary_var.set("Validation status: -")
            return
        report = self._on_validate(raw)
        if not report.ok:
            self._show_report(report)
            return
        parsed = json.loads(raw)
        self.set_text(json.dumps(parsed, ensure_ascii=False, indent=2))
        self.summary_var.set("Validation status: ok | pretty-formatted")
        self._clear_results()
        self.results.insert("", "end", values=("ok", report.stage, "", "", "/", "Pretty format applied", ""))

    def _clear_clicked(self) -> None:
        self.set_text("")
        self._clear_results()
        self.summary_var.set("Validation status: -")

    def _load_clicked(self) -> None:
        loaded = self._on_load_file()
        if loaded is None:
            return
        path, text = loaded
        self.set_text(text)
        self.summary_var.set(f"Loaded JSON from: {path}")
        self._clear_results()
