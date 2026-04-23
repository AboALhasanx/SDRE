from __future__ import annotations


def build_generation_prompt(*, title_hint: str | None = None, author_hint: str | None = None) -> str:
    title_note = f"Preferred title hint: {title_hint.strip()}" if title_hint and title_hint.strip() else "No title hint provided."
    author_note = (
        f"Preferred author hint: {author_hint.strip()}" if author_hint and author_hint.strip() else "No author hint provided."
    )
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
