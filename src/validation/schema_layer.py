from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

from .errors import ErrorItem, json_pointer_from_parts


def load_schema(schema_path: Path) -> dict[str, Any]:
    with schema_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_schema(schema: dict[str, Any]) -> list[ErrorItem]:
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as e:
        return [
            ErrorItem(
                code="schema.invalid",
                severity="error",
                path="/",
                message=str(e),
                hint="Fix schema/project.schema.json (Draft 2020-12).",
            )
        ]
    return []


def validate_instance(schema: dict[str, Any], instance: Any) -> list[ErrorItem]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    out: list[ErrorItem] = []
    for err in errors:
        path = json_pointer_from_parts(list(err.absolute_path))
        schema_path = json_pointer_from_parts(list(err.absolute_schema_path))
        out.append(
            ErrorItem(
                code="schema.validation",
                severity="error",
                path=path,
                message=err.message,
                hint=f"Schema path: {schema_path}",
            )
        )
    return out

