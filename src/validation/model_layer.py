from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from src.models.project import ProjectFile

from .errors import ErrorItem, json_pointer_from_parts


def validate_model(instance: Any) -> list[ErrorItem]:
    try:
        ProjectFile.model_validate(instance)
        return []
    except ValidationError as e:
        out: list[ErrorItem] = []
        for item in e.errors():
            loc = item.get("loc", ())
            parts = list(loc) if isinstance(loc, tuple) else [loc]
            path = json_pointer_from_parts(parts)
            typ = item.get("type", "validation_error")
            msg = item.get("msg", "Validation error")
            out.append(
                ErrorItem(
                    code="model.validation",
                    severity="error",
                    path=path,
                    message=str(msg),
                    hint=f"Pydantic error type: {typ}",
                )
            )
        return out

