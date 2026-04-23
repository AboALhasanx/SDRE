from datetime import datetime

from src.ai.defaults import (
    DEFAULT_THEME,
    IDENTIFIER_PATTERN,
    default_meta_skeleton,
    generate_safe_id,
    make_safe_identifier,
    now_rfc3339,
)
from src.validation.engine import validate_project_data


def test_now_rfc3339_is_parseable():
    value = now_rfc3339()
    assert value.endswith("Z")
    datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_make_safe_identifier_matches_pattern():
    safe = make_safe_identifier(" 123 bad id ! ")
    assert IDENTIFIER_PATTERN.match(safe)


def test_generate_safe_id_is_unique_and_valid():
    used: set[str] = set()
    a = generate_safe_id("subject", used, seed="subject")
    b = generate_safe_id("subject", used, seed="subject")
    assert a != b
    assert IDENTIFIER_PATTERN.match(a)
    assert IDENTIFIER_PATTERN.match(b)


def test_default_theme_and_meta_are_schema_safe():
    meta = default_meta_skeleton(title_hint="AI Draft", author_hint="Tester")
    payload = {
        "project": {
            "meta": meta,
            "theme": DEFAULT_THEME,
            "subjects": [
                {
                    "id": "subject_1",
                    "title": "Subject 1",
                    "blocks": [{"id": "paragraph_1", "type": "paragraph", "content": [{"type": "text", "value": "x"}]}],
                }
            ],
        }
    }
    report = validate_project_data(payload, file_label="<test>")
    assert report.ok is True
