from __future__ import annotations

from typing import Iterable

from pydantic import Field, model_validator

from ._base import SDREModel
from .blocks import (
    Block,
    BlockCallout,
    BlockFootnote,
    BlockList,
    BlockQuote,
    BlockSection,
    ListItem,
)
from .meta import Meta
from .subject import Subject
from .theme import Theme
from .types import Identifier


def _iter_child_blocks(block: Block) -> Iterable[Block]:
    # Container blocks that hold other blocks.
    if isinstance(block, BlockSection):
        return block.blocks
    if isinstance(block, BlockQuote):
        return block.blocks
    if isinstance(block, BlockCallout):
        return block.blocks
    if isinstance(block, BlockFootnote):
        return block.blocks
    if isinstance(block, BlockList):
        out: list[Block] = []
        for item in block.items:
            out.extend(item.blocks)
        return out
    return ()


def _walk_blocks(blocks: list[Block]) -> Iterable[Block]:
    stack = list(blocks)
    while stack:
        b = stack.pop()
        yield b
        stack.extend(_iter_child_blocks(b))


class Project(SDREModel):
    meta: Meta
    theme: Theme
    subjects: dict[Identifier, Subject]
    blocks: list[Block] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_references(self) -> "Project":
        subject_ids = set(self.subjects.keys())

        unknown_subjects: set[str] = set()
        for b in _walk_blocks(self.blocks):
            if b.subject_id is not None and b.subject_id not in subject_ids:
                unknown_subjects.add(b.subject_id)

        if unknown_subjects:
            unknown_list = ", ".join(sorted(unknown_subjects))
            raise ValueError(f"Unknown subject_id reference(s): {unknown_list}")

        # Footnote keys should be unique across the entire document.
        footnote_keys: set[str] = set()
        dup_footnote_keys: set[str] = set()
        for b in _walk_blocks(self.blocks):
            if isinstance(b, BlockFootnote):
                if b.key in footnote_keys:
                    dup_footnote_keys.add(b.key)
                footnote_keys.add(b.key)
        if dup_footnote_keys:
            dup_list = ", ".join(sorted(dup_footnote_keys))
            raise ValueError(f"Duplicate footnote key(s): {dup_list}")

        return self

