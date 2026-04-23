from __future__ import annotations

from src.ai.chunker import chunk_text, should_use_chunking


def _structured_heading_text() -> str:
    paragraph = (
        "This paragraph explains core details and keeps enough length to force chunk packing "
        "without losing the section context across the generated chunks."
    )
    return "\n".join(
        [
            "1. Introduction",
            paragraph * 2,
            "2. Data Modeling",
            paragraph * 2,
            "3. Validation Strategy",
            paragraph * 2,
            "4. Build Pipeline",
            paragraph * 2,
        ]
    )


def test_chunker_heading_based_chunking_prefers_heading_boundaries():
    text = _structured_heading_text()
    chunks = chunk_text(
        text,
        threshold_chars=250,
        target_chunk_chars=380,
        min_chunk_chars=240,
        max_chunk_chars=520,
    )
    assert len(chunks) >= 2
    assert chunks[0].text.startswith("1. Introduction")
    assert any("2. Data Modeling" in chunk.text for chunk in chunks[1:])


def test_chunker_fallback_paragraph_grouping_without_headings():
    text = "\n\n".join(
        [
            "Paragraph one has enough detail to represent a meaningful segment in the source input.",
            "Paragraph two continues with additional explanation and no heading syntax at all.",
            "Paragraph three adds practical examples and keeps the flow paragraph-based only.",
            "Paragraph four closes the topic with summary details and notes.",
        ]
    )
    chunks = chunk_text(
        text,
        threshold_chars=120,
        target_chunk_chars=180,
        min_chunk_chars=120,
        max_chunk_chars=230,
    )
    assert len(chunks) >= 2
    assert all("Paragraph" in chunk.text for chunk in chunks)
    assert "Paragraph one" in chunks[0].text
    assert "Paragraph four" in chunks[-1].text


def test_chunker_threshold_behavior_switches_mode_deterministically():
    short_text = "Short input stays single-shot."
    long_text = short_text * 400

    assert should_use_chunking(short_text, threshold_chars=200) is False
    assert should_use_chunking(long_text, threshold_chars=200) is True

    short_chunks = chunk_text(short_text, threshold_chars=200)
    assert len(short_chunks) == 1
    assert short_chunks[0].text == short_text
