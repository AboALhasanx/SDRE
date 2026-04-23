from src.ai.defaults import IDENTIFIER_PATTERN
from src.ai.schema_adapter import sanitize_project_draft
from src.validation.engine import validate_project_data


def test_recovery_wraps_project_blocks_into_subjects():
    draft = {
        "project": {
            "meta": {"title": "Recovered"},
            "blocks": [{"type": "paragraph", "content": "hello"}],
        }
    }
    out = sanitize_project_draft(draft)
    subjects = out["project"]["subjects"]
    assert len(subjects) == 1
    assert len(subjects[0]["blocks"]) == 1
    assert subjects[0]["blocks"][0]["type"] == "paragraph"
    assert subjects[0]["blocks"][0]["content"][0]["value"] == "hello"


def test_recovery_injects_placeholder_when_subject_blocks_missing():
    draft = {"project": {"subjects": [{"title": "S1"}]}}
    out = sanitize_project_draft(draft)
    blocks = out["project"]["subjects"][0]["blocks"]
    assert blocks
    assert blocks[0]["type"] == "paragraph"


def test_cleaning_removes_unknown_block_types_and_normalizes_lists_table():
    draft = {
        "project": {
            "subjects": [
                {
                    "title": "S",
                    "blocks": [
                        {"type": "unknown_block", "x": 1},
                        {"type": "bullet_list", "items": ["a", {"type": "inline_math", "value": "x"}]},
                        {"type": "table", "rows": [["r1c1", {"content": "r1c2"}]]},
                    ],
                }
            ]
        }
    }
    out = sanitize_project_draft(draft)
    blocks = out["project"]["subjects"][0]["blocks"]
    assert len(blocks) == 2
    assert blocks[0]["type"] == "bullet_list"
    assert blocks[0]["items"][0][0]["type"] == "text"
    assert blocks[1]["type"] == "table"
    assert blocks[1]["rows"][0][0]["content"][0]["type"] == "text"


def test_cleaning_injects_placeholder_height_for_image_placeholder():
    draft = {
        "project": {
            "subjects": [
                {
                    "title": "S",
                    "blocks": [{"type": "image_placeholder", "label": "Figure"}],
                }
            ]
        }
    }
    out = sanitize_project_draft(draft)
    block = out["project"]["subjects"][0]["blocks"][0]
    assert block["type"] == "image_placeholder"
    assert block["reserve_height_mm"] == 60.0


def test_injection_generates_valid_ids_and_defaults():
    draft = {
        "project": {
            "meta": {"title": "AI Doc"},
            "subjects": [{"title": "A", "blocks": [{"type": "paragraph", "content": "ok"}]}],
        }
    }
    out = sanitize_project_draft(draft, title_hint="Hinted title", author_hint="Hinted author")
    project = out["project"]
    assert project["meta"]["language"] == "ar"
    assert project["meta"]["direction"] == "rtl"
    assert project["meta"]["version"] == "1.0.0"
    assert project["meta"]["title"] == "Hinted title"
    assert project["meta"]["author"] == "Hinted author"

    for subject in project["subjects"]:
        assert IDENTIFIER_PATTERN.match(subject["id"])
        for block in subject["blocks"]:
            assert IDENTIFIER_PATTERN.match(block["id"])

    report = validate_project_data(out, file_label="<ai-sanitized>")
    assert report.ok is True
