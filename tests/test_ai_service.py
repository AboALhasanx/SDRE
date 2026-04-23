from src.ai.ai_service import AIService
from src.validation.report import ValidationReport


class _StubClient:
    def __init__(self, response: str):
        self.response = response

    def generate_json_draft(self, raw_text: str, prompt: str) -> str:
        return self.response


def test_ai_service_accepts_valid_json_draft():
    client = _StubClient(
        """
        {
          "project": {
            "meta": {"title": "From AI"},
            "subjects": [
              {"title": "Topic", "blocks": [{"type": "paragraph", "content": "Hello"}]}
            ]
          }
        }
        """
    )
    service = AIService(client=client)
    result = service.generate_project_draft("Any text")
    assert result.ok is True
    assert result.validation_report is not None and result.validation_report.ok is True
    assert result.sanitized_payload is not None
    assert result.sanitized_payload["project"]["subjects"]


def test_ai_service_handles_malformed_model_output():
    service = AIService(client=_StubClient("not-json"))
    result = service.generate_project_draft("Any text")
    assert result.ok is False
    assert result.stage == "parse"
    assert result.validation_report is not None
    assert result.validation_report.stage == "parse"


def test_ai_service_handles_schema_invalid_result_via_validator():
    client = _StubClient('{"project": {"subjects": [{"title":"S","blocks":[{"type":"paragraph","content":"x"}]}]}}')

    def _invalid_validator(data, *, file_label="<x>"):
        return ValidationReport(ok=False, file=file_label, stage="schema", errors=[])

    service = AIService(client=client, validator=_invalid_validator)
    result = service.generate_project_draft("text")
    assert result.ok is False
    assert result.stage == "validate"
    assert result.validation_report is not None
    assert result.validation_report.stage == "schema"
