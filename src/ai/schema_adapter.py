from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from .defaults import DEFAULT_THEME, default_meta_skeleton, generate_safe_id, make_safe_identifier, now_rfc3339

SUPPORTED_BLOCK_TYPES = {
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
}
SUPPORTED_INLINE_TYPES = {"text", "ltr", "inline_math", "inline_code"}
TEXT_CONTENT_BLOCK_TYPES = {"paragraph", "note", "warning"}


def sanitize_project_draft(
    draft: Any,
    *,
    title_hint: str | None = None,
    author_hint: str | None = None,
) -> dict:
    recovered = _recover_project_shape(draft)
    cleaned = _clean_project(recovered)
    injected = _inject_defaults(cleaned, title_hint=title_hint, author_hint=author_hint)
    return {"project": injected}


def _recover_project_shape(draft: Any) -> dict:
    root = deepcopy(draft) if isinstance(draft, dict) else {}
    project = root.get("project", root)
    if not isinstance(project, dict):
        project = {}

    if "subjects" not in project and isinstance(project.get("blocks"), list):
        project["subjects"] = [{"title": "Subject 1", "blocks": project.get("blocks", [])}]

    if not isinstance(project.get("subjects"), list) or not project.get("subjects"):
        project["subjects"] = [{"title": "Subject 1", "blocks": [_placeholder_paragraph_block()]}]

    for subject in project["subjects"]:
        if not isinstance(subject, dict):
            continue
        blocks = subject.get("blocks")
        if not isinstance(blocks, list) or len(blocks) == 0:
            subject["blocks"] = [_placeholder_paragraph_block()]

    return project


def _clean_project(project: dict) -> dict:
    out: dict[str, Any] = {}
    if isinstance(project.get("meta"), dict):
        out["meta"] = deepcopy(project["meta"])
    if isinstance(project.get("theme"), dict):
        out["theme"] = deepcopy(project["theme"])

    subjects_in = project.get("subjects")
    subjects_out: list[dict] = []
    if isinstance(subjects_in, list):
        for idx, subject in enumerate(subjects_in, start=1):
            cleaned = _clean_subject(subject, index=idx)
            if cleaned is not None:
                subjects_out.append(cleaned)

    if not subjects_out:
        subjects_out = [{"title": "Subject 1", "blocks": [_placeholder_paragraph_block()]}]
    out["subjects"] = subjects_out
    return out


def _clean_subject(subject: Any, *, index: int) -> dict | None:
    if isinstance(subject, dict):
        title = _as_non_empty_string(subject.get("title")) or f"Subject {index}"
        description = _as_non_empty_string(subject.get("description"))
        blocks_in = subject.get("blocks")
        subject_id = _as_non_empty_string(subject.get("id"))
    else:
        title = f"Subject {index}"
        description = None
        blocks_in = None
        subject_id = None

    blocks_out: list[dict] = []
    if isinstance(blocks_in, list):
        for block in blocks_in:
            cleaned = _clean_block(block)
            if cleaned is not None:
                blocks_out.append(cleaned)

    if not blocks_out:
        blocks_out = [_placeholder_paragraph_block()]

    out = {"title": title, "blocks": blocks_out}
    if description:
        out["description"] = description
    if subject_id:
        out["id"] = subject_id
    return out


