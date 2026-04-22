from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from ._base import SDREModel


class InlineText(SDREModel):
    type: Literal["text"]
    value: str


class InlineCode(SDREModel):
    type: Literal["inline_code"]
    value: str
    lang: str | None = Field(default=None, min_length=1, max_length=32)


class InlineMath(SDREModel):
    type: Literal["inline_math"]
    value: str = Field(min_length=1, max_length=8192)


InlineChild = Annotated[Union[InlineText, InlineCode, InlineMath], Field(discriminator="type")]


class InlineLtr(SDREModel):
    type: Literal["ltr"]
    value: str = Field(min_length=1, max_length=256)
    style: Literal["plain", "boxed", "mono"] | None = None


InlineNode = Annotated[
    Union[InlineText, InlineCode, InlineMath, InlineLtr],
    Field(discriminator="type"),
]
