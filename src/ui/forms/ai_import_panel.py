from __future__ import annotations

import json
from typing import Callable
from tkinter import ttk

import customtkinter as ctk

from src.ai.ai_service import AIGenerationResult
from src.validation.report import ValidationReport

GenerateDraftCallback = Callable[[str, str | None, str | None], AIGenerationResult]
ImportDraftCallback = Callable[[], ValidationReport]


class AIImportPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        *,
        on_generate: GenerateDraftCallback,
        on_import: ImportDraftCallback,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._on_generate = on_generate
        self._on_import = on_import

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=3)
        self.grid_rowconfigure(5, weight=2)
        self.grid_rowconfigure(7, weight=2)

        top = ctk.CTkFrame(self)
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 6))
        top.grid_columnconfigure(1, weight=1)
        top.grid_columnconfigure(3, weight=1)

        self.title_var = ctk.StringVar(value="")
        self.author_var = ctk.StringVar(value="")

        ctk.CTkLabel(top, text="Optional title").grid(row=0, column=0, padx=(8, 6), pady=8, sticky="w")
        ctk.CTkEntry(top, textvariable=self.title_var).grid(row=0, column=1, padx=(0, 12), pady=8, sticky="ew")
        ctk.CTkLabel(top, text="Optional author").grid(row=0, column=2, padx=(0, 6), pady=8, sticky="w")
        ctk.CTkEntry(top, textvariable=self.author_var).grid(row=0, column=3, padx=(0, 8), pady=8, sticky="ew")

        ctk.CTkLabel(self, text="Raw source text").grid(row=1, column=0, sticky="w", padx=8)
        self.raw_text = ctk.CTkTextbox(self)
        self.raw_text.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 6))

        btns = ctk.CTkFrame(self)
        btns.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 6))
        ctk.CTkButton(btns, text="Generate Draft", width=130, command=self._generate_clicked).grid(row=0, column=0, padx=(0, 6), pady=6)
        ctk.CTkButton(btns, text="Import Generated Project", width=170, command=self._import_clicked).grid(
            row=0, column=1, padx=(0, 6), pady=6
        )
        ctk.CTkButton(btns, text="Clear", width=90, command=self._clear_clicked).grid(row=0, column=2, pady=6)

        self.status_var = ctk.StringVar(value="AI draft status: -")
        ctk.CTkLabel(self, textvariable=self.status_var, anchor="w").grid(row=4, column=0, sticky="ew", padx=8, pady=(0, 4))

        result_frame = ctk.CTkFrame(self)
        result_frame.grid(row=5, column=0, sticky="nsew", padx=8, pady=(0, 6))
        result_frame.grid_columnconfigure(0, weight=1)
        result_frame.grid_rowconfigure(0, weight=1)

        self.results = ttk.Treeview(
            result_frame,
            columns=["status", "stage", "line", "column", "path", "message", "hint"],
            show="headings",
            height=6,
        )
        for col in ("status", "stage", "line", "column", "path", "message", "hint"):
            self.results.heading(col, text=col)
        self.results.column("status", width=80, stretch=False, anchor="center")
        self.results.column("stage", width=100, stretch=False)
        self.results.column("line", width=60, stretch=False, anchor="center")
        self.results.column("column", width=60, stretch=False, anchor="center")
        self.results.column("path", width=190, stretch=False)
        self.results.column("message", width=420, stretch=True)
        self.results.column("hint", width=260, stretch=True)
        self.results.grid(row=0, column=0, sticky="nsew")
        y = ttk.Scrollbar(result_frame, orient="vertical", command=self.results.yview)
        self.results.configure(yscrollcommand=y.set)
        y.grid(row=0, column=1, sticky="ns")

        ctk.CTkLabel(self, text="Generated JSON preview").grid(row=6, column=0, sticky="w", padx=8)
        self.preview = ctk.CTkTextbox(self)
        self.preview.grid(row=7, column=0, sticky="nsew", padx=8, pady=(0, 8))

    def _clear_results(self) -> None:
        for iid in self.results.get_children():
            self.results.delete(iid)

    def _show_validation_report(self, report: ValidationReport) -> None:
        self._clear_results()
        if report.ok:
            self.results.insert("", "end", values=("ok", report.stage, "", "", "/", "Validation passed", ""))
            return
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

    def _generate_clicked(self) -> None:
        raw = self.raw_text.get("1.0", "end-1c")
        title = self.title_var.get().strip() or None
        author = self.author_var.get().strip() or None
        result = self._on_generate(raw, title, author)

        if result.sanitized_payload is not None:
            preview_text = json.dumps(result.sanitized_payload, ensure_ascii=False, indent=2)
        elif result.parsed_draft is not None:
            preview_text = json.dumps(result.parsed_draft, ensure_ascii=False, indent=2)
        else:
            preview_text = result.raw_output
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", preview_text)

        if result.validation_report is not None:
            self._show_validation_report(result.validation_report)
        else:
            self._clear_results()

        self.status_var.set(self._build_status_line(result))

    def _build_status_line(self, result: AIGenerationResult) -> str:
        base = f"AI draft: {'ok' if result.ok else 'failed'} | stage={result.stage} | attempts={result.attempts}"
        if result.ok:
            if result.attempts > 1:
                return f"{base} | recovered_after_retry"
            return base

        if result.failure_class:
            base += f" | class={result.failure_class}"
        if result.max_retries_exceeded:
            base += " | max_retries_exceeded"
        if result.semantic_reasons:
            base += f" | semantic={result.semantic_reasons[0]}"
        return base

    def _import_clicked(self) -> None:
        report = self._on_import()
        self._show_validation_report(report)
        self.status_var.set(
            f"AI import status: {'ok' if report.ok else 'failed'} | stage={report.stage}"
        )

    def _clear_clicked(self) -> None:
        self.raw_text.delete("1.0", "end")
        self.preview.delete("1.0", "end")
        self._clear_results()
        self.status_var.set("AI draft status: -")