def _clean_block(block: Any) -> dict | None:
    if not isinstance(block, dict):
        text_value = _best_effort_text(block)
        return {"type": "paragraph", "content": _normalize_inline_nodes(text_value)}

    block_type = block.get("type")
    if block_type not in SUPPORTED_BLOCK_TYPES:
        return None

    if block_type in {"section", "subsection"}:
        title = _as_non_empty_string(block.get("title")) or ("Section" if block_type == "section" else "Subsection")
        return {"type": block_type, "title": title}

    if block_type in TEXT_CONTENT_BLOCK_TYPES:
        return {
            "type": block_type,
            "content": _normalize_inline_nodes(block.get("content", block.get("value", ""))),
        }

    if block_type == "code_block":
        value = _best_effort_text(block.get("value", block.get("content", "")))
        out = {"type": "code_block", "value": value}
        lang = _as_non_empty_string(block.get("lang"))
        if lang:
            out["lang"] = lang[:32]
        return out

    if block_type == "math_block":
        value = _normalize_math_expression(_as_non_empty_string(block.get("value")) or "x")
        return {"type": "math_block", "value": value}

    if block_type == "table":
        rows = _normalize_rows(block.get("rows"))
        out = {"type": "table", "rows": rows}
        caption = block.get("caption")
        if caption is not None:
            out["caption"] = _normalize_inline_nodes(caption)
        return out

    if block_type == "image":
        src = _as_non_empty_string(block.get("src")) or "image.png"
        out = {"type": "image", "src": src}
        alt = _as_non_empty_string(block.get("alt"))
        if alt:
            out["alt"] = alt
        caption = block.get("caption")
        if caption is not None:
            out["caption"] = _normalize_inline_nodes(caption)
        return out

    if block_type == "image_placeholder":
        out: dict[str, Any] = {"type": "image_placeholder"}
        reserve = _as_number(block.get("reserve_height_mm"))
        ratio = _as_number(block.get("aspect_ratio"))
        if reserve is None and ratio is None:
            reserve = 60.0
        if reserve is not None:
            out["reserve_height_mm"] = reserve
        if ratio is not None:
            out["aspect_ratio"] = ratio
        if isinstance(block.get("border"), bool):
            out["border"] = block["border"]
        label = _as_non_empty_string(block.get("label"))
        if label:
            out["label"] = label
        caption = block.get("caption")
        if caption is not None:
            out["caption"] = _normalize_inline_nodes(caption)
        return out

    if block_type in {"bullet_list", "numbered_list"}:
        items = _normalize_list_items(block.get("items"))
        return {"type": block_type, "items": items}

    if block_type in {"page_break", "horizontal_rule"}:
        return {"type": block_type}

    return None


def _normalize_rows(value: Any) -> list[list[dict]]:
    rows_out: list[list[dict]] = []
    if isinstance(value, list):
        for row in value:
            if not isinstance(row, list):
                row = [row]
            cells_out: list[dict] = []
            for cell in row:
                if isinstance(cell, dict) and "content" in cell:
                    content = _normalize_inline_nodes(cell.get("content"))
                else:
                    content = _normalize_inline_nodes(cell)
                cells_out.append({"content": content})
            if cells_out:
                rows_out.append(cells_out)
    if not rows_out:
        rows_out = [[{"content": _normalize_inline_nodes("")}]]
    return rows_out


def _normalize_list_items(value: Any) -> list[list[dict]]:
    items_out: list[list[dict]] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, list):
                nodes = _normalize_inline_nodes(item)
            else:
                nodes = _normalize_inline_nodes(item)
            items_out.append(nodes)
    if not items_out:
        items_out = [_normalize_inline_nodes("Item")]
    return items_out


def _normalize_inline_nodes(value: Any) -> list[dict]:
    if isinstance(value, str):
        return [{"type": "text", "value": value}]

    items = value if isinstance(value, list) else [value]
    out: list[dict] = []
    for item in items:
        node = _clean_inline_node(item)
        if node is not None:
            out.append(node)
    if not out:
        out = [{"type": "text", "value": ""}]
    return out


def _clean_inline_node(node: Any) -> dict | None:
    if isinstance(node, str):
        return {"type": "text", "value": node}

    if not isinstance(node, dict):
        return {"type": "text", "value": _best_effort_text(node)}

    node_type = node.get("type")
    if node_type not in SUPPORTED_INLINE_TYPES:
        return {"type": "text", "value": _best_effort_text(node)}

    if node_type == "text":
        return {"type": "text", "value": _best_effort_text(node.get("value", ""))}

    if node_type == "ltr":
        value = _as_non_empty_string(node.get("value")) or _best_effort_text(node)
        out = {"type": "ltr", "value": value}
        style = node.get("style")
        if style in {"plain", "boxed", "mono"}:
            out["style"] = style
        return out

    if node_type == "inline_math":
        value = _normalize_math_expression(_as_non_empty_string(node.get("value")) or "x")
        return {"type": "inline_math", "value": value}

    if node_type == "inline_code":
        value = _best_effort_text(node.get("value", ""))
        out = {"type": "inline_code", "value": value}
        lang = _as_non_empty_string(node.get("lang"))
        if lang:
            out["lang"] = lang[:32]
        return out

    return None


