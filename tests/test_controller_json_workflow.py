import json
from pathlib import Path

import pytest

from src.services.build_service import BuildReport
from src.ui.controllers.app_controller import AppController


def test_import_json_text_success_marks_dirty():
    c = AppController()
    raw = Path("examples/sample_project.json").read_text(encoding="utf-8")
    rep = c.import_json_text(raw)
    assert rep.ok is True
    assert c.dirty is True
    assert c.project_file.project.meta.id == "sdre_demo"


def test_import_json_text_failure_does_not_modify_state():
    c = AppController()
    rep = c.import_json_text("{")
    assert rep.ok is False
    assert rep.stage == "load_json"
    assert c.dirty is False
    assert rep.errors[0].line is not None
    assert rep.errors[0].column is not None


def test_generate_typst_only_writes_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    c = AppController()
    out = tmp_path / "generated_content.typ"
    monkeypatch.setattr(c, "generated_typst_path", lambda: out)

    rep = c.generate_typst_only()
    assert rep.ok is True
    assert out.exists()
    assert "#sdre_document(" in out.read_text(encoding="utf-8")


def test_build_uses_snapshot_source_when_unsaved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    c = AppController()
    c.mark_dirty()
    monkeypatch.setattr(c, "_build_dir", lambda: tmp_path)

    captured: dict[str, str] = {}

    def _fake_build_pdf(*, source_file, mode):
        captured["source_file"] = str(source_file)
        return BuildReport(
            ok=True,
            mode=mode,
            source_file=str(source_file),
            generated_typst_file=str(tmp_path / "generated_content.typ"),
            template_file="templates/main.typ",
            output_pdf=str(tmp_path / "output.pdf"),
            stage="ok",
            stdout="",
            stderr="",
            errors=[],
            timings_ms={},
        )

    monkeypatch.setattr("src.ui.controllers.app_controller.build_pdf", _fake_build_pdf)
    rep = c.build("preview")
    assert rep.ok is True
    assert Path(captured["source_file"]).name == "_ui_snapshot.json"
    assert Path(captured["source_file"]).exists()
    data = json.loads(Path(captured["source_file"]).read_text(encoding="utf-8"))
    assert "project" in data
