from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from src.validation.engine import ValidationReport, validate_project_data
from src.validation.errors import ErrorItem

from .chunker import TextChunk, chunk_text
from .client import AIClient, create_default_client
from .merger import merge_chunk_projects
from .prompt_builder import (
    build_chunk_generation_prompt,
    build_generation_prompt,
    build_semantic_retry_prompt,
    build_technical_correction_prompt,
)
from .schema_adapter import sanitize_project_draft


class FailureClass(str, Enum):
    TECHNICAL = "technical"
    SEMANTIC = "semantic"


class AttemptMode(str, Enum):
    INITIAL = "initial"
    TECHNICAL_CORRECTION = "technical_correction"
    SEMANTIC_RETRY = "semantic_retry"


@dataclass
class SemanticAssessment:
    ok: bool
    score: float
    reasons: list[str]
    heading_under_preserved: bool = False
    source_heading_count: int = 0
    generated_heading_count: int = 0
    heading_coverage_ratio: float = 1.0


@dataclass
class LocalizedBlockTarget:
    path: str
    subject_index: int
    block_index: int
    fragment_json: dict[str, Any]


@dataclass(frozen=True)
class ChunkContext:
    chunk_index: int
    total_chunks: int
    heading_hint: str | None = None


@dataclass
class AIGenerationResult:
    ok: bool
    stage: str
    message: str
    raw_output: str = ""
    parsed_draft: dict[str, Any] | None = None
    sanitized_payload: dict[str, Any] | None = None
    validation_report: ValidationReport | None = None
    attempts: int = 1
    failure_class: str | None = None
    correction_applied: bool = False
    max_retries_exceeded: bool = False
    semantic_ok: bool | None = None
    semantic_score: float | None = None
    semantic_reasons: list[str] = field(default_factory=list)
    canceled: bool = False
    chunked_mode: bool = False
    total_chunks: int = 0
    completed_chunks: int = 0
    failed_chunk_indices: list[int] = field(default_factory=list)
    merge_performed: bool = False
    chunk_statuses: list[dict[str, Any]] = field(default_factory=list)


