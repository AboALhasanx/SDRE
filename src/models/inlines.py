from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from ._base import SDREModel


class InlineText(SDREModel):
    type: Literal["text"]
    text: str


class InlineCode(SDREModel):
    type: Literal["code"]
    code: str
    lang: str | None = Field(default=None, min_length=1, max_length=32)


class InlineMath(SDREModel):
    type: Literal["math"]
    latex: str = Field(min_length=1, max_length=8192)


InlineChild = Annotated[Union[InlineText, InlineCode, InlineMath], Field(discriminator="type")]


class InlineLtr(SDREModel):
    type: Literal["ltr"]
    children: list[InlineChild] = Field(min_length=1)


InlineNode = Annotated[
    Union[InlineText, InlineCode, InlineMath, InlineLtr],
    Field(discriminator="type"),
]

