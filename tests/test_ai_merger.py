from __future__ import annotations

from src.ai.merger import merge_chunk_projects
from src.validation.engine import validate_project_data


def _chunk_payload(subject_title: str, *, subject_id: str, block_id: str) -> dict:
    return {
        "project": {
            "meta": {
                "id": "proj",
                "title": "Chunked",
                "author": "AI",
                "language": "ar",
                "direction": "rtl",
                "version": "1.0.0",
                "created_at": "2026-04-23T00:00:00Z",
                "updated_at": "2026-04-23T00:00:00Z",
            },
            "theme": {
                "page": {"size": "A4", "dpi": 300, "margin_mm": {"top": 15, "right": 15, "bottom": 15, "left": 15}},
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
            },
            "subjects": [
                {
                    "id": subject_id,
                    "title": subject_title,
                    "blocks": [
                        {"id": block_id, "type": "section", "title": f"{subject_title} Section"},
                        {
                            "id": f"{block_id}_p",
                            "type": "paragraph",
                            "content": [{"type": "text", "value": f"Paragraph for {subject_title}"}],
                        },
                    ],
                }
            ],
        }
    }


def test_merge_preserves_subject_order_and_unique_ids():
    payloads = [
        _chunk_payload("First", subject_id="subject_1", block_id="block_1"),
        _chunk_payload("Second", subject_id="subject_1", block_id="block_1"),
    ]
    merged, summary = merge_chunk_projects(payloads)
    subjects = merged["project"]["subjects"]

    assert [s["title"] for s in subjects] == ["First", "Second"]
    subject_ids = [s["id"] for s in subjects]
    assert len(subject_ids) == len(set(subject_ids))

    block_ids = [b["id"] for s in subjects for b in s["blocks"]]
    assert len(block_ids) == len(set(block_ids))
    assert summary.total_chunks == 2
    assert summary.merged_subjects == 2


def test_merge_final_payload_validates_successfully():
    payloads = [
        _chunk_payload("First", subject_id="subject_a", block_id="blk_a"),
        _chunk_payload("Second", subject_id="subject_b", block_id="blk_b"),
    ]
    merged, _summary = merge_chunk_projects(payloads, title_hint="Merged Title")
    report = validate_project_data(merged, file_label="<merged>")
    assert report.ok is True
    assert merged["project"]["meta"]["title"] == "Merged Title"
