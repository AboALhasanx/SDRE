from __future__ import annotations

import json
import os
from pathlib import Path

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

    @staticmethod
    def _repo_root() -> Path:
        return Path(__file__).resolve().parents[3]

    def _build_dir(self) -> Path:
        return self._repo_root() / "build"

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

    def open_project(self, path: str | Path) -> ValidationReport:
        report = validate_project_file(path)
        self.last_validation = report
        if report.ok:
            self.project_file = ps.load_project_file(path)
            self.path = Path(path)
            self.dirty = False
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
        self.project_file = ProjectFile.model_validate(payload)
        self.mark_dirty()
        return report

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
        rep = build_pdf(source_file=source_file, mode=mode)  # type: ignore[arg-type]
        self.last_build = rep
        return rep

    def open_output_folder(self) -> Path:
        build_dir = self._build_dir()
        os.startfile(str(build_dir))  # Windows
        return build_dir

    def generated_typst_path(self) -> Path:
        return self._build_dir() / "generated_content.typ"

    def preview_pdf_path(self) -> Path:
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