def _inject_defaults(project: dict, *, title_hint: str | None, author_hint: str | None) -> dict:
    meta = _normalize_meta(project.get("meta"), title_hint=title_hint, author_hint=author_hint)
    theme = _normalize_theme(project.get("theme"))

    subjects = project.get("subjects")
    subjects_out: list[dict] = []
    used_subject_ids: set[str] = set()
    if isinstance(subjects, list):
        for index, subject in enumerate(subjects, start=1):
            if not isinstance(subject, dict):
                continue
            title = _as_non_empty_string(subject.get("title")) or f"Subject {index}"
            subject_id = generate_safe_id(
                "subject",
                used_subject_ids,
                seed=_as_non_empty_string(subject.get("id")) or title,
            )

            blocks_out: list[dict] = []
            used_block_ids: set[str] = set()
            for block in subject.get("blocks", []):
                if not isinstance(block, dict) or block.get("type") not in SUPPORTED_BLOCK_TYPES:
                    continue
                clean = deepcopy(block)
                prefix = make_safe_identifier(str(clean["type"]), fallback_prefix="block")
                clean["id"] = generate_safe_id(prefix, used_block_ids, seed=_as_non_empty_string(clean.get("id")))
                blocks_out.append(clean)

            if not blocks_out:
                placeholder = _placeholder_paragraph_block()
                placeholder["id"] = generate_safe_id("paragraph", used_block_ids)
                blocks_out = [placeholder]

            subject_out = {"id": subject_id, "title": title, "blocks": blocks_out}
            description = _as_non_empty_string(subject.get("description"))
            if description:
                subject_out["description"] = description
            subjects_out.append(subject_out)

    if not subjects_out:
        subject_id = generate_safe_id("subject", used_subject_ids, seed="subject_1")
        block_id = generate_safe_id("paragraph", set(), seed="paragraph_1")
        placeholder = _placeholder_paragraph_block()
        placeholder["id"] = block_id
        subjects_out = [{"id": subject_id, "title": "Subject 1", "blocks": [placeholder]}]

    return {"meta": meta, "theme": theme, "subjects": subjects_out}


def _normalize_meta(meta_in: Any, *, title_hint: str | None, author_hint: str | None) -> dict:
    meta = default_meta_skeleton(title_hint=title_hint, author_hint=author_hint)
    if isinstance(meta_in, dict):
        incoming_title = _as_non_empty_string(meta_in.get("title"))
        incoming_author = _as_non_empty_string(meta_in.get("author"))
        if incoming_title and not (title_hint and title_hint.strip()):
            meta["title"] = incoming_title
        if incoming_author and not (author_hint and author_hint.strip()):
            meta["author"] = incoming_author

        subtitle = _as_non_empty_string(meta_in.get("subtitle"))
        if subtitle:
            meta["subtitle"] = subtitle

        language = _as_non_empty_string(meta_in.get("language"))
        if language:
            meta["language"] = language
        direction = _as_non_empty_string(meta_in.get("direction"))
        if direction in {"ltr", "rtl"}:
            meta["direction"] = direction
        version = _as_non_empty_string(meta_in.get("version"))
        if version:
            meta["version"] = version

        preferred_id = _as_non_empty_string(meta_in.get("id")) or meta["title"]
    else:
        preferred_id = meta["title"]

    meta["id"] = make_safe_identifier(preferred_id, fallback_prefix="project")
    if not _as_non_empty_string(meta.get("language")):
        meta["language"] = "ar"
    if meta.get("direction") not in {"ltr", "rtl"}:
        meta["direction"] = "rtl"
    if not _as_non_empty_string(meta.get("version")):
        meta["version"] = "1.0.0"
    now = now_rfc3339()
    meta["created_at"] = now
    meta["updated_at"] = now
    return meta


