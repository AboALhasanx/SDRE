from __future__ import annotations

from pydantic import Field

from ._base import SDREModel
from .types import DateTimeStr, Direction, Identifier, LangTag


class Meta(SDREModel):
    id: Identifier
    title: str = Field(min_length=1, max_length=256)
    subtitle: str | None = Field(default=None, min_length=1, max_length=256)
    author: str = Field(min_length=1, max_length=256)
    language: LangTag
    direction: Direction
    version: str | None = Field(default=None, min_length=1, max_length=64)
    created_at: DateTimeStr | None = None
    updated_at: DateTimeStr | None = None
