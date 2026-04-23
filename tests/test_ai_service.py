from __future__ import annotations

import json
import re
import threading
from typing import Any

from src.ai.chunker import chunk_text
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


class _HeadingAwareChunkClient:
    def __init__(self, *, fail_on_call: int | None = None):
        self.calls = 0
        self.prompts: list[str] = []
        self.fail_on_call = fail_on_call

    def generate_json_draft(self, raw_text: str, prompt: str) -> str:
        self.calls += 1
        self.prompts.append(prompt)
        if self.fail_on_call is not None and self.calls == self.fail_on_call:
            return "not-json"

        headings = [
            line.strip()
            for line in raw_text.splitlines()
            if re.match(r"^\d+[\.\)]\s+Section\s+\d+", line.strip(), flags=re.IGNORECASE)
        ]
        if not headings:
            headings = ["Chunk Heading"]

        blocks: list[dict[str, Any]] = []
        for heading in headings:
            blocks.append({"type": "section", "title": heading})
            blocks.append(
                {
                    "type": "paragraph",
                    "content": f"Detailed explanation for {heading} with enough words to avoid sparse output.",
                }
            )
        blocks.append({"type": "bullet_list", "items": ["Point A", "Point B", "Point C"]})
        blocks.append({"type": "code_block", "value": "def chunk_step():\n    return 1", "lang": "python"})

        payload = {
            "project": {
                "meta": {"title": headings[0]},
                "subjects": [
                    {
                        "title": headings[0],
                        "blocks": blocks,
                    }
                ],
            }
        }
        return json.dumps(payload, ensure_ascii=False)


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


def _heading_rich_source() -> str:
    return "\n".join(
        [
            "مقدمة عن الخوارزمية",
            "هذه الفقرة تقدّم فكرة عامة عن الخوارزمية وسياق استخدامها في المقررات التعليمية.",
            "Time Complexity (تعقيد الوقت)",
            "هنا نشرح الفرق بين O(n) و O(log n) وتأثير كل منهما على الأداء.",
            "Space Complexity",
            "يوضح هذا القسم استخدام الذاكرة في أفضل وأسوأ الحالات.",
            "Edge Cases",
            "هذا القسم يذكر القيم الفارغة والتكرارات والحالات الحدية.",
        ]
    )


def _understructured_paragraph_only_json() -> str:
    return """
    {
      "project": {
        "meta": {"title": "Flat Output"},
        "subjects": [
          {
            "title": "Algorithm Notes",
            "blocks": [
              {"type":"paragraph","content":"مقدمة عامة عن الموضوع مع شرح تمهيدي مناسب."},
              {"type":"paragraph","content":"تفاصيل متوسطة عن التعقيد الزمني واستخدام الحالات المختلفة."},
              {"type":"paragraph","content":"عرض مبسط لتعقيد الذاكرة مع أمثلة صغيرة."},
              {"type":"paragraph","content":"قائمة بالحالات الحدية وكيفية التعامل معها."},
              {"type":"paragraph","content":"خلاصة عامة تربط المفاهيم السابقة في سياق واحد."}
            ]
          }
        ]
      }
    }
    """


def _heading_preserving_json() -> str:
    return """
    {
      "project": {
        "meta": {"title": "Structured Output"},
        "subjects": [
          {
            "title": "Algorithm Notes",
            "blocks": [
              {"type":"section","title":"مقدمة عن الخوارزمية"},
              {"type":"paragraph","content":"هذه الفقرة تقدّم فكرة عامة عن الخوارزمية وسياق استخدامها في المقررات التعليمية."},
              {"type":"section","title":"Time Complexity (تعقيد الوقت)"},
              {"type":"paragraph","content":"هنا نشرح الفرق بين O(n) و O(log n) وتأثير كل منهما على الأداء."},
              {"type":"subsection","title":"Space Complexity"},
              {"type":"paragraph","content":"يوضح هذا القسم استخدام الذاكرة في أفضل وأسوأ الحالات."},
              {"type":"subsection","title":"Edge Cases"},
              {"type":"paragraph","content":"هذا القسم يذكر القيم الفارغة والتكرارات والحالات الحدية."}
            ]
          }
        ]
      }
    }
    """


def _heading_rich_source_en() -> str:
    return "\n".join(
        [
            "1. Introduction",
            "Detailed overview paragraph for introduction with practical educational context and examples.",
            "2. Data Modeling",
            "Detailed overview paragraph for data modeling with constraints, entities, and relationships.",
            "3. Validation Rules",
            "Detailed overview paragraph for validation strategy and strict rule enforcement behavior.",
            "4. Build Pipeline",
            "Detailed overview paragraph for generation and build flow with operational notes.",
        ]
    )


