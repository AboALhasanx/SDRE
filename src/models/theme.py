from __future__ import annotations

from typing import Literal

from pydantic import Field

from ._base import SDREModel
from .types import ColorHex


class ThemePageMarginsMm(SDREModel):
    top: float = Field(ge=0, le=100)
    right: float = Field(ge=0, le=100)
    bottom: float = Field(ge=0, le=100)
    left: float = Field(ge=0, le=100)


class ThemePage(SDREModel):
    size: Literal["A4", "Letter"]
    dpi: int = Field(ge=72, le=1200)
    margin_mm: ThemePageMarginsMm


class ThemeFonts(SDREModel):
    base: str = Field(min_length=1, max_length=128)
    mono: str = Field(min_length=1, max_length=128)
    math: str | None = Field(default=None, min_length=1, max_length=128)


class ThemeText(SDREModel):
    base_size_px: float = Field(ge=6, le=72)
    line_height: float = Field(ge=1.0, le=3.0)


class ThemeColors(SDREModel):
    text: ColorHex
    background: ColorHex
    muted: ColorHex
    accent: ColorHex
    border: ColorHex
    code_bg: ColorHex


class ThemeHeadings(SDREModel):
    h1_size_px: float | None = Field(default=None, ge=6, le=200)
    h2_size_px: float | None = Field(default=None, ge=6, le=200)
    h3_size_px: float | None = Field(default=None, ge=6, le=200)
    h4_size_px: float | None = Field(default=None, ge=6, le=200)


class ThemeCode(SDREModel):
    font_size_px: float | None = Field(default=None, ge=6, le=72)
    background: ColorHex | None = None


class ThemeTables(SDREModel):
    border_color: ColorHex | None = None
    header_background: ColorHex | None = None


class ThemeLtrInlineStyle(SDREModel):
    boxed_border_color: ColorHex | None = None
    boxed_background: ColorHex | None = None
    mono_background: ColorHex | None = None


class Theme(SDREModel):
    page: ThemePage
    fonts: ThemeFonts
    colors: ThemeColors
    text: ThemeText | None = None
    headings: ThemeHeadings | None = None
    code: ThemeCode | None = None
    tables: ThemeTables | None = None
    ltr_inline_style: ThemeLtrInlineStyle | None = None
