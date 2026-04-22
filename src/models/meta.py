from __future__ import annotations

from pydantic import Field

from ._base import SDREModel
from .types import Direction, Identifier, LangTag


class Meta(SDREModel):
    id: Identifier
    title: str = Field(min_length=1, max_length=256)
    author: str = Field(min_length=1, max_length=256)
    lang: LangTag
    direction: Direction

