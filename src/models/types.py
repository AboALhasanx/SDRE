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

