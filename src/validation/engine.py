from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import ErrorItem
from .model_layer import validate_model
from .report import ValidationReport
from .schema_layer import load_schema, validate_instance, validate_schema


def default_schema_path() -> Path:
    # src/validation/engine.py -> src/validation -> src -> repo root
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "schema" / "project.schema.json"


def _json_parse_error_item(e: json.JSONDecodeError) -> ErrorItem:
    return ErrorItem(
        code="json.parse",
        severity="error",
        path="/",
        message=f"Invalid JSON: {e.msg} (line {e.lineno}, col {e.colno})",
        hint="Fix JSON syntax (commas, quotes, braces).",
        line=e.lineno,
        column=e.colno,
    )


def load_json(path: Path) -> tuple[Any | None, list[ErrorItem]]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f), []
    except FileNotFoundError:
        return (
            None,
            [
                ErrorItem(
                    code="json.not_found",
                    severity="error",
                    path="/",
                    message=f"File not found: {path}",
                    hint="Check the path and try again.",
                )
            ],
        )
    except json.JSONDecodeError as e:
        return (None, [_json_parse_error_item(e)])


def load_json_text(text: str) -> tuple[Any | None, list[ErrorItem]]:
    try:
        return json.loads(text), []
    except json.JSONDecodeError as e:
        return (None, [_json_parse_error_item(e)])


def validate_project_data(
    data: Any,
    *,
    file_label: str = "<in-memory>",
    schema_path: str | Path | None = None,
) -> ValidationReport:
    schema_path = Path(schema_path) if schema_path is not None else default_schema_path()
    schema = load_schema(schema_path)
    schema_errors = validate_schema(schema)
    if schema_errors:
        return ValidationReport(ok=False, file=file_label, stage="schema", errors=schema_errors)

    instance_errors = validate_instance(schema, data)
    if instance_errors:
        return ValidationReport(ok=False, file=file_label, stage="schema", errors=instance_errors)

    model_errors = validate_model(data)
    if model_errors:
        return ValidationReport(ok=False, file=file_label, stage="model", errors=model_errors)

    return ValidationReport(ok=True, file=file_label, stage="ok", errors=[])


def validate_json_text(
    text: str,
    *,
    file_label: str = "<json-text>",
    schema_path: str | Path | None = None,
) -> ValidationReport:
    data, load_errors = load_json_text(text)
    if load_errors:
        return ValidationReport(ok=False, file=file_label, stage="load_json", errors=load_errors)
    return validate_project_data(data, file_label=file_label, schema_path=schema_path)


def validate_project_file(
    json_path: str | Path, schema_path: str | Path | None = None
) -> ValidationReport:
    json_path = Path(json_path)

    data, load_errors = load_json(json_path)
    if load_errors:
        return ValidationReport(ok=False, file=str(json_path), stage="load_json", errors=load_errors)
    return validate_project_data(data, file_label=str(json_path), schema_path=schema_path)
