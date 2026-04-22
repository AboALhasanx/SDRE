from __future__ import annotations

from typing import Annotated, Literal

from pydantic import StringConstraints

Identifier = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z][A-Za-z0-9_-]*$",
    ),
]

LangTag = Annotated[
    str,
    StringConstraints(
        min_length=2,
        max_length=35,
        pattern=r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$",
    ),
]

Direction = Literal["ltr", "rtl"]

ColorHex = Annotated[
    str,
    StringConstraints(pattern=r"^#([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$"),
]

# RFC3339-ish datetime string for JSON source-of-truth.
# Example: 2026-04-22T10:00:00Z or 2026-04-22T10:00:00+03:00
DateTimeStr = Annotated[
    str,
    StringConstraints(
        min_length=20,
        max_length=40,
        pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$",
    ),
]
