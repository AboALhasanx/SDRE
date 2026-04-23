from __future__ import annotations

import json
from typing import Any, Iterable


def _hint_line(label: str, value: str | None) -> str:
    clean = (value or "").strip()
    if clean:
        return f"{label}: {clean}"
    return f"{label}: not provided."


def _json_snippet(value: Any, *, fallback: str = "null") -> str:
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except Exception:
        return fallback


def _format_error_lines(errors: Iterable[dict[str, str]]) -> str:
    lines: list[str] = []
    for item in errors:
        path = item.get("path", "/")
        message = item.get("message", "Validation error")
        hint = item.get("hint", "")
        if hint:
            lines.append(f"- path={path} | message={message} | hint={hint}")
        else:
            lines.append(f"- path={path} | message={message}")
    if not lines:
        return "- path=/ | message=Unknown technical validation failure."
    return "\n".join(lines)


def build_generation_prompt(*, title_hint: str | None = None, author_hint: str | None = None) -> str:
    title_note = _hint_line("Preferred title hint", title_hint)
    author_note = _hint_line("Preferred author hint", author_hint)
    return f"""
You are generating an SDRE draft in JSON from raw source text.

Output requirements:
1) Return JSON only. No markdown fences. No commentary.
2) Output must be a JSON object.
3) Use only supported block types:
   section, subsection, paragraph, code_block, math_block, table, image, image_placeholder,
   note, warning, bullet_list, numbered_list, page_break, horizontal_rule
4) Use only supported inline types:
   text, ltr, inline_math, inline_code
5) Keep structure focused and practical (subjects -> blocks).
6) Do NOT invent timestamps. Do NOT invent IDs. Do NOT invent complex theme details.
7) If unsure about exact formatting, prefer simple paragraph blocks with text nodes.

Compact shape reminder:
{{
  "project": {{
    "meta": {{"title": "...", "author": "..."}},
    "subjects": [
      {{
        "title": "...",
        "blocks": [ ... ]
      }}
    ]
  }}
}}

Short valid snippets:
- paragraph with text + ltr:
  {{"type":"paragraph","content":[{{"type":"text","value":"Use "}},{{"type":"ltr","value":"Binary Search","style":"boxed"}}]}}
- inline_math:
  {{"type":"inline_math","value":"O(log n)"}}
- inline_code:
  {{"type":"inline_code","value":"x += 1","lang":"python"}}
- bullet_list:
  {{"type":"bullet_list","items":[[{{"type":"text","value":"First"}}],[{{"type":"text","value":"Second"}}]]}}

Additional context:
- {title_note}
- {author_note}
""".strip()


def build_technical_correction_prompt(
    *,
    raw_text: str,
    errors: list[dict[str, str]],
    previous_json: Any | None = None,
    fragment_json: Any | None = None,
    fragment_path: str | None = None,
    title_hint: str | None = None,
    author_hint: str | None = None,
) -> str:
    title_note = _hint_line("Preferred title hint", title_hint)
    author_note = _hint_line("Preferred author hint", author_hint)
    error_lines = _format_error_lines(errors)
    if fragment_json is not None:
        fragment_note = f"Target fragment path: {fragment_path or '/'}"
        return f"""
You are fixing a technically invalid SDRE JSON fragment.

Return JSON only. No markdown. No commentary.
Output MUST be one JSON object representing only the corrected fragment (not the whole project).
Keep the same semantic meaning; fix structure/types only.
Use only supported SDRE block/inline types and valid field shapes.

Technical errors to fix:
{error_lines}

{fragment_note}
Fragment JSON to fix:
{_json_snippet(fragment_json, fallback="{}")}

Source text (for context only):
{raw_text}

Additional context:
- {title_note}
- {author_note}
""".strip()

    return f"""
You are fixing a technically invalid SDRE project JSON.

Return JSON only. No markdown. No commentary.
Output MUST be one JSON object for the SDRE project draft.
Keep structure/meaning, but fix schema/model violations.
Use only supported SDRE block/inline types and valid field shapes.

Technical errors to fix:
{error_lines}

Previous JSON draft:
{_json_snippet(previous_json, fallback="{}")}

Source text:
{raw_text}

Additional context:
- {title_note}
- {author_note}
""".strip()


def build_semantic_retry_prompt(
    *,
    raw_text: str,
    semantic_reasons: list[str],
    previous_json: Any | None = None,
    title_hint: str | None = None,
    author_hint: str | None = None,
) -> str:
    title_note = _hint_line("Preferred title hint", title_hint)
    author_note = _hint_line("Preferred author hint", author_hint)
    reason_lines = "\n".join(f"- {r}" for r in semantic_reasons) or "- Previous output was too sparse."
    return f"""
You previously generated an SDRE JSON draft that was technically valid but semantically incomplete.

Regenerate a fuller draft from the same source text.
Return JSON only. No markdown. No commentary.
Output must be one SDRE JSON object with practical coverage.

Requirements for this retry:
1) Preserve major document structure and headings where possible.
2) Produce sufficient section/subsection and content blocks for the source length.
3) Avoid collapsing rich text into one tiny paragraph.
4) Use only supported SDRE block/inline types.
5) Do not invent IDs/timestamps/complex theme details.

Why previous draft was rejected:
{reason_lines}

Previous draft (for reference):
{_json_snippet(previous_json, fallback="{}")}

Source text:
{raw_text}

Additional context:
- {title_note}
- {author_note}
""".strip()
