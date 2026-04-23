from __future__ import annotations

import re
from dataclasses import dataclass

CHUNK_SWITCH_THRESHOLD_CHARS = 4200
TARGET_CHUNK_CHARS = 2200
MIN_CHUNK_CHARS = 1100
MAX_CHUNK_CHARS = 3200


@dataclass(frozen=True)
class TextChunk:
    index: int
    text: str
    heading_hint: str | None = None

    @property
    def char_count(self) -> int:
        return len(self.text)


@dataclass(frozen=True)
class _Section:
    text: str
    heading_hint: str | None = None


def should_use_chunking(
    raw_text: str,
    *,
    threshold_chars: int = CHUNK_SWITCH_THRESHOLD_CHARS,
) -> bool:
    return len(raw_text.strip()) > threshold_chars


def chunk_text(
    raw_text: str,
    *,
    threshold_chars: int = CHUNK_SWITCH_THRESHOLD_CHARS,
    target_chunk_chars: int = TARGET_CHUNK_CHARS,
    min_chunk_chars: int = MIN_CHUNK_CHARS,
    max_chunk_chars: int = MAX_CHUNK_CHARS,
) -> list[TextChunk]:
    text = raw_text.strip()
    if not text:
        return []

    if len(text) <= threshold_chars:
        return [TextChunk(index=1, text=text, heading_hint=_first_heading_hint(text))]

    sections = _split_by_heading_boundaries(text)
    if len(sections) <= 1:
        sections = _split_by_paragraph_groups(text)

    packed_sections = _pack_sections(
        sections,
        target_chunk_chars=target_chunk_chars,
        min_chunk_chars=min_chunk_chars,
        max_chunk_chars=max_chunk_chars,
    )
    if len(packed_sections) <= 1 and len(text) > max_chunk_chars:
        packed_sections = _fallback_size_grouping(
            text,
            target_chunk_chars=target_chunk_chars,
            max_chunk_chars=max_chunk_chars,
        )

    if not packed_sections:
        packed_sections = [_Section(text=text, heading_hint=_first_heading_hint(text))]

    return [TextChunk(index=idx + 1, text=s.text, heading_hint=s.heading_hint) for idx, s in enumerate(packed_sections)]


def _split_by_heading_boundaries(text: str) -> list[_Section]:
    lines = [line.rstrip() for line in text.splitlines()]
    if not lines:
        return []

    sections: list[_Section] = []
    current: list[str] = []
    current_heading: str | None = None
    heading_count = 0

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if _is_heading_line(lines, idx):
            heading_count += 1
            if current:
                sections.append(_Section(text="\n".join(current).strip(), heading_hint=current_heading))
                current = []
                current_heading = None
            if stripped:
                current_heading = stripped
        current.append(line)

    if current:
        sections.append(_Section(text="\n".join(current).strip(), heading_hint=current_heading))

    if heading_count < 2:
        return []
    return [s for s in sections if s.text]


def _split_by_paragraph_groups(text: str) -> list[_Section]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    if not paragraphs:
        return [_Section(text=text.strip(), heading_hint=None)]
    return [_Section(text=p, heading_hint=_first_heading_hint(p)) for p in paragraphs]


def _pack_sections(
    sections: list[_Section],
    *,
    target_chunk_chars: int,
    min_chunk_chars: int,
    max_chunk_chars: int,
) -> list[_Section]:
    if not sections:
        return []

    chunks: list[_Section] = []
    current_parts: list[str] = []
    current_length = 0
    current_heading: str | None = None

    def flush() -> None:
        nonlocal current_parts, current_length, current_heading
        if not current_parts:
            return
        chunk_text = "\n\n".join(part for part in current_parts if part).strip()
        if chunk_text:
            chunks.append(_Section(text=chunk_text, heading_hint=current_heading))
        current_parts = []
        current_length = 0
        current_heading = None

    for section in sections:
        section_text = section.text.strip()
        if not section_text:
            continue
        section_len = len(section_text)

        if current_parts and current_length >= min_chunk_chars and section_len + current_length > max_chunk_chars:
            flush()

        if (
            current_parts
            and current_length >= min_chunk_chars
            and current_length >= target_chunk_chars
            and section.heading_hint is not None
        ):
            flush()

        if not current_parts:
            current_heading = section.heading_hint
        current_parts.append(section_text)
        current_length += section_len + 2

    flush()

    if len(chunks) >= 2 and len(chunks[-1].text) < min_chunk_chars:
        prev = chunks[-2]
        merged_text = f"{prev.text}\n\n{chunks[-1].text}".strip()
        merged_heading = prev.heading_hint or chunks[-1].heading_hint
        chunks = chunks[:-2] + [_Section(text=merged_text, heading_hint=merged_heading)]

    return chunks


def _fallback_size_grouping(
    text: str,
    *,
    target_chunk_chars: int,
    max_chunk_chars: int,
) -> list[_Section]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    if not paragraphs:
        paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
    if not paragraphs:
        return []

    chunks: list[_Section] = []
    current: list[str] = []
    current_len = 0

    for paragraph in paragraphs:
        p_len = len(paragraph)
        if current and current_len >= target_chunk_chars and current_len + p_len > max_chunk_chars:
            chunks.append(_Section(text="\n\n".join(current).strip(), heading_hint=_first_heading_hint(current[0])))
            current = []
            current_len = 0
        current.append(paragraph)
        current_len += p_len + 2

    if current:
        chunks.append(_Section(text="\n\n".join(current).strip(), heading_hint=_first_heading_hint(current[0])))
    return chunks


def _is_heading_line(lines: list[str], index: int) -> bool:
    line = lines[index].strip()
    if not line:
        return False
    if re.match(r"^#{1,6}\s+\S+", line):
        return True
    if re.match(r"^\d+[\.\)]\s+\S+", line):
        return True
    if re.match(r"^(Chapter|Section|Part)\b[:\s]", line, flags=re.IGNORECASE):
        return True
    if line.endswith(":") and len(line.split()) <= 10:
        return True
    if _looks_like_bilingual_heading(line):
        return True
    return _looks_like_standalone_heading(lines, index)


def _looks_like_standalone_heading(lines: list[str], index: int) -> bool:
    line = lines[index].strip()
    words = line.split()
    if not (1 <= len(words) <= 10):
        return False
    if len(line) > 90:
        return False
    if line[-1] in ".!?؟؛;,،":
        return False
    next_line = _next_non_empty_line(lines, index + 1)
    if not next_line:
        return False
    if len(next_line.split()) < len(words) + 2:
        return False
    return True


def _looks_like_bilingual_heading(line: str) -> bool:
    if "(" not in line or ")" not in line:
        return False
    if len(line.split()) > 14:
        return False
    return _contains_arabic(line) and _contains_latin(line)


def _first_heading_hint(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for idx, _line in enumerate(lines):
        if _is_heading_line(lines, idx):
            return lines[idx]
    return None


def _next_non_empty_line(lines: list[str], start: int) -> str | None:
    for idx in range(start, len(lines)):
        line = lines[idx].strip()
        if line:
            return line
    return None


def _contains_arabic(text: str) -> bool:
    return any("\u0600" <= ch <= "\u06FF" for ch in text)


def _contains_latin(text: str) -> bool:
    return any("a" <= ch.lower() <= "z" for ch in text)
