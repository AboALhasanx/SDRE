from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from src.models.blocks import (
    Block,
    BlockBulletList,
    BlockCodeBlock,
    BlockHorizontalRule,
    BlockImage,
    BlockImagePlaceholder,
    BlockMathBlock,
    BlockNote,
    BlockNumberedList,
    BlockPageBreak,
    BlockParagraph,
    BlockSection,
    BlockSubsection,
    BlockTable,
    BlockWarning,
    TableCell,
)
from src.models.inlines import InlineCode, InlineLtr, InlineMath, InlineNode, InlineText
from src.models.meta import Meta
from src.models.project import Project, ProjectFile
from src.models.subject import Subject
from src.models.theme import (
    Theme,
    ThemeColors,
    ThemeFonts,
    ThemePage,
    ThemePageMarginsMm,
    ThemeText,
)
from src.models.types import Identifier


def _now_rfc3339() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_project_file() -> ProjectFile:
    # Create a minimal valid project (schema-safe).
    meta = Meta(
        id="sdre_project",
        title="New SDRE Project",
        subtitle=None,
        author="Unknown",
        language="en",
        direction="ltr",
        version="0.1",
        created_at=_now_rfc3339(),
        updated_at=_now_rfc3339(),
    )
    theme = Theme(
        page=ThemePage(
            size="A4",
            dpi=300,
            margin_mm=ThemePageMarginsMm(top=15, right=15, bottom=15, left=15),
        ),
        fonts=ThemeFonts(base="Arial", mono="Consolas", math=None),
        colors=ThemeColors(
            text="#111111",
            background="#FFFFFF",
            muted="#666666",
            accent="#0B5FFF",
            border="#DDDDDD",
            code_bg="#F6F8FA",
        ),
        text=ThemeText(base_size_px=14, line_height=1.6),
        headings=None,
        code=None,
        tables=None,
        ltr_inline_style=None,
    )

    blocks: list[Block] = [
        BlockSection(id="sec_1", type="section", title="Section 1"),
        BlockParagraph(
            id="p_1",
            type="paragraph",
            content=[InlineText(type="text", value="")],
        ),
    ]
    subject = Subject(id="subject_1", title="Subject 1", description=None, blocks=blocks)
    return ProjectFile(project=Project(meta=meta, theme=theme, subjects=[subject]))


def load_project_file(path: str | Path) -> ProjectFile:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    return ProjectFile.model_validate(data)


