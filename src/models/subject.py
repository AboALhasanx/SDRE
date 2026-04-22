from __future__ import annotations

from pydantic import Field

from ._base import SDREModel


class Subject(SDREModel):
    name: str = Field(min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=4096)

