from __future__ import annotations

from pydantic import Field

from ._base import SDREModel
from .types import Identifier


class Subject(SDREModel):
    id: Identifier
    title: str = Field(min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=4096)
    blocks: list["Block"] = Field(min_length=1)


from .blocks import Block  # noqa: E402

Subject.model_rebuild()
