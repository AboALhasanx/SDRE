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
        return (
            None,
            [
                ErrorItem(
                    code="json.parse",
                    severity="error",
                    path="/",
                    message=f"Invalid JSON: {e.msg} (line {e.lineno}, col {e.colno})",
                    hint="Fix JSON syntax (commas, quotes, braces).",
                )
            ],
        )


def validate_project_file(
    json_path: str | Path, schema_path: str | Path | None = None
) -> ValidationReport:
    json_path = Path(json_path)
    schema_path = Path(schema_path) if schema_path is not None else default_schema_path()

    data, load_errors = load_json(json_path)
    if load_errors:
        return ValidationReport(ok=False, file=str(json_path), stage="load_json", errors=load_errors)

    schema = load_schema(schema_path)
    schema_errors = validate_schema(schema)
    if schema_errors:
        return ValidationReport(ok=False, file=str(json_path), stage="schema", errors=schema_errors)

    instance_errors = validate_instance(schema, data)
    if instance_errors:
        return ValidationReport(ok=False, file=str(json_path), stage="schema", errors=instance_errors)

    model_errors = validate_model(data)
    if model_errors:
        return ValidationReport(ok=False, file=str(json_path), stage="model", errors=model_errors)

    return ValidationReport(ok=True, file=str(json_path), stage="ok", errors=[])

