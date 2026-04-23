from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable

from src.validation.engine import ValidationReport, validate_project_data
from src.validation.errors import ErrorItem

from .client import AIClient, create_default_client
from .prompt_builder import build_generation_prompt
from .schema_adapter import sanitize_project_draft


@dataclass
class AIGenerationResult:
    ok: bool
    stage: str
    message: str
    raw_output: str = ""
    parsed_draft: dict[str, Any] | None = None
    sanitized_payload: dict[str, Any] | None = None
    validation_report: ValidationReport | None = None


class AIService:
    def __init__(
        self,
        *,
        client: AIClient | None = None,
        adapter: Callable[..., dict] = sanitize_project_draft,
        validator: Callable[..., ValidationReport] = validate_project_data,
    ) -> None:
        self.client = client or create_default_client()
        self._adapter = adapter
        self._validator = validator

    def generate_project_draft(
        self,
        raw_text: str,
        *,
        title_hint: str | None = None,
        author_hint: str | None = None,
    ) -> AIGenerationResult:
        source = raw_text.strip()
        if not source:
            report = _error_report(stage="input", code="ai.input.empty", message="Raw text input is empty.")
            return AIGenerationResult(
                ok=False,
                stage="input",
                message="Raw text input is empty.",
                validation_report=report,
            )

        prompt = build_generation_prompt(title_hint=title_hint, author_hint=author_hint)

        try:
            raw_output = self.client.generate_json_draft(source, prompt)
        except Exception as e:
            report = _error_report(stage="provider", code="ai.provider.failed", message=str(e))
            return AIGenerationResult(
                ok=False,
                stage="provider",
                message="AI provider request failed.",
                validation_report=report,
            )

        parsed, parse_error = _parse_model_output(raw_output)
        if parse_error is not None:
            report = _error_report(stage="parse", code="ai.parse.failed", message=parse_error)
            return AIGenerationResult(
                ok=False,
                stage="parse",
                message="AI output is not valid JSON.",
                raw_output=raw_output,
                validation_report=report,
            )

        sanitized = self._adapter(parsed, title_hint=title_hint, author_hint=author_hint)
        report = self._validator(sanitized, file_label="<ai-sanitized>")
        if not report.ok:
            return AIGenerationResult(
                ok=False,
                stage="validate",
                message="Sanitized AI draft failed strict validation.",
                raw_output=raw_output,
                parsed_draft=parsed,
                sanitized_payload=sanitized,
                validation_report=report,
            )

        return AIGenerationResult(
            ok=True,
            stage="ok",
            message="AI draft generated and validated.",
            raw_output=raw_output,
            parsed_draft=parsed,
            sanitized_payload=sanitized,
            validation_report=report,
        )


def _parse_model_output(raw_output: str) -> tuple[dict[str, Any] | None, str | None]:
    candidates = [_extract_fenced_json(raw_output), raw_output, _extract_braced_json(raw_output)]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed, None
            return None, "Top-level JSON value must be an object."
        except json.JSONDecodeError:
            continue
    return None, "Unable to parse model output as JSON object."


def _extract_fenced_json(raw_output: str) -> str | None:
    match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", raw_output, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


def _extract_braced_json(raw_output: str) -> str | None:
    start = raw_output.find("{")
    end = raw_output.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return raw_output[start : end + 1]


def _error_report(*, stage: str, code: str, message: str) -> ValidationReport:
    err = ErrorItem(code=code, severity="error", path="/", message=message, hint="")
    return ValidationReport(ok=False, file="<ai>", stage=stage, errors=[err])
