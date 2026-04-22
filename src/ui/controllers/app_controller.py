from __future__ import annotations

import os
from pathlib import Path

from src.services.build_service import BuildReport, build_pdf
from src.validation.engine import ValidationReport, validate_project_file

from src.ui.state import project_state as ps


class AppController:
    """UI controller: coordinates file IO + backend services + in-memory state."""

    def __init__(self) -> None:
        self.path: Path | None = None
        self.project_file = ps.new_project_file()
        self.dirty = False
        self.last_validation: ValidationReport | None = None
        self.last_build: BuildReport | None = None

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
        if self.path is None:
            # Validate in-memory snapshot by writing to a temporary json dict
            payload = self.project_file.model_dump(mode="json")
            # The Phase 2 validator works with paths; GUI displays model-only validation here.
            try:
                ps.validate_in_memory(self.project_file)
                report = ValidationReport(ok=True, file="<in-memory>", stage="ok", errors=[])
            except Exception as e:
                from src.validation.errors import ErrorItem

                report = ValidationReport(
                    ok=False,
                    file="<in-memory>",
                    stage="model",
                    errors=[
                        ErrorItem(
                            code="model.validation",
                            severity="error",
                            path="/",
                            message=str(e),
                            hint="Fix the form fields and try again.",
                        )
                    ],
                )
            self.last_validation = report
            return report

        report = validate_project_file(self.path)
        self.last_validation = report
        return report

    def build(self, mode: str) -> BuildReport:
        # Build service consumes a path; ensure saved file exists for strict reproducibility.
        if self.path is None:
            raise ValueError("Save the project before building.")
        self.save()
        rep = build_pdf(source_file=self.path, mode=mode)  # type: ignore[arg-type]
        self.last_build = rep
        return rep

    def open_output_folder(self) -> Path:
        build_dir = Path(__file__).resolve().parents[3] / "build"
        os.startfile(str(build_dir))  # Windows
        return build_dir

