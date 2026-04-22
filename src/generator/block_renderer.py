from __future__ import annotations

from src.generator.inline_renderer import _escape_typst_string, render_inlines
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


def _fmt_num(n: float) -> str:
    if float(n).is_integer():
        return str(int(n))
    return str(n)


def _render_inline_item(item: list) -> str:
    return f"[{render_inlines(item)}]"


def _render_table_cell(cell: TableCell) -> str:
    return f"[{render_inlines(cell.content)}]"


def render_block(block: Block) -> str:
    header = f"// block:{block.id} type:{block.type}\n"

    if isinstance(block, BlockSection):
        return header + f'#sdre_section("{_escape_typst_string(block.title)}")\n'

    if isinstance(block, BlockSubsection):
        return header + f'#sdre_subsection("{_escape_typst_string(block.title)}")\n'

    if isinstance(block, BlockParagraph):
        return header + f"#sdre_paragraph([{render_inlines(block.content)}])\n"

    if isinstance(block, BlockCodeBlock):
        lang_arg = f', lang: "{_escape_typst_string(block.lang)}"' if block.lang else ""
        return header + f'#sdre_code_block("{_escape_typst_string(block.value)}"{lang_arg})\n'

    if isinstance(block, BlockMathBlock):
        return header + f"#sdre_math_block(${block.value}$)\n"

    if isinstance(block, BlockTable):
        # Represent rows as nested arrays of content blocks.
        row_chunks: list[str] = []
        for row in block.rows:
            cells = ", ".join(_render_table_cell(c) for c in row)
            row_chunks.append(f"({cells})")
        rows = "(" + ", ".join(row_chunks) + ")"
        caption = f"[{render_inlines(block.caption)}]" if block.caption else "none"
        return header + f"#sdre_table({rows}, caption: {caption})\n"

    if isinstance(block, BlockImage):
        alt_arg = f', alt: "{_escape_typst_string(block.alt)}"' if block.alt else ""
        caption = f"[{render_inlines(block.caption)}]" if block.caption else "none"
        return (
            header
            + f'#sdre_image("{_escape_typst_string(block.src)}"{alt_arg}, caption: {caption})\n'
        )

    if isinstance(block, BlockImagePlaceholder):
        caption = f"[{render_inlines(block.caption)}]" if block.caption else "none"
        label_arg = f', label: "{_escape_typst_string(block.label)}"' if block.label else ""
        border_arg = f", border: {str(block.border).lower()}" if block.border is not None else ""
        height_arg = (
            f", reserve_height: {_fmt_num(block.reserve_height_mm)}mm"
            if block.reserve_height_mm is not None
            else ""
        )
        aspect_arg = (
            f", aspect_ratio: {_fmt_num(block.aspect_ratio)}"
            if block.aspect_ratio is not None
            else ""
        )
        return (
            header
            + f"#sdre_image_placeholder({height_arg}{aspect_arg}{border_arg}{label_arg}, caption: {caption})\n"
        )

    if isinstance(block, BlockNote):
        return header + f"#sdre_note([{render_inlines(block.content)}])\n"

    if isinstance(block, BlockWarning):
        return header + f"#sdre_warning([{render_inlines(block.content)}])\n"

    if isinstance(block, BlockBulletList):
        items = "(" + ", ".join(_render_inline_item(i) for i in block.items) + ")"
        return header + f"#sdre_bullet_list({items})\n"

    if isinstance(block, BlockNumberedList):
        items = "(" + ", ".join(_render_inline_item(i) for i in block.items) + ")"
        return header + f"#sdre_numbered_list({items})\n"

    if isinstance(block, BlockPageBreak):
        return header + "#sdre_page_break()\n"

    if isinstance(block, BlockHorizontalRule):
        return header + "#sdre_horizontal_rule()\n"

    raise TypeError(f"Unsupported block: {type(block).__name__}")


def render_blocks(blocks: list[Block]) -> str:
    return "".join(render_block(b) + "\n" for b in blocks)
