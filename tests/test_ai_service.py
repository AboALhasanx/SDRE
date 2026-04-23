from __future__ import annotations

from typing import Any

from src.ai.ai_service import AIService
from src.validation.errors import ErrorItem
from src.validation.report import ValidationReport


class _StubClient:
    def __init__(self, responses: list[str] | None = None, *, error_on_call: int | None = None):
        self.responses = responses or []
        self.error_on_call = error_on_call
        self.calls = 0
        self.prompts: list[str] = []

    def generate_json_draft(self, raw_text: str, prompt: str) -> str:
        self.calls += 1
        self.prompts.append(prompt)
        if self.error_on_call is not None and self.calls == self.error_on_call:
            raise RuntimeError("provider unavailable")
        if self.responses:
            return self.responses.pop(0)
        return "not-json"


def _valid_minimal_project_json() -> str:
    return """
    {
      "project": {
        "meta": {"title": "From AI"},
        "subjects": [
          {"title": "Topic", "blocks": [{"type": "paragraph", "content": "Hello world from AI"}]}
        ]
      }
    }
    """


def _valid_rich_project_json() -> str:
    return """
    {
      "project": {
        "meta": {"title": "Rich"},
        "subjects": [
          {
            "title": "Algorithms",
            "blocks": [
              {"type": "section", "title": "Intro"},
              {"type": "paragraph", "content": "Overview and context around the algorithm and its assumptions."},
              {"type": "section", "title": "Preconditions"},
              {"type": "subsection", "title": "Steps"},
              {"type": "subsection", "title": "Complexity"},
              {"type": "bullet_list", "items": ["Prepare input", "Split range", "Choose midpoint", "Compare values"]},
              {"type": "code_block", "value": "def search(arr, target):\\n    lo, hi = 0, len(arr)-1\\n    return -1", "lang": "python"},
              {"type": "paragraph", "content": "Complexity analysis and edge-case handling details."}
            ]
          }
        ]
      }
    }
    """


def _long_structured_source() -> str:
    return "\n".join(
        [
            "1. Introduction",
            "This section introduces binary search and where it is used in sorted arrays.",
            "2. Preconditions",
            "The data must be sorted and random access is assumed.",
            "3. Procedure",
            "Start from the midpoint and shrink range based on comparison.",
            "4. Complexity",
            "Time complexity is logarithmic and memory overhead is small.",
            "5. Edge Cases",
            "Handle empty arrays, duplicates, and not-found outcomes explicitly.",
        ]
    )


def test_ai_service_accepts_valid_json_draft():
    service = AIService(client=_StubClient([_valid_minimal_project_json()]))
    result = service.generate_project_draft("Any text", max_attempts=1)
    assert result.ok is True
    assert result.validation_report is not None and result.validation_report.ok is True
    assert result.sanitized_payload is not None
    assert result.sanitized_payload["project"]["subjects"]
    assert result.attempts == 1


def test_ai_service_classifies_parse_failure_as_technical():
    service = AIService(client=_StubClient(["not-json"]))
    result = service.generate_project_draft("Any text", max_attempts=1)
    assert result.ok is False
    assert result.stage == "parse"
    assert result.failure_class == "technical"
    assert result.validation_report is not None
    assert result.validation_report.stage == "parse"


def test_ai_service_classifies_schema_model_failure_as_technical():
    client = _StubClient(['{"project": {"subjects": [{"title":"S","blocks":[{"type":"paragraph","content":"x"}]}]}}'])

    def _invalid_validator(data: Any, *, file_label: str = "<x>") -> ValidationReport:
        return ValidationReport(
            ok=False,
            file=file_label,
            stage="model",
            errors=[
                ErrorItem(
                    code="model.validation",
                    severity="error",
                    path="/project/subjects/0/blocks/0",
                    message="Dummy model failure",
                    hint="",
                )
            ],
        )

    service = AIService(client=client, validator=_invalid_validator)
    result = service.generate_project_draft("text", max_attempts=1)
    assert result.ok is False
    assert result.failure_class == "technical"
    assert result.stage == "model"


def test_ai_service_classifies_semantic_under_generation():
    service = AIService(client=_StubClient([_valid_minimal_project_json()]))
    result = service.generate_project_draft(_long_structured_source(), max_attempts=1)
    assert result.ok is False
    assert result.failure_class == "semantic"
    assert result.stage == "semantic"
    assert result.semantic_reasons
    assert result.semantic_score is not None


def test_ai_service_retries_with_semantic_prompt_and_recovers():
    client = _StubClient([_valid_minimal_project_json(), _valid_rich_project_json()])
    service = AIService(client=client)

    result = service.generate_project_draft(_long_structured_source())
    assert result.ok is True
    assert result.attempts == 2
    assert result.correction_applied is True
    assert any("semantically incomplete" in prompt for prompt in client.prompts[1:])


def test_ai_service_retries_with_technical_prompt_and_recovers():
    client = _StubClient(["not-json", _valid_rich_project_json()])
    service = AIService(client=client)

    result = service.generate_project_draft("Any source text")
    assert result.ok is True
    assert result.attempts == 2
    assert result.correction_applied is True
    assert any("technically invalid SDRE project JSON" in prompt for prompt in client.prompts[1:])


def test_ai_service_stops_after_max_retries():
    service = AIService(client=_StubClient(["not-json", "still-bad", "again-bad"]))
    result = service.generate_project_draft("Any text")
    assert result.ok is False
    assert result.max_retries_exceeded is True
    assert result.attempts == 3
    assert result.failure_class == "technical"


def test_ai_service_recovers_after_provider_failure():
    client = _StubClient([_valid_rich_project_json()], error_on_call=1)
    service = AIService(client=client)
    result = service.generate_project_draft("source text")
    assert result.ok is True
    assert result.attempts == 2
    assert result.correction_applied is True


def test_ai_service_uses_localized_block_correction_when_possible():
    initial_full = """
    {
      "project": {
        "meta": {"title": "Local"},
        "subjects": [
          {
            "title": "S1",
            "blocks": [
              {"type": "code_block", "value": "print(1)", "lang": "python"},
              {"type": "paragraph", "content": "extra context paragraph with enough length to be substantive."},
              {"type": "section", "title": "H1"},
              {"type": "subsection", "title": "H2"},
              {"type": "bullet_list", "items": ["a", "b", "c"]}
            ]
          }
        ]
      }
    }
    """
    corrected_fragment = '{"type":"code_block","value":"print(\\"ok\\")\\nprint(2)","lang":"python"}'
    client = _StubClient([initial_full, corrected_fragment])

    call_counter = {"count": 0}

    def _validator(data: Any, *, file_label: str = "<x>") -> ValidationReport:
        call_counter["count"] += 1
        if call_counter["count"] == 1:
            return ValidationReport(
                ok=False,
                file=file_label,
                stage="schema",
                errors=[
                    ErrorItem(
                        code="schema.validation",
                        severity="error",
                        path="/project/subjects/0/blocks/0/value",
                        message="Value must be multiline",
                        hint="",
                    )
                ],
            )
        return ValidationReport(ok=True, file=file_label, stage="ok", errors=[])

    service = AIService(client=client, validator=_validator)
    result = service.generate_project_draft("This source focuses on fixing one local block fragment.")

    assert result.ok is True
    assert result.attempts == 2
    assert call_counter["count"] == 2
    assert any("corrected fragment" in prompt for prompt in client.prompts[1:])
    assert any("/project/subjects/0/blocks/0" in prompt for prompt in client.prompts[1:])
