from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SDREModel(BaseModel):
    """Base model for SDRE data structures.

    Phase 1 priorities:
    - strict type enforcement
    - forbid unknown/extra fields
    """

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        validate_assignment=True,
    )

