from __future__ import annotations

import json
import queue
import threading
from typing import Callable
from tkinter import ttk

import customtkinter as ctk

from src.ai.ai_service import AIGenerationResult
from src.validation.report import ValidationReport

GenerateDraftCallback = Callable[..., AIGenerationResult]
ImportDraftCallback = Callable[[], ValidationReport]
GenerationDoneCallback = Callable[[AIGenerationResult], None]


class AIImportPanel(ctk.CTkFrame):
    LONG_TEXT_WARNING_CHARS = 5000

    def __init__(
        self,
        master,
        *,
        on_generate: GenerateDraftCallback,
        on_import: ImportDraftCallback,
        on_generation_done: GenerationDoneCallback | None = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._on_generate = on_generate
        self._on_import = on_import
        self._on_generation_done = on_generation_done
        self._is_generating = False
        self._worker_queue: queue.Queue[dict] = queue.Queue()
        self._worker_thread: threading.Thread | None = None
        self._cancel_event: threading.Event | None = None

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
        self.generate_btn = ctk.CTkButton(btns, text="Generate Draft", width=130, command=self._generate_clicked)
        self.generate_btn.grid(row=0, column=0, padx=(0, 6), pady=6)
        self.cancel_btn = ctk.CTkButton(
            btns,
            text="Cancel",
            width=90,
            state="disabled",
            command=self._cancel_clicked,
        )
        self.cancel_btn.grid(row=0, column=1, padx=(0, 6), pady=6)
        self.import_btn = ctk.CTkButton(btns, text="Import Generated Project", width=170, command=self._import_clicked)
        self.import_btn.grid(row=0, column=2, padx=(0, 6), pady=6)
        self.clear_btn = ctk.CTkButton(btns, text="Clear", width=90, command=self._clear_clicked)
        self.clear_btn.grid(row=0, column=3, pady=6)

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
        if self._is_generating:
            return

        raw = self.raw_text.get("1.0", "end-1c")
        title = self.title_var.get().strip() or None
        author = self.author_var.get().strip() or None
        self._set_generating(True)
        self._cancel_event = threading.Event()
        status = "Generating draft..."
        if len(raw) >= self.LONG_TEXT_WARNING_CHARS:
            status += " Long input detected; retries may increase API usage."
        self.status_var.set(status)

        self._worker_thread = threading.Thread(
            target=self._run_generate_worker,
            args=(raw, title, author, self._cancel_event),
            daemon=True,
        )
        self._worker_thread.start()
        self.after(120, self._drain_worker_queue)

    def _run_generate_worker(self, raw: str, title: str | None, author: str | None, cancel_event: threading.Event) -> None:
        try:
            result = self._on_generate(
                raw,
                title,
                author,
                progress_callback=self._queue_progress,
                cancel_event=cancel_event,
            )
        except Exception as exc:
            result = AIGenerationResult(
                ok=False,
                stage="worker",
                message=f"AI generation worker failed: {exc}",
                failure_class="technical",
            )
        self._worker_queue.put({"type": "result", "result": result})

    def _queue_progress(self, payload: dict) -> None:
        self._worker_queue.put({"type": "progress", "payload": payload})

    def _drain_worker_queue(self) -> None:
        got_result = False
        while True:
            try:
                item = self._worker_queue.get_nowait()
            except queue.Empty:
                break

            kind = item.get("type")
            if kind == "progress":
                payload = item.get("payload") or {}
                self._handle_progress(payload)
            elif kind == "result":
                result = item.get("result")
                if isinstance(result, AIGenerationResult):
                    self._handle_result(result)
                got_result = True

        if self._is_generating and not got_result:
            self.after(120, self._drain_worker_queue)

    def _handle_progress(self, payload: dict) -> None:
        event = payload.get("event")
        chunk_index = payload.get("chunk_index")
        total_chunks = payload.get("total_chunks")
        chunk_prefix = f"[chunk {chunk_index}/{total_chunks}] " if chunk_index and total_chunks else ""
        if event == "chunk_mode":
            total = payload.get("total_chunks", "?")
            self.status_var.set(f"Chunked generation enabled ({total} chunks).")
            return
        if event == "chunk_start":
            self.status_var.set(
                f"Generating chunk {payload.get('chunk_index', '?')}/{payload.get('total_chunks', '?')}..."
            )
            return
        if event == "chunk_done":
            self.status_var.set(
                f"Completed chunk {payload.get('chunk_index', '?')}/{payload.get('total_chunks', '?')}."
            )
            return
        if event == "chunk_failed":
            self.status_var.set(
                f"Chunk {payload.get('chunk_index', '?')}/{payload.get('total_chunks', '?')} failed."
            )
            return
        if event == "attempt":
            attempt = payload.get("attempt", "?")
            max_attempts = payload.get("max_attempts", "?")
            mode = str(payload.get("mode", "initial"))
            if mode != "initial":
                self.status_var.set(f"{chunk_prefix}Generating draft... attempt {attempt}/{max_attempts} (retry: {mode})")
            else:
                self.status_var.set(f"{chunk_prefix}Generating draft... attempt {attempt}/{max_attempts}")
            return
        if event == "retry":
            reason = str(payload.get("reason", "")).strip()
            next_attempt = payload.get("next_attempt", "?")
            if reason:
                self.status_var.set(f"{chunk_prefix}Retrying generation (attempt {next_attempt})... {reason}")
            else:
                self.status_var.set(f"{chunk_prefix}Retrying generation (attempt {next_attempt})...")
            return

    def _handle_result(self, result: AIGenerationResult) -> None:
        self._set_generating(False)
        self._cancel_event = None

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
        if self._on_generation_done is not None:
            self._on_generation_done(result)

    def _build_status_line(self, result: AIGenerationResult) -> str:
        if result.canceled:
            return f"AI draft: cancelled | attempts={result.attempts}"
        base = f"AI draft: {'ok' if result.ok else 'failed'} | stage={result.stage} | attempts={result.attempts}"
        if result.chunked_mode:
            base += f" | chunked {result.completed_chunks}/{result.total_chunks}"
            if result.failed_chunk_indices:
                joined = ",".join(str(i) for i in result.failed_chunk_indices)
                base += f" | failed_chunks={joined}"
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
        if self._is_generating:
            self.status_var.set("Generation is still running. Please wait for completion or cancel.")
            return
        report = self._on_import()
        self._show_validation_report(report)
        self.status_var.set(
            f"AI import status: {'ok' if report.ok else 'failed'} | stage={report.stage}"
        )

    def _clear_clicked(self) -> None:
        if self._is_generating:
            self.status_var.set("Cannot clear while generation is running. Cancel first if needed.")
            return
        self.raw_text.delete("1.0", "end")
        self.preview.delete("1.0", "end")
        self._clear_results()
        self.status_var.set("AI draft status: -")

    def _cancel_clicked(self) -> None:
        if not self._is_generating:
            return
        if self._cancel_event is not None:
            self._cancel_event.set()
        self.status_var.set("Cancel requested... waiting for current attempt to finish.")

    def _set_generating(self, generating: bool) -> None:
        self._is_generating = generating
        if generating:
            self.generate_btn.configure(state="disabled")
            self.cancel_btn.configure(state="normal")
            self.import_btn.configure(state="disabled")
            self.clear_btn.configure(state="disabled")
        else:
            self.generate_btn.configure(state="normal")
            self.cancel_btn.configure(state="disabled")
            self.import_btn.configure(state="normal")
            self.clear_btn.configure(state="normal")