class AIService:
    MAX_ATTEMPTS = 3

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
        max_attempts: int | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        cancel_event: Any | None = None,
        _force_single_shot: bool = False,
        _chunk_context: ChunkContext | None = None,
    ) -> AIGenerationResult:
        source = raw_text.strip()
        if not source:
            report = _error_report(stage="input", code="ai.input.empty", message="Raw text input is empty.")
            return AIGenerationResult(
                ok=False,
                stage="input",
                message="Raw text input is empty.",
                validation_report=report,
                attempts=1,
                failure_class=FailureClass.TECHNICAL.value,
                semantic_ok=False,
            )

        if not _force_single_shot:
            chunks = chunk_text(source)
            if len(chunks) > 1:
                return self._generate_chunked_project_draft(
                    source=source,
                    chunks=chunks,
                    title_hint=title_hint,
                    author_hint=author_hint,
                    max_attempts=max_attempts,
                    progress_callback=progress_callback,
                    cancel_event=cancel_event,
                )

        attempt_limit = max(1, min(max_attempts or self.MAX_ATTEMPTS, self.MAX_ATTEMPTS))
        mode = AttemptMode.INITIAL
        attempts = 0
        correction_applied = False

        last_raw_output = ""
        last_parsed: dict[str, Any] | None = None
        last_sanitized: dict[str, Any] | None = None
        last_report: ValidationReport | None = None
        last_message = ""
        last_failure_class: FailureClass | None = None
        last_semantic = SemanticAssessment(ok=True, score=100.0, reasons=[])

        technical_errors: list[dict[str, str]] = []
        technical_previous_json: dict[str, Any] | None = None
        local_target: LocalizedBlockTarget | None = None
        semantic_reasons: list[str] = []
        semantic_heading_under_preserved = False

        while attempts < attempt_limit:
            if _is_cancelled(cancel_event):
                return AIGenerationResult(
                    ok=False,
                    stage="cancelled",
                    message="AI draft generation was cancelled.",
                    attempts=max(1, attempts),
                    canceled=True,
                )

            attempts += 1
            _emit_progress(
                progress_callback,
                {
                    "event": "attempt",
                    "attempt": attempts,
                    "max_attempts": attempt_limit,
                    "mode": mode.value,
                    "retrying": attempts > 1,
                },
            )

            prompt = self._build_attempt_prompt(
                mode=mode,
                source=source,
                title_hint=title_hint,
                author_hint=author_hint,
                technical_errors=technical_errors,
                technical_previous_json=technical_previous_json,
                local_target=local_target,
                semantic_reasons=semantic_reasons,
                semantic_heading_under_preserved=semantic_heading_under_preserved,
                chunk_context=_chunk_context,
                last_sanitized=last_sanitized,
                last_parsed=last_parsed,
            )

            try:
                raw_output = self.client.generate_json_draft(source, prompt)
            except Exception as exc:
                last_failure_class = FailureClass.TECHNICAL
                if _is_timeout_error(exc):
                    last_message = "AI provider request timed out."
                    last_report = _error_report(stage="provider", code="ai.provider.timeout", message=str(exc))
                else:
                    last_message = "AI provider request failed."
                    last_report = _error_report(stage="provider", code="ai.provider.failed", message=str(exc))
                technical_errors = _report_errors(last_report)
                technical_previous_json = last_sanitized or last_parsed
                local_target = None
                if attempts < attempt_limit:
                    _emit_progress(
                        progress_callback,
                        {
                            "event": "retry",
                            "next_attempt": attempts + 1,
                            "failure_class": FailureClass.TECHNICAL.value,
                            "reason": last_message,
                        },
                    )
                    mode = AttemptMode.TECHNICAL_CORRECTION
                    correction_applied = True
                    continue
                break

            last_raw_output = raw_output
            if _is_cancelled(cancel_event):
                return AIGenerationResult(
                    ok=False,
                    stage="cancelled",
                    message="AI draft generation was cancelled.",
                    raw_output=last_raw_output,
                    attempts=attempts,
                    canceled=True,
                )

            parsed, parse_error = _parse_model_output(raw_output)
            if parse_error is not None:
                last_failure_class = FailureClass.TECHNICAL
                last_message = "AI output is not valid JSON."
                last_report = _error_report(stage="parse", code="ai.parse.failed", message=parse_error)
                technical_errors = _report_errors(last_report)
                technical_previous_json = last_sanitized or last_parsed
                local_target = None
                if attempts < attempt_limit:
                    _emit_progress(
                        progress_callback,
                        {
                            "event": "retry",
                            "next_attempt": attempts + 1,
                            "failure_class": FailureClass.TECHNICAL.value,
                            "reason": "JSON parse failure",
                        },
                    )
                    mode = AttemptMode.TECHNICAL_CORRECTION
                    correction_applied = True
                    continue
                break

            adapted_input: dict[str, Any] = parsed
            if mode == AttemptMode.TECHNICAL_CORRECTION and local_target is not None and "project" not in parsed:
                patched = _patch_localized_fragment(last_sanitized, local_target, parsed)
                if patched is not None:
                    adapted_input = patched
            last_parsed = parsed
            if _is_cancelled(cancel_event):
                return AIGenerationResult(
                    ok=False,
                    stage="cancelled",
                    message="AI draft generation was cancelled.",
                    raw_output=last_raw_output,
                    parsed_draft=last_parsed,
                    attempts=attempts,
                    canceled=True,
                )

            try:
                sanitized = self._adapter(adapted_input, title_hint=title_hint, author_hint=author_hint)
            except Exception as exc:
                last_failure_class = FailureClass.TECHNICAL
                last_message = "Sanitizer failed to normalize AI output."
                last_report = _error_report(stage="sanitize", code="ai.sanitize.failed", message=str(exc))
                technical_errors = _report_errors(last_report)
                technical_previous_json = adapted_input
                local_target = None
                if attempts < attempt_limit:
                    _emit_progress(
                        progress_callback,
                        {
                            "event": "retry",
                            "next_attempt": attempts + 1,
                            "failure_class": FailureClass.TECHNICAL.value,
                            "reason": "Sanitizer failure",
                        },
                    )
                    mode = AttemptMode.TECHNICAL_CORRECTION
                    correction_applied = True
                    continue
                break

            last_sanitized = sanitized
            if _is_cancelled(cancel_event):
                return AIGenerationResult(
                    ok=False,
                    stage="cancelled",
                    message="AI draft generation was cancelled.",
                    raw_output=last_raw_output,
                    parsed_draft=last_parsed,
                    sanitized_payload=last_sanitized,
                    attempts=attempts,
                    canceled=True,
                )
            report = self._validator(sanitized, file_label="<ai-sanitized>")
            if not report.ok:
                last_failure_class = FailureClass.TECHNICAL
                last_message = "Sanitized AI draft failed strict validation."
                last_report = report
                technical_errors = _report_errors(report)
                technical_previous_json = sanitized
                local_target = _detect_localized_block_target(report, sanitized)
                if attempts < attempt_limit:
                    _emit_progress(
                        progress_callback,
                        {
                            "event": "retry",
                            "next_attempt": attempts + 1,
                            "failure_class": FailureClass.TECHNICAL.value,
                            "reason": "Validation failure",
                            "localized": local_target is not None,
                        },
                    )
                    mode = AttemptMode.TECHNICAL_CORRECTION
                    correction_applied = True
                    continue
                break

            semantic = _assess_semantic_completeness(source, sanitized)
            last_semantic = semantic
            if not semantic.ok:
                last_failure_class = FailureClass.SEMANTIC
                last_message = "AI draft is valid but semantically incomplete."
                last_report = _error_report(
                    stage="semantic",
                    code="ai.semantic.incomplete",
                    message="; ".join(semantic.reasons) if semantic.reasons else "Semantically incomplete output.",
                )
                semantic_reasons = semantic.reasons
                semantic_heading_under_preserved = semantic.heading_under_preserved
                if attempts < attempt_limit:
                    _emit_progress(
                        progress_callback,
                        {
                            "event": "retry",
                            "next_attempt": attempts + 1,
                            "failure_class": FailureClass.SEMANTIC.value,
                            "reason": semantic.reasons[0] if semantic.reasons else "Semantic completeness failure",
                            "heading_under_preserved": semantic.heading_under_preserved,
                        },
                    )
                    mode = AttemptMode.SEMANTIC_RETRY
                    correction_applied = True
                    continue
                break

            message = "AI draft generated and validated."
            if attempts > 1:
                message = f"AI draft generated and validated after {attempts} attempts."
            return AIGenerationResult(
                ok=True,
                stage="ok",
                message=message,
                raw_output=raw_output,
                parsed_draft=parsed,
                sanitized_payload=sanitized,
                validation_report=report,
                attempts=attempts,
                failure_class=None,
                correction_applied=attempts > 1,
                max_retries_exceeded=False,
                semantic_ok=True,
                semantic_score=semantic.score,
                semantic_reasons=semantic.reasons,
            )

        failed_stage = last_report.stage if last_report is not None else "failed"
        failure_class_value = last_failure_class.value if last_failure_class is not None else FailureClass.TECHNICAL.value
        maxed = attempts >= attempt_limit
        if last_failure_class == FailureClass.SEMANTIC and maxed:
            failure_message = "Semantic completeness failed after maximum retries."
        elif last_failure_class == FailureClass.TECHNICAL and maxed:
            failure_message = "Technical generation/validation failed after maximum retries."
        else:
            failure_message = last_message or "AI generation failed."

        return AIGenerationResult(
            ok=False,
            stage=failed_stage,
            message=failure_message,
            raw_output=last_raw_output,
            parsed_draft=last_parsed,
            sanitized_payload=last_sanitized,
            validation_report=last_report,
            attempts=attempts or 1,
            failure_class=failure_class_value,
            correction_applied=correction_applied,
            max_retries_exceeded=maxed,
            semantic_ok=last_semantic.ok if last_failure_class == FailureClass.SEMANTIC else None,
            semantic_score=last_semantic.score if last_failure_class == FailureClass.SEMANTIC else None,
            semantic_reasons=last_semantic.reasons if last_failure_class == FailureClass.SEMANTIC else [],
        )

    def _generate_chunked_project_draft(
        self,
        *,
        source: str,
        chunks: list[TextChunk],
        title_hint: str | None,
        author_hint: str | None,
        max_attempts: int | None,
        progress_callback: Callable[[dict[str, Any]], None] | None,
        cancel_event: Any | None,
    ) -> AIGenerationResult:
        total_chunks = len(chunks)
        chunk_statuses: list[dict[str, Any]] = []
        failed_chunk_indices: list[int] = []
        completed_chunks = 0
        total_attempts = 0
        merged_inputs: list[dict[str, Any]] = []

        _emit_progress(
            progress_callback,
            {
                "event": "chunk_mode",
                "chunked_mode": True,
                "total_chunks": total_chunks,
            },
        )

        for chunk in chunks:
            if _is_cancelled(cancel_event):
                return AIGenerationResult(
                    ok=False,
                    stage="cancelled",
                    message="AI draft generation was cancelled.",
                    attempts=max(1, total_attempts),
                    canceled=True,
                    chunked_mode=True,
                    total_chunks=total_chunks,
                    completed_chunks=completed_chunks,
                    failed_chunk_indices=failed_chunk_indices,
                    merge_performed=False,
                    chunk_statuses=chunk_statuses,
                )

            _emit_progress(
                progress_callback,
                {
                    "event": "chunk_start",
                    "chunk_index": chunk.index,
                    "total_chunks": total_chunks,
                    "chunk_chars": chunk.char_count,
                },
            )

            def _chunk_progress(payload: dict[str, Any]) -> None:
                merged = dict(payload)
                merged["chunk_index"] = chunk.index
                merged["total_chunks"] = total_chunks
                _emit_progress(progress_callback, merged)

            chunk_result = self.generate_project_draft(
                chunk.text,
                title_hint=title_hint,
                author_hint=author_hint,
                max_attempts=max_attempts,
                progress_callback=_chunk_progress,
                cancel_event=cancel_event,
                _force_single_shot=True,
                _chunk_context=ChunkContext(
                    chunk_index=chunk.index,
                    total_chunks=total_chunks,
                    heading_hint=chunk.heading_hint,
                ),
            )
            total_attempts += max(1, chunk_result.attempts)
            chunk_statuses.append(
                {
                    "chunk_index": chunk.index,
                    "ok": chunk_result.ok,
                    "stage": chunk_result.stage,
                    "attempts": chunk_result.attempts,
                    "failure_class": chunk_result.failure_class,
                    "message": chunk_result.message,
                }
            )

            if chunk_result.ok and chunk_result.sanitized_payload is not None:
                completed_chunks += 1
                merged_inputs.append(chunk_result.sanitized_payload)
                _emit_progress(
                    progress_callback,
                    {
                        "event": "chunk_done",
                        "chunk_index": chunk.index,
                        "total_chunks": total_chunks,
                        "completed_chunks": completed_chunks,
                    },
                )
                continue

            failed_chunk_indices.append(chunk.index)
            _emit_progress(
                progress_callback,
                {
                    "event": "chunk_failed",
                    "chunk_index": chunk.index,
                    "total_chunks": total_chunks,
                    "stage": chunk_result.stage,
                    "failure_class": chunk_result.failure_class,
                },
            )
            return AIGenerationResult(
                ok=False,
                stage="chunk_generation",
                message=f"Chunk {chunk.index}/{total_chunks} failed: {chunk_result.message}",
                raw_output=chunk_result.raw_output,
                parsed_draft=chunk_result.parsed_draft,
                sanitized_payload=chunk_result.sanitized_payload,
                validation_report=chunk_result.validation_report,
                attempts=total_attempts,
                failure_class=chunk_result.failure_class or FailureClass.TECHNICAL.value,
                correction_applied=any(s.get("attempts", 1) > 1 for s in chunk_statuses),
                max_retries_exceeded=chunk_result.max_retries_exceeded,
                semantic_ok=chunk_result.semantic_ok,
                semantic_score=chunk_result.semantic_score,
                semantic_reasons=chunk_result.semantic_reasons,
                canceled=chunk_result.canceled,
                chunked_mode=True,
                total_chunks=total_chunks,
                completed_chunks=completed_chunks,
                failed_chunk_indices=failed_chunk_indices,
                merge_performed=False,
                chunk_statuses=chunk_statuses,
            )

        try:
            merged_payload, merge_summary = merge_chunk_projects(
                merged_inputs,
                title_hint=title_hint,
                author_hint=author_hint,
            )
        except Exception as exc:
            report = _error_report(stage="merge", code="ai.chunk.merge_failed", message=str(exc))
            return AIGenerationResult(
                ok=False,
                stage="merge",
                message=f"Chunk merge failed: {exc}",
                validation_report=report,
                attempts=total_attempts or 1,
                failure_class=FailureClass.TECHNICAL.value,
                chunked_mode=True,
                total_chunks=total_chunks,
                completed_chunks=completed_chunks,
                failed_chunk_indices=failed_chunk_indices,
                merge_performed=False,
                chunk_statuses=chunk_statuses,
            )

        report = self._validator(merged_payload, file_label="<ai-merged>")
        if not report.ok:
            return AIGenerationResult(
                ok=False,
                stage="merge_validation",
                message="Merged chunk output failed strict validation.",
                sanitized_payload=merged_payload,
                validation_report=report,
                attempts=total_attempts or 1,
                failure_class=FailureClass.TECHNICAL.value,
                chunked_mode=True,
                total_chunks=total_chunks,
                completed_chunks=completed_chunks,
                failed_chunk_indices=failed_chunk_indices,
                merge_performed=True,
                chunk_statuses=chunk_statuses,
            )

        semantic = _assess_semantic_completeness(source, merged_payload)
        if not semantic.ok:
            semantic_report = _error_report(
                stage="semantic",
                code="ai.semantic.incomplete",
                message="; ".join(semantic.reasons) if semantic.reasons else "Semantically incomplete output.",
            )
            return AIGenerationResult(
                ok=False,
                stage="semantic",
                message="Merged chunk output is still semantically incomplete.",
                sanitized_payload=merged_payload,
                validation_report=semantic_report,
                attempts=total_attempts or 1,
                failure_class=FailureClass.SEMANTIC.value,
                semantic_ok=False,
                semantic_score=semantic.score,
                semantic_reasons=semantic.reasons,
                chunked_mode=True,
                total_chunks=total_chunks,
                completed_chunks=completed_chunks,
                failed_chunk_indices=failed_chunk_indices,
                merge_performed=True,
                chunk_statuses=chunk_statuses,
            )

        return AIGenerationResult(
            ok=True,
            stage="ok",
            message=f"AI draft generated and validated in chunked mode ({total_chunks} chunks).",
            raw_output=json.dumps(merged_payload, ensure_ascii=False),
            parsed_draft=merged_payload,
            sanitized_payload=merged_payload,
            validation_report=report,
            attempts=total_attempts or 1,
            correction_applied=any(s.get("attempts", 1) > 1 for s in chunk_statuses),
            semantic_ok=True,
            semantic_score=semantic.score,
            semantic_reasons=semantic.reasons,
            chunked_mode=True,
            total_chunks=total_chunks,
            completed_chunks=completed_chunks,
            failed_chunk_indices=failed_chunk_indices,
            merge_performed=True,
            chunk_statuses=chunk_statuses
            + [
                {
                    "merge_summary": {
                        "total_chunks": merge_summary.total_chunks,
                        "merged_subjects": merge_summary.merged_subjects,
                        "skipped_chunk_indices": merge_summary.skipped_chunk_indices,
                    }
                }
            ],
        )

    @staticmethod
    def _build_attempt_prompt(
        *,
        mode: AttemptMode,
        source: str,
        title_hint: str | None,
        author_hint: str | None,
        technical_errors: list[dict[str, str]],
        technical_previous_json: dict[str, Any] | None,
        local_target: LocalizedBlockTarget | None,
        semantic_reasons: list[str],
        semantic_heading_under_preserved: bool,
        chunk_context: ChunkContext | None,
        last_sanitized: dict[str, Any] | None,
        last_parsed: dict[str, Any] | None,
    ) -> str:
        if mode == AttemptMode.INITIAL:
            if chunk_context is not None:
                return build_chunk_generation_prompt(
                    chunk_index=chunk_context.chunk_index,
                    total_chunks=chunk_context.total_chunks,
                    chunk_heading_hint=chunk_context.heading_hint,
                    title_hint=title_hint,
                    author_hint=author_hint,
                )
            return build_generation_prompt(title_hint=title_hint, author_hint=author_hint)

        if mode == AttemptMode.TECHNICAL_CORRECTION:
            return build_technical_correction_prompt(
                raw_text=source,
                errors=technical_errors,
                previous_json=technical_previous_json,
                fragment_json=local_target.fragment_json if local_target is not None else None,
                fragment_path=local_target.path if local_target is not None else None,
                title_hint=title_hint,
                author_hint=author_hint,
            )

        return build_semantic_retry_prompt(
            raw_text=source,
            semantic_reasons=semantic_reasons,
            previous_json=last_sanitized or last_parsed,
            title_hint=title_hint,
            author_hint=author_hint,
            heading_under_preserved=semantic_heading_under_preserved,
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


def _report_errors(report: ValidationReport) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for err in report.errors:
        out.append({"path": err.path, "message": err.message, "hint": err.hint})
    return out


_BLOCK_PATH_PATTERN = re.compile(r"^/project/subjects/(\d+)/blocks/(\d+)(?:/.*)?$")


def _detect_localized_block_target(report: ValidationReport, payload: dict[str, Any]) -> LocalizedBlockTarget | None:
    subjects = payload.get("project", {}).get("subjects")
    if not isinstance(subjects, list):
        return None

    for err in report.errors:
        match = _BLOCK_PATH_PATTERN.match(err.path or "")
        if not match:
            continue
        subject_index = int(match.group(1))
        block_index = int(match.group(2))
        if subject_index < 0 or subject_index >= len(subjects):
            continue
        blocks = subjects[subject_index].get("blocks")
        if not isinstance(blocks, list) or block_index < 0 or block_index >= len(blocks):
            continue
        fragment = blocks[block_index]
        if not isinstance(fragment, dict):
            continue
        return LocalizedBlockTarget(
            path=f"/project/subjects/{subject_index}/blocks/{block_index}",
            subject_index=subject_index,
            block_index=block_index,
            fragment_json=deepcopy(fragment),
        )
    return None


def _patch_localized_fragment(
    base_payload: dict[str, Any] | None,
    target: LocalizedBlockTarget,
    parsed_fragment: dict[str, Any],
) -> dict[str, Any] | None:
    if base_payload is None:
        return None
    candidate = deepcopy(base_payload)
    project = candidate.get("project")
    if not isinstance(project, dict):
        return None
    subjects = project.get("subjects")
    if not isinstance(subjects, list) or target.subject_index >= len(subjects):
        return None
    blocks = subjects[target.subject_index].get("blocks")
    if not isinstance(blocks, list) or target.block_index >= len(blocks):
        return None
    fragment = parsed_fragment.get("block") if isinstance(parsed_fragment.get("block"), dict) else parsed_fragment
    if not isinstance(fragment, dict):
        return None
    blocks[target.block_index] = fragment
    return candidate


def _assess_semantic_completeness(raw_text: str, payload: dict[str, Any]) -> SemanticAssessment:
    text = raw_text.strip()
    text_length = len(text)
    heading_candidates = _extract_heading_like_lines(text)
    heading_lines = len(heading_candidates)
    subjects = payload.get("project", {}).get("subjects", [])

    blocks = []
    for subject in subjects if isinstance(subjects, list) else []:
        subject_blocks = subject.get("blocks") if isinstance(subject, dict) else None
        if isinstance(subject_blocks, list):
            blocks.extend(subject_blocks)

    block_count = len(blocks)
    section_count = 0
    non_trivial_blocks = 0

    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        if block_type in {"section", "subsection"}:
            section_count += 1
        if _is_non_trivial_block(block):
            non_trivial_blocks += 1

    expected_blocks = _expected_block_count(text_length, heading_lines)
    reasons: list[str] = []
    score = 100.0
    heading_under_preserved = False

    if block_count < expected_blocks:
        reasons.append(f"Too few blocks for source length ({block_count} < expected {expected_blocks}).")
        score -= min(45.0, (expected_blocks - block_count) * 8.0)

    if heading_lines >= 2:
        heading_coverage_ratio = section_count / heading_lines if heading_lines else 1.0
        min_heading_blocks = max(2, min(heading_lines, 6))
        required_headings = max(2, min_heading_blocks // 2 + min_heading_blocks % 2)
        if section_count < required_headings or heading_coverage_ratio < 0.5:
            heading_under_preserved = True
            reasons.append("Explicit headings were under-preserved.")
            reasons.append("Source text appears structured, but generated section/subsection coverage is too low.")
            score -= max(18.0, min(35.0, (required_headings - section_count) * 9.0))
    else:
        heading_coverage_ratio = 1.0

    if text_length >= 1200 and block_count <= 2:
        reasons.append("Long source text collapsed into very few blocks.")
        score -= 25.0

    if text_length >= 1800 and non_trivial_blocks <= 1:
        reasons.append("Large source text produced too little substantive content.")
        score -= 20.0

    score = max(0.0, round(score, 2))
    return SemanticAssessment(
        ok=len(reasons) == 0,
        score=score,
        reasons=reasons,
        heading_under_preserved=heading_under_preserved,
        source_heading_count=heading_lines,
        generated_heading_count=section_count,
        heading_coverage_ratio=round(heading_coverage_ratio, 3),
    )


def _expected_block_count(text_length: int, heading_count: int) -> int:
    if text_length < 250:
        base = 1
    elif text_length < 800:
        base = 2
    elif text_length < 1600:
        base = 4
    elif text_length < 3200:
        base = 6
    else:
        base = 8
    if heading_count > 0:
        base = max(base, min(heading_count + 1, 10))
    return base


def _count_heading_like_lines(text: str) -> int:
    return len(_extract_heading_like_lines(text))


def _extract_heading_like_lines(text: str) -> list[str]:
    if not text:
        return []

    lines = [line.strip() for line in text.splitlines()]
    heading_lines: list[str] = []
    for index, line in enumerate(lines):
        if not line:
            continue
        if re.match(r"^#{1,6}\s+\S+", line):
            heading_lines.append(line)
            continue
        if re.match(r"^\d+[\.\)]\s+\S+", line):
            heading_lines.append(line)
            continue
        if re.match(r"^(Chapter|Section|Part)\b[:\s]", line, flags=re.IGNORECASE):
            heading_lines.append(line)
            continue
        if line.endswith(":") and len(line.split()) <= 10:
            heading_lines.append(line)
            continue
        if _looks_like_standalone_heading(line, lines, index):
            heading_lines.append(line)
            continue
        if _looks_like_bilingual_heading(line):
            heading_lines.append(line)
    return heading_lines


def _looks_like_standalone_heading(line: str, lines: list[str], index: int) -> bool:
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


def _next_non_empty_line(lines: list[str], start: int) -> str | None:
    for idx in range(start, len(lines)):
        candidate = lines[idx].strip()
        if candidate:
            return candidate
    return None


def _contains_arabic(text: str) -> bool:
    return any("\u0600" <= ch <= "\u06FF" for ch in text)


def _contains_latin(text: str) -> bool:
    return any(("a" <= ch.lower() <= "z") for ch in text)


def _is_non_trivial_block(block: dict[str, Any]) -> bool:
    block_type = block.get("type")
    if block_type in {"section", "subsection", "page_break", "horizontal_rule"}:
        return False
    if block_type == "code_block":
        value = str(block.get("value", ""))
        return len(value.strip()) >= 20 or "\n" in value
    if block_type in {"bullet_list", "numbered_list"}:
        items = block.get("items")
        return isinstance(items, list) and len(items) >= 2
    if block_type == "table":
        rows = block.get("rows")
        return isinstance(rows, list) and len(rows) >= 2
    if block_type in {"paragraph", "note", "warning"}:
        content = block.get("content")
        return _inline_text_len(content) >= 25
    if block_type in {"math_block", "image", "image_placeholder"}:
        return True
    return False


def _inline_text_len(content: Any) -> int:
    if not isinstance(content, list):
        return 0
    total = 0
    for node in content:
        if isinstance(node, dict):
            total += len(str(node.get("value", "")))
    return total


def _error_report(*, stage: str, code: str, message: str) -> ValidationReport:
    err = ErrorItem(code=code, severity="error", path="/", message=message, hint="")
    return ValidationReport(ok=False, file="<ai>", stage=stage, errors=[err])


def _emit_progress(callback: Callable[[dict[str, Any]], None] | None, payload: dict[str, Any]) -> None:
    if callback is None:
        return
    try:
        callback(payload)
    except Exception:
        return


def _is_cancelled(cancel_event: Any | None) -> bool:
    if cancel_event is None:
        return False
    is_set = getattr(cancel_event, "is_set", None)
    if callable(is_set):
        try:
            return bool(is_set())
        except Exception:
            return False
    return False


def _is_timeout_error(exc: Exception) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    return "timed out" in str(exc).lower() or "timeout" in str(exc).lower()