def _subject_heading_preserving_json() -> str:
    return """
    {
      "project": {
        "meta": {"title": "Subject Heading Preservation"},
        "subjects": [
          {
            "title": "1. Introduction",
            "blocks": [
              {"type":"paragraph","content":"Intro explanation with enough detail to be treated as substantive content."},
              {"type":"bullet_list","items":["Context","Goal","Scope"]}
            ]
          },
          {
            "title": "2. Data Modeling",
            "blocks": [
              {"type":"paragraph","content":"Data modeling explanation including entities, constraints, and relationship notes."},
              {"type":"bullet_list","items":["Entities","Constraints","Relations"]}
            ]
          },
          {
            "title": "3. Validation Rules",
            "blocks": [
              {"type":"paragraph","content":"Validation rules explanation with deterministic enforcement and error pathways."},
              {"type":"bullet_list","items":["Schema checks","Model checks","Fallback handling"]}
            ]
          },
          {
            "title": "4. Build Pipeline",
            "blocks": [
              {"type":"paragraph","content":"Build pipeline explanation for generation, strict build, and report output handling."},
              {"type":"bullet_list","items":["Generate","Build","Report"]}
            ]
          }
        ]
      }
    }
    """


def test_ai_service_accepts_valid_json_draft():
    client = _StubClient([_valid_minimal_project_json()])
    service = AIService(client=client)
    result = service.generate_project_draft("Any text", max_attempts=1)
    assert result.ok is True
    assert result.validation_report is not None and result.validation_report.ok is True
    assert result.sanitized_payload is not None
    assert result.sanitized_payload["project"]["subjects"]
    assert result.attempts == 1
    assert "Heading-like source lines should generally become section/subsection blocks." in client.prompts[0]
    assert "Preserve displayed equations faithfully" in client.prompts[0]


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


def test_ai_service_detects_heading_under_preservation_semantically():
    service = AIService(client=_StubClient([_understructured_paragraph_only_json()]))
    result = service.generate_project_draft(_heading_rich_source(), max_attempts=1)
    assert result.ok is False
    assert result.failure_class == "semantic"
    assert any("Explicit headings were under-preserved." in reason for reason in result.semantic_reasons)
    assert any(
        "Source text appears structured, but generated section/subsection coverage is too low." in reason
        for reason in result.semantic_reasons
    )


def test_ai_service_accepts_heading_preservation_via_subject_titles():
    service = AIService(client=_StubClient([_subject_heading_preserving_json()]))
    result = service.generate_project_draft(_heading_rich_source_en(), max_attempts=1, _force_single_shot=True)
    assert result.ok is True
    assert result.failure_class is None
    assert result.semantic_reasons == []


def test_ai_service_flags_trivial_math_degradation_for_rich_formula_source():
    client = _StubClient(
        [
            """
            {
              "project": {
                "meta": {"title": "Math"},
                "subjects": [
                  {
                    "title": "Recurrence",
                    "blocks": [
                      {"type": "math_block", "value": "x"}
                    ]
                  }
                ]
              }
            }
            """
        ]
    )
    service = AIService(client=client)
    source = "T(n)=aT(n/b)+f(n)"

    result = service.generate_project_draft(source, max_attempts=1, _force_single_shot=True)
    assert result.ok is False
    assert result.failure_class == "semantic"
    assert any("Displayed equations appear degraded to trivial placeholders." in reason for reason in result.semantic_reasons)


def test_ai_service_does_not_flag_math_degradation_when_equation_is_preserved():
    client = _StubClient(
        [
            """
            {
              "project": {
                "meta": {"title": "Math"},
                "subjects": [
                  {
                    "title": "Recurrence",
                    "blocks": [
                      {"type": "math_block", "value": "T(n)=aT(n/b)+f(n)"}
                    ]
                  }
                ]
              }
            }
            """
        ]
    )
    service = AIService(client=client)
    source = "T(n)=aT(n/b)+f(n)"

    result = service.generate_project_draft(source, max_attempts=1, _force_single_shot=True)
    assert result.ok is True


def test_ai_service_retries_with_semantic_prompt_and_recovers():
    client = _StubClient([_valid_minimal_project_json(), _valid_rich_project_json()])
    service = AIService(client=client)

    result = service.generate_project_draft(_long_structured_source())
    assert result.ok is True
    assert result.attempts == 2
    assert result.correction_applied is True
    assert any("semantically incomplete" in prompt for prompt in client.prompts[1:])


