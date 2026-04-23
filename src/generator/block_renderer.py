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


def _normalize_code_value(value: str) -> str:
    # Keep real line breaks as-is; if the payload is a single escaped line,
    # normalize common escaped newline sequences into actual newlines.
    if "\n" in value or "\r" in value:
        return value.replace("\r\n", "\n").replace("\r", "\n")
    if "\\r\\n" in value:
        value = value.replace("\\r\\n", "\n")
    if "\\n" in value:
        value = value.replace("\\n", "\n")
    return value


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
        code_value = _normalize_code_value(block.value)
        lang_arg = f', lang: "{_escape_typst_string(block.lang)}"' if block.lang else ""
        return header + f'#sdre_code_block("{_escape_typst_string(code_value)}"{lang_arg})\n'

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
        args: list[str] = []
        if block.reserve_height_mm is not None:
            args.append(f"reserve_height: {_fmt_num(block.reserve_height_mm)}mm")
        if block.aspect_ratio is not None:
            args.append(f"aspect_ratio: {_fmt_num(block.aspect_ratio)}")
        if block.border is not None:
            args.append(f"border: {str(block.border).lower()}")
        if block.label:
            args.append(f'label: "{_escape_typst_string(block.label)}"')
        args.append(f"caption: {caption}")
        return header + f"#sdre_image_placeholder(theme: theme, {', '.join(args)})\n"

    if isinstance(block, BlockNote):
        return header + f"#sdre_note([{render_inlines(block.content)}], theme: theme)\n"

    if isinstance(block, BlockWarning):
        return header + f"#sdre_warning([{render_inlines(block.content)}], theme: theme)\n"

    if isinstance(block, BlockBulletList):
        items = "(" + ", ".join(_render_inline_item(i) for i in block.items) + ")"
        return header + f"#sdre_bullet_list({items})\n"

    if isinstance(block, BlockNumberedList):
        items = "(" + ", ".join(_render_inline_item(i) for i in block.items) + ")"
        return header + f"#sdre_numbered_list({items})\n"

    if isinstance(block, BlockPageBreak):
        return header + "#sdre_page_break()\n"

    if isinstance(block, BlockHorizontalRule):
        return header + "#sdre_horizontal_rule(theme: theme)\n"

    raise TypeError(f"Unsupported block: {type(block).__name__}")


def render_blocks(blocks: list[Block]) -> str:
    return "".join(render_block(b) + "\n" for b in blocks)
