import json
from pathlib import Path

import pytest

from src.validation.engine import validate_json_text, validate_project_file


def _load_sample() -> dict:
    p = Path("examples/sample_project.json")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write(tmp_path: Path, data: dict, name: str) -> Path:
    out = tmp_path / name
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def test_valid_example_project_passes():
    report = validate_project_file("examples/sample_project.json")
    assert report.ok is True
    assert report.stage == "ok"
    assert report.errors == []


def test_missing_required_field_fails_schema(tmp_path: Path):
    data = _load_sample()
    del data["project"]["meta"]["title"]
    path = _write(tmp_path, data, "missing_title.json")

    report = validate_project_file(path)
    assert report.ok is False
    assert report.stage == "schema"
    assert any(e.code == "schema.validation" for e in report.errors)


def test_invalid_block_type_fails_schema(tmp_path: Path):
    data = _load_sample()
    data["project"]["subjects"][0]["blocks"][0]["type"] = "heading"
    path = _write(tmp_path, data, "invalid_block_type.json")

    report = validate_project_file(path)
    assert report.ok is False
    assert report.stage == "schema"
    assert any(e.code == "schema.validation" for e in report.errors)


def test_duplicate_subject_ids_fails_model(tmp_path: Path):
    data = _load_sample()
    subj = data["project"]["subjects"][0]
    data["project"]["subjects"].append(subj)
    path = _write(tmp_path, data, "dup_subject_ids.json")

    report = validate_project_file(path)
    assert report.ok is False
    assert report.stage == "model"
    assert any(e.code == "model.validation" for e in report.errors)


def test_duplicate_block_ids_inside_subject_fails_model(tmp_path: Path):
    data = _load_sample()
    blocks = data["project"]["subjects"][0]["blocks"]
    blocks.append(blocks[0])
    path = _write(tmp_path, data, "dup_block_ids.json")

    report = validate_project_file(path)
    assert report.ok is False
    assert report.stage == "model"
    assert any(e.code == "model.validation" for e in report.errors)


def test_image_placeholder_missing_size_hint_fails_schema(tmp_path: Path):
    data = _load_sample()
    blocks = data["project"]["subjects"][0]["blocks"]
    blocks.append(
        {
            "id": "imgph_bad",
            "type": "image_placeholder",
            "border": True
        }
    )
    path = _write(tmp_path, data, "image_placeholder_missing_hint.json")

    report = validate_project_file(path)
    assert report.ok is False
    assert report.stage == "schema"
    assert any(e.code == "schema.validation" for e in report.errors)


def test_invalid_inline_node_structure_fails_schema(tmp_path: Path):
    data = _load_sample()
    # Break an inline: ltr without required "value"
    p = None
    for b in data["project"]["subjects"][0]["blocks"]:
        if b["type"] == "paragraph":
            p = b
            break
    assert p is not None
    p["content"].append({"type": "ltr", "style": "boxed"})

    path = _write(tmp_path, data, "bad_inline.json")
    report = validate_project_file(path)
    assert report.ok is False
    assert report.stage == "schema"
    assert any(e.code == "schema.validation" for e in report.errors)


def test_validate_json_text_reports_parse_line_column():
    report = validate_json_text('{"project": ')
    assert report.ok is False
    assert report.stage == "load_json"
    assert report.errors
    err = report.errors[0]
    assert err.code == "json.parse"
    assert err.line is not None
    assert err.column is not None
