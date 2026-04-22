from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .errors import ErrorItem


class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    ok: bool
    file: str
    stage: str = Field(
        description="Where validation stopped: load_json, schema, model, or ok."
    )
    errors: list[ErrorItem] = Field(default_factory=list)

