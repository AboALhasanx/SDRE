from __future__ import annotations

import re
from datetime import datetime, timezone

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")

DEFAULT_THEME: dict = {
    "page": {
        "size": "A4",
        "dpi": 300,
        "margin_mm": {"top": 15, "right": 15, "bottom": 15, "left": 15},
    },
    "fonts": {"base": "Arial", "mono": "Consolas", "math": "STIX Two Math"},
    "colors": {
        "text": "#111111",
        "background": "#FFFFFF",
        "muted": "#666666",
        "accent": "#0B5FFF",
        "border": "#DDDDDD",
        "code_bg": "#F6F8FA",
    },
    "text": {"base_size_px": 14, "line_height": 1.6},
    "ltr_inline_style": {"boxed_border_color": "#DDDDDD"},
}


def now_rfc3339() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def make_safe_identifier(raw: str | None, *, fallback_prefix: str = "id") -> str:
    text = (raw or "").strip()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^A-Za-z0-9_-]", "_", text)
    text = re.sub(r"_+", "_", text).strip("_-")
    if not text:
        text = fallback_prefix
    if not text[0].isalpha():
        text = f"{fallback_prefix}_{text}"
    text = text[:64]
    if not text[0].isalpha():
        text = f"id_{text}"
        text = text[:64]
    return text


def generate_safe_id(prefix: str, used_ids: set[str], *, seed: str | None = None) -> str:
    base = make_safe_identifier(seed or prefix, fallback_prefix=prefix)
    candidate = base
    index = 1
    while candidate in used_ids:
        candidate = make_safe_identifier(f"{base}_{index}", fallback_prefix=prefix)
        index += 1
    used_ids.add(candidate)
    return candidate


def default_meta_skeleton(*, title_hint: str | None = None, author_hint: str | None = None) -> dict:
    now = now_rfc3339()
    title = (title_hint or "").strip() or "AI Generated Project"
    author = (author_hint or "").strip() or "AI Assistant"
    return {
        "id": make_safe_identifier(title, fallback_prefix="project"),
        "title": title,
        "author": author,
        "language": "ar",
        "direction": "rtl",
        "version": "1.0.0",
        "created_at": now,
        "updated_at": now,
    }
