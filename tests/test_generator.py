import json
from pathlib import Path

from src.generator.block_renderer import render_block
from src.generator.inline_renderer import render_inline, render_inlines
from src.generator.project_renderer import render_project_file
from src.models.blocks import (
    BlockCodeBlock,
    BlockImagePlaceholder,
    BlockMathBlock,
    BlockParagraph,
    BlockSection,
    BlockTable,
    TableCell,
)
from src.models.inlines import InlineCode, InlineLtr, InlineMath, InlineText
from src.models.project import ProjectFile


def test_inline_rendering_text_ltr_math_code():
    nodes = [
        InlineText(type="text", value="Hello "),
        InlineLtr(type="ltr", value="Binary Search", style="boxed"),
        InlineText(type="text", value=" in "),
        InlineMath(type="inline_math", value="O(log n)"),
        InlineText(type="text", value=" and "),
        InlineCode(type="inline_code", value="x += 1", lang="python"),
    ]
    out = render_inlines(nodes)
    assert "Hello" in out
    assert '#sdre_ltr("Binary Search", theme: theme, style: "boxed")' in out
    assert "#sdre_inline_math($O(log n)$)" in out
    assert '#sdre_inline_code("x += 1", lang: "python")' in out


def test_paragraph_rendering():
    b = BlockParagraph(
        id="p1",
        type="paragraph",
        content=[InlineText(type="text", value="Para")],
    )
    out = render_block(b)
    assert "#sdre_paragraph([" in out
    assert "Para" in out


def test_code_block_rendering():
    b = BlockCodeBlock(id="c1", type="code_block", value="print(1)", lang="python")
    out = render_block(b)
    assert "#sdre_code_block(" in out
    assert 'lang: "python"' in out


def test_math_block_rendering():
    b = BlockMathBlock(id="m1", type="math_block", value="a + b")
    out = render_block(b)
    assert "#sdre_math_block($a + b$)" in out


def test_table_rendering():
    b = BlockTable(
        id="t1",
        type="table",
        caption=[InlineText(type="text", value="Cap")],
        rows=[
            [
                TableCell(content=[InlineText(type="text", value="A")]),
                TableCell(content=[InlineMath(type="inline_math", value="x")]),
            ]
        ],
    )
    out = render_block(b)
    assert "#sdre_table(" in out
    assert "caption:" in out
    assert "Cap" in out


def test_image_placeholder_rendering():
    b = BlockImagePlaceholder(
        id="ph1",
        type="image_placeholder",
        reserve_height_mm=40,
        border=True,
        label="Figure 1",
        caption=[InlineText(type="text", value="Later")],
    )
    out = render_block(b)
    assert "#sdre_image_placeholder(" in out
    assert "reserve_height: 40mm" in out
    assert 'label: "Figure 1"' in out


def test_full_project_generation_from_sample():
    data = json.loads(Path("examples/sample_project.json").read_text(encoding="utf-8"))
    pf = ProjectFile.model_validate(data)
    typ = render_project_file(pf)
    assert "#sdre_document(" in typ
    assert "#sdre_section(" in typ
    assert "#sdre_code_block(" in typ
    assert "#sdre_table(" in typ
    assert "#sdre_image_placeholder(" in typ


def test_macros_interpolate_runtime_values():
    macros = Path("templates/macros.typ").read_text(encoding="utf-8")
    assert "heading(level: 1)[#title]" in macros
    assert "heading(level: 2)[#title]" in macros
    assert "text(dir: ltr)[#value]" in macros
    assert "#if label != none" in macros
