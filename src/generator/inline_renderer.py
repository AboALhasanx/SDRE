from __future__ import annotations

from src.models.inlines import InlineCode, InlineLtr, InlineMath, InlineNode, InlineText


def _escape_typst_text(s: str) -> str:
    # Escapes for Typst markup contexts inside `[...]`.
    # Keep this conservative; we only need to avoid breaking markup/code entry points.
    return (
        s.replace("\\", "\\\\")
        .replace("#", "\\#")
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("$", "\\$")
    )


def _escape_typst_string(s: str) -> str:
    # Escapes for Typst string literals "..."
    return s.replace("\\", "\\\\").replace('"', '\\"')


def render_inline(node: InlineNode) -> str:
    if isinstance(node, InlineText):
        return _escape_typst_text(node.value)

    if isinstance(node, InlineLtr):
        style = node.style or "plain"
        return f'#sdre_ltr("{_escape_typst_string(node.value)}", theme: theme, style: "{style}")'

    if isinstance(node, InlineCode):
        lang_arg = f', lang: "{_escape_typst_string(node.lang)}"' if node.lang else ""
        return f'#sdre_inline_code("{_escape_typst_string(node.value)}"{lang_arg})'

    if isinstance(node, InlineMath):
        # Typst-native math expression.
        # We intentionally do not treat this as a string.
        return f"#sdre_inline_math(${node.value}$)"

    raise TypeError(f"Unsupported inline node: {type(node).__name__}")


def render_inlines(nodes: list[InlineNode]) -> str:
    return "".join(render_inline(n) for n in nodes)
