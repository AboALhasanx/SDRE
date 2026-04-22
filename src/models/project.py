from __future__ import annotations

from pydantic import Field, model_validator

from ._base import SDREModel
from .blocks import Block
from .meta import Meta
from .subject import Subject
from .theme import Theme
from .types import Identifier


class Project(SDREModel):
    meta: Meta
    theme: Theme
    subjects: list[Subject] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_references(self) -> "Project":
        # Enforce unique subject ids (subjects are a list by design).
        seen_subjects: set[str] = set()
        dup_subjects: set[str] = set()
        for s in self.subjects:
            if s.id in seen_subjects:
                dup_subjects.add(s.id)
            seen_subjects.add(s.id)
        if dup_subjects:
            dup_list = ", ".join(sorted(dup_subjects))
            raise ValueError(f"Duplicate subject id(s): {dup_list}")

        # Enforce unique block ids within each subject (form-based UI & reordering safety).
        for s in self.subjects:
            seen_blocks: set[str] = set()
            dup_blocks: set[str] = set()
            for b in s.blocks:
                if b.id in seen_blocks:
                    dup_blocks.add(b.id)
                seen_blocks.add(b.id)
            if dup_blocks:
                dup_list = ", ".join(sorted(dup_blocks))
                raise ValueError(f"Duplicate block id(s) in subject '{s.id}': {dup_list}")

        return self


class ProjectFile(SDREModel):
    """JSON root wrapper.

    Required root shape:
    {
      "project": { ... }
    }
    """

    project: Project