def save_project_file(pf: ProjectFile, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = pf.model_dump(mode="json")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def clone_project_file(pf: ProjectFile) -> ProjectFile:
    return ProjectFile.model_validate(deepcopy(pf.model_dump(mode="json")))


def _existing_ids(items: list, attr: str) -> set[str]:
    return {getattr(x, attr) for x in items}


def _new_id(prefix: str, existing: set[str]) -> Identifier:
    i = 1
    while True:
        cand = f"{prefix}_{i}"
        if cand not in existing:
            return cand  # type: ignore[return-value]
        i += 1


def add_subject(pf: ProjectFile, title: str = "New Subject") -> Identifier:
    project = pf.project
    sid = _new_id("subject", _existing_ids(project.subjects, "id"))
    subject = Subject(
        id=sid,
        title=title,
        description=None,
        blocks=[
            BlockSection(id="sec_1", type="section", title="Section 1"),
            BlockParagraph(id="p_1", type="paragraph", content=[InlineText(type="text", value="")]),
        ],
    )
    project.subjects.append(subject)
    return sid


def delete_subject(pf: ProjectFile, subject_id: str) -> None:
    project = pf.project
    project.subjects = [s for s in project.subjects if s.id != subject_id]


def move_subject(pf: ProjectFile, subject_id: str, direction: Literal["up", "down"]) -> None:
    subs = pf.project.subjects
    idx = next((i for i, s in enumerate(subs) if s.id == subject_id), None)
    if idx is None:
        return
    if direction == "up" and idx > 0:
        subs[idx - 1], subs[idx] = subs[idx], subs[idx - 1]
    if direction == "down" and idx < len(subs) - 1:
        subs[idx + 1], subs[idx] = subs[idx], subs[idx + 1]


def update_subject_meta(pf: ProjectFile, subject_id: str, *, title: str, description: str | None) -> None:
    s = get_subject(pf, subject_id)
    s.title = title
    s.description = description


def get_subject(pf: ProjectFile, subject_id: str) -> Subject:
    for s in pf.project.subjects:
        if s.id == subject_id:
            return s
    raise KeyError(f"Subject not found: {subject_id}")


def get_block(pf: ProjectFile, subject_id: str, block_id: str) -> Block:
    s = get_subject(pf, subject_id)
    for b in s.blocks:
        if b.id == block_id:
            return b
    raise KeyError(f"Block not found: {block_id}")


def delete_block(pf: ProjectFile, subject_id: str, block_id: str) -> None:
    s = get_subject(pf, subject_id)
    s.blocks = [b for b in s.blocks if b.id != block_id]


def move_block(pf: ProjectFile, subject_id: str, block_id: str, direction: Literal["up", "down"]) -> None:
    s = get_subject(pf, subject_id)
    blocks = s.blocks
    idx = next((i for i, b in enumerate(blocks) if b.id == block_id), None)
    if idx is None:
        return
    if direction == "up" and idx > 0:
        blocks[idx - 1], blocks[idx] = blocks[idx], blocks[idx - 1]
    if direction == "down" and idx < len(blocks) - 1:
        blocks[idx + 1], blocks[idx] = blocks[idx], blocks[idx + 1]


BlockType = Literal[
    "section",
    "subsection",
    "paragraph",
    "code_block",
    "math_block",
    "table",
    "image",
    "image_placeholder",
    "note",
    "warning",
    "bullet_list",
    "numbered_list",
    "page_break",
    "horizontal_rule",
]


def add_block(pf: ProjectFile, subject_id: str, block_type: BlockType) -> Identifier:
    s = get_subject(pf, subject_id)
    bid = _new_id(block_type, _existing_ids(s.blocks, "id"))

    b: Block
    if block_type == "section":
        b = BlockSection(id=bid, type="section", title="New Section")
    elif block_type == "subsection":
        b = BlockSubsection(id=bid, type="subsection", title="New Subsection")
    elif block_type == "paragraph":
        b = BlockParagraph(id=bid, type="paragraph", content=[InlineText(type="text", value="")])
    elif block_type == "code_block":
        b = BlockCodeBlock(id=bid, type="code_block", lang="python", value="")
    elif block_type == "math_block":
        b = BlockMathBlock(id=bid, type="math_block", value="x")
    elif block_type == "table":
        b = BlockTable(
            id=bid,
            type="table",
            caption=None,
            rows=[[TableCell(content=[InlineText(type="text", value="")])]],
        )
    elif block_type == "image":
        b = BlockImage(id=bid, type="image", src="", alt=None, caption=None)
    elif block_type == "image_placeholder":
        b = BlockImagePlaceholder(
            id=bid,
            type="image_placeholder",
            caption=None,
            reserve_height_mm=40,
            aspect_ratio=None,
            border=True,
            label=None,
        )
    elif block_type == "note":
        b = BlockNote(id=bid, type="note", content=[InlineText(type="text", value="")])
    elif block_type == "warning":
        b = BlockWarning(id=bid, type="warning", content=[InlineText(type="text", value="")])
    elif block_type == "bullet_list":
        b = BlockBulletList(id=bid, type="bullet_list", items=[[InlineText(type="text", value="")]])
    elif block_type == "numbered_list":
        b = BlockNumberedList(id=bid, type="numbered_list", items=[[InlineText(type="text", value="")]])
    elif block_type == "page_break":
        b = BlockPageBreak(id=bid, type="page_break")
    elif block_type == "horizontal_rule":
        b = BlockHorizontalRule(id=bid, type="horizontal_rule")
    else:
        raise ValueError(f"Unsupported block type: {block_type}")

    s.blocks.append(b)
    return bid


def touch_updated_at(pf: ProjectFile) -> None:
    # Update meta.updated_at in-place (string rfc3339).
    pf.project.meta.updated_at = _now_rfc3339()


def validate_in_memory(pf: ProjectFile) -> None:
    # Optional convenience: ensure the current in-memory state still validates as a model.
    # (Schema validation is handled by backend services on demand.)
    ProjectFile.model_validate(pf.model_dump(mode="json"))