def _normalize_theme(theme_in: Any) -> dict:
    theme = deepcopy(DEFAULT_THEME)
    if not isinstance(theme_in, dict):
        return theme

    page = theme_in.get("page")
    if isinstance(page, dict):
        size = page.get("size")
        if size in {"A4", "Letter"}:
            theme["page"]["size"] = size
        dpi = page.get("dpi")
        if isinstance(dpi, int):
            theme["page"]["dpi"] = dpi
        margins = page.get("margin_mm")
        if isinstance(margins, dict):
            for k in ("top", "right", "bottom", "left"):
                v = margins.get(k)
                if isinstance(v, (int, float)):
                    theme["page"]["margin_mm"][k] = float(v)

    fonts = theme_in.get("fonts")
    if isinstance(fonts, dict):
        for k in ("base", "mono", "math"):
            v = _as_non_empty_string(fonts.get(k))
            if v:
                theme["fonts"][k] = v

    colors = theme_in.get("colors")
    if isinstance(colors, dict):
        for k in ("text", "background", "muted", "accent", "border", "code_bg"):
            v = _as_non_empty_string(colors.get(k))
            if v:
                theme["colors"][k] = v

    text = theme_in.get("text")
    if isinstance(text, dict):
        size = text.get("base_size_px")
        line_height = text.get("line_height")
        if isinstance(size, (int, float)):
            theme["text"]["base_size_px"] = float(size)
        if isinstance(line_height, (int, float)):
            theme["text"]["line_height"] = float(line_height)

    ltr_style = theme_in.get("ltr_inline_style")
    if isinstance(ltr_style, dict):
        border = _as_non_empty_string(ltr_style.get("boxed_border_color"))
        if border:
            theme["ltr_inline_style"]["boxed_border_color"] = border
    return theme


def _placeholder_paragraph_block() -> dict:
    return {"type": "paragraph", "content": [{"type": "text", "value": ""}]}


def _as_non_empty_string(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return stripped
    return None


def _as_number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _best_effort_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        for key in ("value", "text", "title", "label", "content"):
            if key in value:
                return _best_effort_text(value[key])
    if isinstance(value, list):
        return " ".join(_best_effort_text(v) for v in value if _best_effort_text(v))
    return json.dumps(value, ensure_ascii=False)


def _normalize_math_expression(value: str) -> str:
    expr = re.sub(r"\s+", " ", value.strip())
    if not expr:
        return "x"

    expr = _normalize_big_o_forms(expr)
    expr = re.sub(r"(?i)\blog(?=[A-Za-z0-9])", "log ", expr)
    expr = re.sub(r"\b([A-Za-z])(\d+)\b", r"\1^\2", expr)
    expr = re.sub(r"([A-Za-z0-9\)])([A-Za-z])\(", r"\1 \2(", expr)
    expr = re.sub(r"\s*([=+\-*/])\s*", r" \1 ", expr)
    expr = re.sub(r"\s*\^\s*", "^", expr)
    expr = re.sub(r"=\s*([A-Za-z])([A-Za-z](?:\^\d+)?)\b", r"= \1 \2", expr)
    expr = re.sub(r"\+\s*([A-Za-z])([A-Za-z](?:\^\d+)?)\b", r"+ \1 \2", expr)
    expr = re.sub(r"-\s*([A-Za-z])([A-Za-z](?:\^\d+)?)\b", r"- \1 \2", expr)
    expr = re.sub(r"\s+", " ", expr).strip()
    return expr or "x"


def _normalize_big_o_forms(expr: str) -> str:
    def _rewrite(match: re.Match[str]) -> str:
        inner = match.group(1).strip()
        inner = re.sub(r"(?i)\blog(?=[A-Za-z0-9])", "log ", inner)
        inner = re.sub(r"\b([A-Za-z])(\d+)\b", r"\1^\2", inner)
        inner = re.sub(r"([A-Za-z0-9\)])(?=log\b)", r"\1 ", inner)
        inner = re.sub(r"\s+", " ", inner).strip()
        return f"O({inner})"

    return re.sub(r"\bO\s*\(([^()]*)\)", _rewrite, expr)
