from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from src.ai.ai_service import AIGenerationResult, AIService
from src.generator.engine import generate_content
from src.models.project import ProjectFile
from src.services.build_service import BuildReport, build_pdf
from src.validation.engine import (
    ValidationReport,
    validate_json_text,
    validate_project_data,
    validate_project_file,
)

from src.ui.state import project_state as ps


class AppController:
    """UI controller: coordinates file IO + backend services + in-memory state."""

    def __init__(self) -> None:
        self.path: Path | None = None
        self.project_file = ps.new_project_file()
        self.dirty = False
        self.last_validation: ValidationReport | None = None
        self.last_build: BuildReport | None = None
        self.output_dir: Path | None = None
        self.custom_filename: str = ""
        self.use_auto_name: bool = True
        self.last_output_pdf_path: Path | None = None
        self.ai_service = AIService()
        self.ai_last_result: AIGenerationResult | None = None
        self.ai_generated_payload: dict | None = None
        self.ai_generated_json_text: str = ""

    @staticmethod
    def _repo_root() -> Path:
        return Path(__file__).resolve().parents[3]

    def _build_dir(self) -> Path:
        return self._repo_root() / "build"

    @staticmethod
    def _sanitize_filename_stem(raw: str) -> str:
        name = raw.strip()
        name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name)
        name = re.sub(r"\s+", "_", name)
        name = re.sub(r"_+", "_", name)
        return name.strip("._ ")

    def _default_output_stem(self) -> str:
        meta = self.project_file.project.meta
        for candidate in (meta.id, meta.title):
            safe = self._sanitize_filename_stem(candidate or "")
            if safe:
                return safe
        return "output"

    def _auto_output_filename(self) -> str:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"{self._default_output_stem()}_{ts}.pdf"

    def get_default_output_dir(self) -> Path:
        return self._build_dir()

    def get_output_dir_display(self) -> str:
        return str(self.output_dir if self.output_dir is not None else self.get_default_output_dir())

    def set_output_dir(self, value: str | Path | None) -> None:
        if value is None:
            self.output_dir = None
            return
        as_text = str(value).strip()
        if not as_text:
            self.output_dir = None
            return
        p = Path(as_text).expanduser()
        self.output_dir = p

    def set_custom_filename(self, value: str) -> None:
        self.custom_filename = value.strip()

    def set_use_auto_name(self, value: bool) -> None:
        self.use_auto_name = bool(value)

    def reset_output_settings(self) -> None:
        self.output_dir = None
        self.custom_filename = ""
        self.use_auto_name = True

    def resolve_output_paths(self) -> dict[str, Path]:
        output_dir = self.output_dir if self.output_dir is not None else self.get_default_output_dir()
        output_dir = output_dir.expanduser()
        if self.use_auto_name:
            filename = self._auto_output_filename()
        else:
            raw = Path(self.custom_filename).name if self.custom_filename else ""
            if raw.lower().endswith(".pdf"):
                raw = raw[:-4]
            stem = self._sanitize_filename_stem(raw)
            if not stem:
                stem = self._default_output_stem()
            filename = f"{stem}.pdf"

        return {"output_pdf": output_dir / filename}

    def _active_file_label(self) -> str:
        if self.path is not None:
            return str(self.path)
        return "<in-memory>"

    def _in_memory_payload(self) -> dict:
        return self.project_file.model_dump(mode="json", exclude_none=True)

    def _write_snapshot_json(self) -> Path:
        build_dir = self._build_dir()
        build_dir.mkdir(parents=True, exist_ok=True)
        snapshot = build_dir / "_ui_snapshot.json"
        snapshot.write_text(
            json.dumps(self._in_memory_payload(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return snapshot

    def _pipeline_source_file(self) -> Path:
        if self.path is not None and self.path.exists() and not self.dirty:
            return self.path
        return self._write_snapshot_json()

    def mark_dirty(self) -> None:
        ps.touch_updated_at(self.project_file)
        self.dirty = True

    def new_project(self) -> None:
        self.path = None
        self.project_file = ps.new_project_file()
        self.dirty = False
        self.last_validation = None
        self.last_build = None
        self.ai_last_result = None
        self.ai_generated_payload = None
        self.ai_generated_json_text = ""

    def open_project(self, path: str | Path) -> ValidationReport:
        report = validate_project_file(path)
        self.last_validation = report
        if report.ok:
            self.project_file = ps.load_project_file(path)
            self.path = Path(path)
            self.dirty = False
            self.ai_last_result = None
            self.ai_generated_payload = None
            self.ai_generated_json_text = ""
        return report

    def save(self) -> None:
        if self.path is None:
            raise ValueError("No current path (use Save As).")
        ps.save_project_file(self.project_file, self.path)
        self.dirty = False

    def save_as(self, path: str | Path) -> None:
        self.path = Path(path)
        ps.save_project_file(self.project_file, self.path)
        self.dirty = False

    def validate_current_file(self) -> ValidationReport:
        if self.path is not None and self.path.exists() and not self.dirty:
            report = validate_project_file(self.path)
            self.last_validation = report
            return report

        report = validate_project_data(self._in_memory_payload(), file_label=self._active_file_label())
        self.last_validation = report
        return report

    def validate_json_text(self, text: str) -> ValidationReport:
        report = validate_json_text(text, file_label="<json-import>")
        self.last_validation = report
        return report

    def import_json_text(self, text: str) -> ValidationReport:
        report = self.validate_json_text(text)
        if not report.ok:
            return report

        payload = json.loads(text)
        return self.import_project_payload(payload, file_label="<json-import>")

    def import_project_payload(self, payload: dict, *, file_label: str = "<import>") -> ValidationReport:
        report = validate_project_data(payload, file_label=file_label)
        self.last_validation = report
        if not report.ok:
            return report
        self.project_file = ps.load_project_data(payload)
        self.mark_dirty()
        return report

    def generate_ai_draft(
        self,
        raw_text: str,
        *,
        title_hint: str | None = None,
        author_hint: str | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        cancel_event: Any | None = None,
    ) -> AIGenerationResult:
        result = self.ai_service.generate_project_draft(
            raw_text,
            title_hint=title_hint,
            author_hint=author_hint,
            progress_callback=progress_callback,
            cancel_event=cancel_event,
        )
        self.ai_last_result = result
        self.ai_generated_payload = result.sanitized_payload if result.ok else None

        if result.sanitized_payload is not None:
            self.ai_generated_json_text = json.dumps(result.sanitized_payload, ensure_ascii=False, indent=2)
        elif result.parsed_draft is not None:
            self.ai_generated_json_text = json.dumps(result.parsed_draft, ensure_ascii=False, indent=2)
        else:
            self.ai_generated_json_text = result.raw_output or ""

        if result.validation_report is not None:
            self.last_validation = result.validation_report
        return result

    def import_ai_generated_project(self) -> ValidationReport:
        from src.validation.errors import ErrorItem

        if self.ai_generated_payload is None:
            report = ValidationReport(
                ok=False,
                file="<ai-import>",
                stage="ai_import",
                errors=[
                    ErrorItem(
                        code="ai.import.missing_draft",
                        severity="error",
                        path="/",
                        message="No validated AI draft available to import.",
                        hint="Generate a draft first.",
                    )
                ],
            )
            self.last_validation = report
            return report
        return self.import_project_payload(self.ai_generated_payload, file_label="<ai-import>")

    def generate_typst_only(self) -> ValidationReport:
        payload = self._in_memory_payload()
        report = validate_project_data(payload, file_label=self._active_file_label())
        self.last_validation = report
        if not report.ok:
            return report
        pf = ProjectFile.model_validate(payload)
        generate_content(project_file=pf, out_path=self.generated_typst_path())
        return report

    def build(self, mode: str) -> BuildReport:
        source_file = self._pipeline_source_file()
        output_paths = self.resolve_output_paths()
        output_pdf = output_paths["output_pdf"]
        rep = build_pdf(source_file=source_file, mode=mode, output_pdf_path=output_pdf)  # type: ignore[arg-type]
        self.last_build = rep
        self.last_output_pdf_path = output_pdf
        return rep

    def open_output_folder(self) -> Path:
        output_dir = self.output_dir if self.output_dir is not None else self._build_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(str(output_dir))  # Windows
        return output_dir

    def generated_typst_path(self) -> Path:
        return self._build_dir() / "generated_content.typ"

    def preview_pdf_path(self) -> Path:
        if self.last_build is not None and self.last_build.output_pdf:
            return Path(self.last_build.output_pdf)
        if self.last_output_pdf_path is not None:
            return self.last_output_pdf_path
        return self._build_dir() / "output.pdf"

    def build_report_path(self) -> Path:
        return self._build_dir() / "build_report.json"

    def open_generated_typst(self) -> Path:
        p = self.generated_typst_path()
        if not p.exists():
            raise FileNotFoundError(str(p))
        os.startfile(str(p))
        return p

    def open_preview_pdf(self) -> Path:
        p = self.preview_pdf_path()
        if not p.exists():
            raise FileNotFoundError(str(p))
        os.startfile(str(p))
        return p

    def open_build_report(self) -> Path:
        p = self.build_report_path()
        if not p.exists():
            raise FileNotFoundError(str(p))
        os.startfile(str(p))
        return p

    def open_last_build_report(self) -> Path:
        return self.open_build_report()
