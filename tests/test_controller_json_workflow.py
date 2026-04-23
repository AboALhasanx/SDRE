import json
from pathlib import Path

import pytest

from src.ai.ai_service import AIGenerationResult
from src.services.build_service import BuildReport
from src.ui.controllers.app_controller import AppController


def test_import_json_text_success_marks_dirty():
    c = AppController()
    raw = Path("examples/sample_project.json").read_text(encoding="utf-8")
    rep = c.import_json_text(raw)
    assert rep.ok is True
    assert c.dirty is True
    assert c.project_file.project.meta.id == "sdre_full_test"


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

    def _fake_build_pdf(*, source_file, mode, output_pdf_path=None, output_report_path=None, output_generated_path=None):
        captured["source_file"] = str(source_file)
        captured["output_pdf_path"] = str(output_pdf_path) if output_pdf_path is not None else ""
        return BuildReport(
            ok=True,
            mode=mode,
            source_file=str(source_file),
            generated_typst_file=str(tmp_path / "generated_content.typ"),
            template_file="templates/main.typ",
            output_pdf=str(output_pdf_path or (tmp_path / "output.pdf")),
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
    assert Path(captured["output_pdf_path"]).parent == tmp_path
    data = json.loads(Path(captured["source_file"]).read_text(encoding="utf-8"))
    assert "project" in data


def test_output_path_resolution_auto_and_custom(tmp_path: Path):
    c = AppController()
    c.project_file.project.meta.id = "my_project"
    c.set_output_dir(tmp_path)

    c.set_use_auto_name(True)
    auto = c.resolve_output_paths()["output_pdf"]
    assert auto.parent == tmp_path
    assert auto.suffix.lower() == ".pdf"
    assert auto.name.startswith("my_project_")

    c.set_use_auto_name(False)
    c.set_custom_filename("custom_report")
    custom = c.resolve_output_paths()["output_pdf"]
    assert custom == tmp_path / "custom_report.pdf"

    c.set_custom_filename("already.pdf")
    custom_with_ext = c.resolve_output_paths()["output_pdf"]
    assert custom_with_ext == tmp_path / "already.pdf"


def test_reset_output_settings_restores_defaults(tmp_path: Path):
    c = AppController()
    c.set_output_dir(tmp_path)
    c.set_custom_filename("manual")
    c.set_use_auto_name(False)

    c.reset_output_settings()
    assert c.output_dir is None
    assert c.custom_filename == ""
    assert c.use_auto_name is True


def test_ai_generate_and_import_pipeline(monkeypatch: pytest.MonkeyPatch):
    c = AppController()
    payload = {
        "project": {
            "meta": {
                "id": "ai_project",
                "title": "AI Project",
                "author": "AI",
                "language": "ar",
                "direction": "rtl",
                "version": "1.0.0",
                "created_at": "2026-04-23T00:00:00Z",
                "updated_at": "2026-04-23T00:00:00Z",
            },
            "theme": c.project_file.project.theme.model_dump(mode="json", exclude_none=True),
            "subjects": [
                {
                    "id": "subject_1",
                    "title": "S1",
                    "blocks": [{"id": "paragraph_1", "type": "paragraph", "content": [{"type": "text", "value": "x"}]}],
                }
            ],
        }
    }

    def _fake_generate(*args, **kwargs):
        return AIGenerationResult(
            ok=True,
            stage="ok",
            message="ok",
            raw_output="{}",
            parsed_draft={"project": {}},
            sanitized_payload=payload,
            validation_report=None,
        )

    monkeypatch.setattr(c.ai_service, "generate_project_draft", _fake_generate)
    res = c.generate_ai_draft("source")
    assert res.ok is True
    assert c.ai_generated_payload == payload

    rep = c.import_ai_generated_project()
    assert rep.ok is True
    assert c.project_file.project.meta.id == "ai_project"
