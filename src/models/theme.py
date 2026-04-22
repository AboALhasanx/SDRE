from __future__ import annotations

from typing import Literal

from pydantic import Field

from ._base import SDREModel
from .types import ColorHex


class ThemeFonts(SDREModel):
    base: str = Field(min_length=1, max_length=128)
    mono: str = Field(min_length=1, max_length=128)
    math: str | None = Field(default=None, min_length=1, max_length=128)


class ThemeSizes(SDREModel):
    base_px: float = Field(ge=6, le=72)
    line_height: float = Field(ge=1.0, le=3.0)
    h1_px: float = Field(ge=6, le=200)
    h2_px: float = Field(ge=6, le=200)
    h3_px: float = Field(ge=6, le=200)
    h4_px: float = Field(ge=6, le=200)
    h5_px: float = Field(ge=6, le=200)
    h6_px: float = Field(ge=6, le=200)


class ThemeColors(SDREModel):
    text: ColorHex
    background: ColorHex
    muted: ColorHex
    accent: ColorHex
    border: ColorHex
    code_bg: ColorHex


class PageMarginsMm(SDREModel):
    top: float = Field(ge=0, le=100)
    right: float = Field(ge=0, le=100)
    bottom: float = Field(ge=0, le=100)
    left: float = Field(ge=0, le=100)


class PageSettings(SDREModel):
    size: Literal["A4", "Letter"]
    dpi: int = Field(ge=72, le=1200)
    margin_mm: PageMarginsMm


class Theme(SDREModel):
    fonts: ThemeFonts
    sizes: ThemeSizes
    colors: ThemeColors
    page: PageSettings

