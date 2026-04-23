from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .defaults import generate_safe_id, make_safe_identifier


@dataclass(frozen=True)
class MergeSummary:
    total_chunks: int
    merged_subjects: int
    skipped_chunk_indices: list[int]


def merge_chunk_projects(
    chunk_payloads: list[dict[str, Any]],
    *,
    title_hint: str | None = None,
    author_hint: str | None = None,
) -> tuple[dict[str, Any], MergeSummary]:
    if not chunk_payloads:
        raise ValueError("No chunk payloads to merge.")

    first_project = _project_from_payload(chunk_payloads[0])
    if first_project is None:
        raise ValueError("First chunk payload does not contain a valid project object.")

    meta = deepcopy(first_project.get("meta", {}))
    theme = deepcopy(first_project.get("theme", {}))

    if title_hint and title_hint.strip():
        meta["title"] = title_hint.strip()
    if author_hint and author_hint.strip():
        meta["author"] = author_hint.strip()
    if isinstance(meta.get("id"), str):
        meta["id"] = make_safe_identifier(meta["id"], fallback_prefix="project")

    merged_subjects: list[dict[str, Any]] = []
    used_subject_ids: set[str] = set()
    used_block_ids: set[str] = set()
    skipped_chunk_indices: list[int] = []

    for idx, payload in enumerate(chunk_payloads, start=1):
        project = _project_from_payload(payload)
        if project is None:
            skipped_chunk_indices.append(idx)
            continue
        subjects = project.get("subjects")
        if not isinstance(subjects, list) or not subjects:
            skipped_chunk_indices.append(idx)
            continue

        before_count = len(merged_subjects)
        for subject in subjects:
            merged = _merge_subject(subject, used_subject_ids=used_subject_ids, used_block_ids=used_block_ids)
            if merged is not None:
                merged_subjects.append(merged)
        if len(merged_subjects) == before_count:
            skipped_chunk_indices.append(idx)

    if not merged_subjects:
        raise ValueError("Merged output has no usable subjects.")

    merged_payload = {
        "project": {
            "meta": meta,
            "theme": theme,
            "subjects": merged_subjects,
        }
    }
    summary = MergeSummary(
        total_chunks=len(chunk_payloads),
        merged_subjects=len(merged_subjects),
        skipped_chunk_indices=skipped_chunk_indices,
    )
    return merged_payload, summary


def _project_from_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    project = payload.get("project")
    if isinstance(project, dict):
        return project
    return None


def _merge_subject(
    subject: Any,
    *,
    used_subject_ids: set[str],
    used_block_ids: set[str],
) -> dict[str, Any] | None:
    if not isinstance(subject, dict):
        return None

    title = str(subject.get("title") or "Subject").strip() or "Subject"
    subject_seed = subject.get("id") or title
    subject_id = generate_safe_id("subject", used_subject_ids, seed=str(subject_seed))

    blocks_in = subject.get("blocks")
    if not isinstance(blocks_in, list):
        return None

    blocks_out: list[dict[str, Any]] = []
    for block in blocks_in:
        if not isinstance(block, dict):
            continue
        block_type = str(block.get("type") or "block")
        prefix = make_safe_identifier(block_type, fallback_prefix="block")
        block_seed = block.get("id") or f"{prefix}_{len(used_block_ids)+1}"
        block_out = deepcopy(block)
        block_out["id"] = generate_safe_id(prefix, used_block_ids, seed=str(block_seed))
        blocks_out.append(block_out)

    if not blocks_out:
        return None

    subject_out = {
        "id": subject_id,
        "title": title,
        "blocks": blocks_out,
    }
    description = subject.get("description")
    if isinstance(description, str) and description.strip():
        subject_out["description"] = description.strip()
    return subject_out