def test_ai_service_semantic_retry_prompt_targets_heading_structure_loss():
    client = _StubClient([_understructured_paragraph_only_json(), _heading_preserving_json()])
    service = AIService(client=client)

    result = service.generate_project_draft(_heading_rich_source())
    assert result.ok is True
    assert result.attempts == 2
    retry_prompt = client.prompts[1]
    assert "lost heading structure" in retry_prompt
    assert "Heading-like source lines should generally become section/subsection blocks." in retry_prompt
    assert "Do not collapse heading lines into plain paragraph text unless absolutely necessary." in retry_prompt


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


def test_ai_service_emits_attempt_progress_and_retry_events():
    client = _StubClient(["not-json", _valid_rich_project_json()])
    service = AIService(client=client)
    events: list[dict[str, Any]] = []

    result = service.generate_project_draft("Any source text", progress_callback=events.append)

    assert result.ok is True
    attempt_events = [e for e in events if e.get("event") == "attempt"]
    retry_events = [e for e in events if e.get("event") == "retry"]
    assert len(attempt_events) >= 2
    assert retry_events
    assert retry_events[0].get("failure_class") == "technical"


def test_ai_service_timeout_failure_is_technical():
    class _TimeoutClient:
        def generate_json_draft(self, raw_text: str, prompt: str) -> str:
            raise TimeoutError("request timed out")

    service = AIService(client=_TimeoutClient())
    result = service.generate_project_draft("Source text", max_attempts=1)
    assert result.ok is False
    assert result.failure_class == "technical"
    assert result.stage == "provider"
    assert result.validation_report is not None
    assert result.validation_report.errors
    assert result.validation_report.errors[0].code == "ai.provider.timeout"


def test_ai_service_can_cancel_before_retry_attempt():
    client = _StubClient(["not-json", _valid_rich_project_json()])
    service = AIService(client=client)
    cancel_event = threading.Event()

    def _progress(payload: dict[str, Any]) -> None:
        if payload.get("event") == "retry":
            cancel_event.set()

    result = service.generate_project_draft(
        "Any source text",
        progress_callback=_progress,
        cancel_event=cancel_event,
    )

    assert result.ok is False
    assert result.canceled is True
    assert result.stage == "cancelled"


def _very_long_chunkable_source() -> str:
    section_paragraph = (
        "This section includes detailed explanation, examples, and notes about implementation behavior. "
        "It is intentionally long to trigger chunking while preserving visible heading boundaries."
    )
    lines: list[str] = []
    for i in range(1, 9):
        lines.append(f"{i}. Section {i}")
        lines.append((section_paragraph + " ") * 6)
    return "\n".join(lines)


def test_ai_service_successful_chunked_generation_flow():
    source = _very_long_chunkable_source()
    chunks = chunk_text(source)
    assert len(chunks) > 1
    client = _HeadingAwareChunkClient()
    service = AIService(client=client)

    result = service.generate_project_draft(source, max_attempts=1)
    assert result.ok is True
    assert result.chunked_mode is True
    assert result.total_chunks == len(chunks)
    assert result.completed_chunks == len(chunks)
    assert result.merge_performed is True
    assert result.validation_report is not None and result.validation_report.ok is True
    assert result.sanitized_payload is not None
    assert len(result.sanitized_payload["project"]["subjects"]) >= len(chunks)
    assert any("processing chunk 1 of" in prompt.lower() for prompt in client.prompts)


def test_ai_service_chunk_failure_propagates_with_index():
    source = _very_long_chunkable_source()
    chunks = chunk_text(source)
    assert len(chunks) > 1
    service = AIService(client=_HeadingAwareChunkClient(fail_on_call=2))

    result = service.generate_project_draft(source, max_attempts=1)
    assert result.ok is False
    assert result.chunked_mode is True
    assert result.stage == "chunk_generation"
    assert result.failed_chunk_indices
    assert result.failed_chunk_indices[0] == 2
    assert result.completed_chunks == 1


def test_ai_service_chunked_mode_improves_over_single_shot_sparse_failure():
    source = _very_long_chunkable_source()

    single_shot_client = _StubClient([_valid_minimal_project_json()])
    single_shot_service = AIService(client=single_shot_client)
    single_result = single_shot_service.generate_project_draft(
        source,
        max_attempts=1,
        _force_single_shot=True,
    )
    assert single_result.ok is False
    assert single_result.failure_class == "semantic"

    chunks = chunk_text(source)
    chunked_client = _HeadingAwareChunkClient()
    chunked_service = AIService(client=chunked_client)
    chunked_result = chunked_service.generate_project_draft(source, max_attempts=1)

    assert chunked_result.ok is True
    assert chunked_result.chunked_mode is True
    assert chunked_result.total_chunks == len(chunks)
