from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from ._base import SDREModel
from .inlines import InlineNode
from .types import Identifier


class BlockBase(SDREModel):
    id: Identifier | None = None
    subject_id: Identifier | None = None


class BlockSection(BlockBase):
    type: Literal["section"]
    title: list[InlineNode] = Field(min_length=1)
    blocks: list["Block"] = Field(default_factory=list)


class BlockHeading(BlockBase):
    type: Literal["heading"]
    level: int = Field(ge=1, le=6)
    inlines: list[InlineNode] = Field(min_length=1)


class BlockParagraph(BlockBase):
    type: Literal["paragraph"]
    inlines: list[InlineNode] = Field(min_length=1)


class BlockCode(BlockBase):
    type: Literal["code"]
    code: str
    lang: str | None = Field(default=None, min_length=1, max_length=32)


class BlockMath(BlockBase):
    type: Literal["math"]
    latex: str = Field(min_length=1, max_length=65535)


class TableCell(SDREModel):
    inlines: list[InlineNode] = Field(min_length=1)


class BlockTable(BlockBase):
    type: Literal["table"]
    rows: list[list[TableCell]] = Field(min_length=1)
    caption: list[InlineNode] | None = None


class BlockImage(BlockBase):
    type: Literal["image"]
    src: str = Field(min_length=1)
    alt: str | None = Field(default=None, max_length=1024)
    caption: list[InlineNode] | None = None


class ListItem(SDREModel):
    checked: bool | None = None
    blocks: list["Block"] = Field(min_length=1)


class BlockList(BlockBase):
    type: Literal["list"]
    ordered: bool
    items: list[ListItem] = Field(min_length=1)


class BlockQuote(BlockBase):
    type: Literal["quote"]
    blocks: list["Block"] = Field(min_length=1)
    cite: str | None = Field(default=None, max_length=2048)


class BlockCallout(BlockBase):
    type: Literal["callout"]
    kind: Literal["note", "info", "success", "warning", "error"]
    blocks: list["Block"] = Field(min_length=1)
    title: list[InlineNode] | None = None


class BlockHorizontalRule(BlockBase):
    type: Literal["horizontal_rule"]


class BlockPageBreak(BlockBase):
    type: Literal["page_break"]


class BlockToc(BlockBase):
    type: Literal["toc"]
    depth: int = Field(ge=1, le=6)


class BlockFootnote(BlockBase):
    type: Literal["footnote"]
    key: Identifier
    blocks: list["Block"] = Field(min_length=1)


Block = Annotated[
    Union[
        BlockSection,
        BlockHeading,
        BlockParagraph,
        BlockCode,
        BlockMath,
        BlockTable,
        BlockImage,
        BlockList,
        BlockQuote,
        BlockCallout,
        BlockHorizontalRule,
        BlockPageBreak,
        BlockToc,
        BlockFootnote,
    ],
    Field(discriminator="type"),
]


for _m in (
    BlockSection,
    BlockHeading,
    BlockParagraph,
    BlockCode,
    BlockMath,
    BlockTable,
    BlockImage,
    BlockList,
    BlockQuote,
    BlockCallout,
    BlockHorizontalRule,
    BlockPageBreak,
    BlockToc,
    BlockFootnote,
    ListItem,
):
    _m.model_rebuild()

