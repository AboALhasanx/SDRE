from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field
from pydantic import model_validator

from ._base import SDREModel
from .inlines import InlineNode
from .types import Identifier


class BlockBase(SDREModel):
    id: Identifier


class BlockSection(BlockBase):
    type: Literal["section"]
    title: str = Field(min_length=1, max_length=256)


class BlockSubsection(BlockBase):
    type: Literal["subsection"]
    title: str = Field(min_length=1, max_length=256)


class BlockParagraph(BlockBase):
    type: Literal["paragraph"]
    content: list[InlineNode] = Field(min_length=1)


class BlockCodeBlock(BlockBase):
    type: Literal["code_block"]
    value: str
    lang: str | None = Field(default=None, min_length=1, max_length=32)


class BlockMathBlock(BlockBase):
    type: Literal["math_block"]
    value: str = Field(min_length=1, max_length=65535)


class TableCell(SDREModel):
    content: list[InlineNode] = Field(min_length=1)


class BlockTable(BlockBase):
    type: Literal["table"]
    rows: list[list[TableCell]] = Field(min_length=1)
    caption: list[InlineNode] | None = None


class BlockImage(BlockBase):
    type: Literal["image"]
    src: str = Field(min_length=1)
    alt: str | None = Field(default=None, max_length=1024)
    caption: list[InlineNode] | None = None


class BlockImagePlaceholder(BlockBase):
    type: Literal["image_placeholder"]
    caption: list[InlineNode] | None = None
    reserve_height_mm: float | None = Field(default=None, gt=0, le=1000)
    aspect_ratio: float | None = Field(default=None, gt=0, le=100)
    border: bool | None = None
    label: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def _require_size_hint(self) -> "BlockImagePlaceholder":
        if self.reserve_height_mm is None and self.aspect_ratio is None:
            raise ValueError("image_placeholder requires reserve_height_mm or aspect_ratio")
        return self


class BlockNote(BlockBase):
    type: Literal["note"]
    content: list[InlineNode] = Field(min_length=1)


class BlockWarning(BlockBase):
    type: Literal["warning"]
    content: list[InlineNode] = Field(min_length=1)


class BlockBulletList(BlockBase):
    type: Literal["bullet_list"]
    items: list[list[InlineNode]] = Field(min_length=1)


class BlockNumberedList(BlockBase):
    type: Literal["numbered_list"]
    items: list[list[InlineNode]] = Field(min_length=1)


class BlockPageBreak(BlockBase):
    type: Literal["page_break"]


class BlockHorizontalRule(BlockBase):
    type: Literal["horizontal_rule"]


Block = Annotated[
    Union[
        BlockSection,
        BlockSubsection,
        BlockParagraph,
        BlockCodeBlock,
        BlockMathBlock,
        BlockTable,
        BlockImage,
        BlockImagePlaceholder,
        BlockNote,
        BlockWarning,
        BlockBulletList,
        BlockNumberedList,
        BlockPageBreak,
        BlockHorizontalRule,
    ],
    Field(discriminator="type"),
]


for _m in (
    BlockSection,
    BlockSubsection,
    BlockParagraph,
    BlockCodeBlock,
    BlockMathBlock,
    BlockTable,
    BlockImage,
    BlockImagePlaceholder,
    BlockNote,
    BlockWarning,
    BlockBulletList,
    BlockNumberedList,
    BlockPageBreak,
    BlockHorizontalRule,
):
    _m.model_rebuild()
