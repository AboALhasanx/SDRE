from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["error", "warning"]


class ErrorItem(BaseModel):
    """Unified engineering error report item."""

    model_config = ConfigDict(extra="forbid", strict=True)

    code: str = Field(min_length=1, max_length=128)
    severity: Severity
    path: str = Field(
        description="JSON Pointer-like path (e.g., /project/meta/title). Root is /."
    )
    message: str = Field(min_length=1, max_length=4096)
    hint: str = Field(default="", max_length=4096)
    line: int | None = Field(default=None, ge=1)
    column: int | None = Field(default=None, ge=1)


def json_pointer_from_parts(parts: list[Any]) -> str:
    # RFC6901-ish escaping (~ -> ~0, / -> ~1)
    if not parts:
        return "/"
    out: list[str] = []
    for p in parts:
        s = str(p)
        s = s.replace("~", "~0").replace("/", "~1")
        out.append(s)
    return "/" + "/".join(out)
