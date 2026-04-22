from __future__ import annotations

from dataclasses import dataclass
from tkinter import messagebox

import customtkinter as ctk

from src.models.theme import (
    ThemeCode,
    ThemeHeadings,
    ThemeLtrInlineStyle,
    ThemeTables,
)


@dataclass(frozen=True)
class ProjectSettingsResult:
    ok: bool
    message: str = ""


class ProjectSettingsDialog(ctk.CTkToplevel):
    def __init__(self, master, *, controller, on_applied):
        super().__init__(master)
        self.title("Project Settings")
        self.geometry("860x640")
        self.minsize(760, 560)
        self.controller = controller
        self._on_applied = on_applied

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.tabs.add("Meta")
        self.tabs.add("Theme")

        self._build_meta(self.tabs.tab("Meta"))
        self._build_theme(self.tabs.tab("Theme"))

        btns = ctk.CTkFrame(self)
        btns.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        btns.grid_columnconfigure(0, weight=1)
        btns.grid_columnconfigure(1, weight=1)
        btns.grid_columnconfigure(2, weight=1)
        ctk.CTkButton(btns, text="Close", command=self.destroy).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(btns, text="Apply", command=self._apply).grid(row=0, column=1, sticky="ew", padx=6)
        ctk.CTkButton(btns, text="Apply + Close", command=self._apply_close).grid(
            row=0, column=2, sticky="ew", padx=(6, 0)
        )

        self.grab_set()

    # ---- Meta
    def _build_meta(self, parent):
        meta = self.controller.project_file.project.meta
        parent.grid_columnconfigure(1, weight=1)

        row = 0

        def add(label, var):
            nonlocal row
            ctk.CTkLabel(parent, text=label).grid(row=row, column=0, sticky="w", padx=12, pady=6)
            e = ctk.CTkEntry(parent, textvariable=var)
            e.grid(row=row, column=1, sticky="ew", padx=12, pady=6)
            row += 1
            return e

        self.meta_id = ctk.StringVar(value=meta.id)
        self.meta_title = ctk.StringVar(value=meta.title)
        self.meta_subtitle = ctk.StringVar(value=meta.subtitle or "")
        self.meta_author = ctk.StringVar(value=meta.author)
        self.meta_language = ctk.StringVar(value=meta.language)
        self.meta_direction = ctk.StringVar(value=meta.direction)
        self.meta_version = ctk.StringVar(value=meta.version or "")
        self.meta_created_at = ctk.StringVar(value=meta.created_at or "")
        self.meta_updated_at = ctk.StringVar(value=meta.updated_at or "")

        add("id", self.meta_id)
        add("title", self.meta_title)
        add("subtitle", self.meta_subtitle)
        add("author", self.meta_author)
        add("language", self.meta_language)

        ctk.CTkLabel(parent, text="direction").grid(row=row, column=0, sticky="w", padx=12, pady=6)
        ctk.CTkOptionMenu(parent, values=["ltr", "rtl"], variable=self.meta_direction).grid(
            row=row, column=1, sticky="w", padx=12, pady=6
        )
        row += 1

        add("version", self.meta_version)
        add("created_at (RFC3339)", self.meta_created_at)
        add("updated_at (RFC3339)", self.meta_updated_at)

    # ---- Theme
    def _build_theme(self, parent):
        theme = self.controller.project_file.project.theme
        parent.grid_columnconfigure(1, weight=1)

        row = 0

        def label(text):
            nonlocal row
            ctk.CTkLabel(parent, text=text).grid(row=row, column=0, columnspan=2, sticky="w", padx=12, pady=(14, 6))
            row += 1

        def add(label_text, var):
            nonlocal row
            ctk.CTkLabel(parent, text=label_text).grid(row=row, column=0, sticky="w", padx=12, pady=6)
            e = ctk.CTkEntry(parent, textvariable=var)
            e.grid(row=row, column=1, sticky="ew", padx=12, pady=6)
            row += 1
            return e

        # Page
        label("Page")
        self.page_size = ctk.StringVar(value=theme.page.size)
        self.page_dpi = ctk.StringVar(value=str(theme.page.dpi))
        self.page_m_top = ctk.StringVar(value=str(theme.page.margin_mm.top))
        self.page_m_right = ctk.StringVar(value=str(theme.page.margin_mm.right))
        self.page_m_bottom = ctk.StringVar(value=str(theme.page.margin_mm.bottom))
        self.page_m_left = ctk.StringVar(value=str(theme.page.margin_mm.left))

        ctk.CTkLabel(parent, text="size").grid(row=row, column=0, sticky="w", padx=12, pady=6)
        ctk.CTkOptionMenu(parent, values=["A4", "Letter"], variable=self.page_size).grid(
            row=row, column=1, sticky="w", padx=12, pady=6
        )
        row += 1
        add("dpi", self.page_dpi)
        add("margin top (mm)", self.page_m_top)
        add("margin right (mm)", self.page_m_right)
        add("margin bottom (mm)", self.page_m_bottom)
        add("margin left (mm)", self.page_m_left)

        # Fonts
        label("Fonts")
        self.font_base = ctk.StringVar(value=theme.fonts.base)
        self.font_mono = ctk.StringVar(value=theme.fonts.mono)
        self.font_math = ctk.StringVar(value=theme.fonts.math or "")
        add("base", self.font_base)
        add("mono", self.font_mono)
        add("math (optional)", self.font_math)

        # Text
        label("Text")
        self.text_size = ctk.StringVar(value=str(theme.text.base_size_px if theme.text else 14))
        self.text_lh = ctk.StringVar(value=str(theme.text.line_height if theme.text else 1.6))
        add("base_size_px", self.text_size)
        add("line_height", self.text_lh)

        # Colors
        label("Colors (hex)")
        c = theme.colors
        self.c_text = ctk.StringVar(value=c.text)
        self.c_bg = ctk.StringVar(value=c.background)
        self.c_muted = ctk.StringVar(value=c.muted)
        self.c_accent = ctk.StringVar(value=c.accent)
        self.c_border = ctk.StringVar(value=c.border)
        self.c_code_bg = ctk.StringVar(value=c.code_bg)
        add("text", self.c_text)
        add("background", self.c_bg)
        add("muted", self.c_muted)
        add("accent", self.c_accent)
        add("border", self.c_border)
        add("code_bg", self.c_code_bg)

        # Optional groups (simple enable + fields)
        label("Headings (optional)")
        self.enable_headings = ctk.BooleanVar(value=theme.headings is not None)
        ctk.CTkCheckBox(parent, text="enable headings", variable=self.enable_headings).grid(
            row=row, column=1, sticky="w", padx=12, pady=6
        )
        row += 1
        h = theme.headings or ThemeHeadings()
        self.h1 = ctk.StringVar(value=str(h.h1_size_px or ""))
        self.h2 = ctk.StringVar(value=str(h.h2_size_px or ""))
        self.h3 = ctk.StringVar(value=str(h.h3_size_px or ""))
        self.h4 = ctk.StringVar(value=str(h.h4_size_px or ""))
        add("h1_size_px", self.h1)
        add("h2_size_px", self.h2)
        add("h3_size_px", self.h3)
        add("h4_size_px", self.h4)

        label("Code (optional)")
        self.enable_code = ctk.BooleanVar(value=theme.code is not None)
        ctk.CTkCheckBox(parent, text="enable code", variable=self.enable_code).grid(
            row=row, column=1, sticky="w", padx=12, pady=6
        )
        row += 1
        cd = theme.code or ThemeCode()
        self.code_font_size = ctk.StringVar(value=str(cd.font_size_px or ""))
        self.code_bg = ctk.StringVar(value=str(cd.background or ""))
        add("font_size_px", self.code_font_size)
        add("background (hex)", self.code_bg)

        label("Tables (optional)")
        self.enable_tables = ctk.BooleanVar(value=theme.tables is not None)
        ctk.CTkCheckBox(parent, text="enable tables", variable=self.enable_tables).grid(
            row=row, column=1, sticky="w", padx=12, pady=6
        )
        row += 1
        tb = theme.tables or ThemeTables()
        self.tbl_border = ctk.StringVar(value=str(tb.border_color or ""))
        self.tbl_header_bg = ctk.StringVar(value=str(tb.header_background or ""))
        add("border_color (hex)", self.tbl_border)
        add("header_background (hex)", self.tbl_header_bg)

        label("LTR Inline Style (optional)")
        self.enable_ltr_style = ctk.BooleanVar(value=theme.ltr_inline_style is not None)
        ctk.CTkCheckBox(parent, text="enable ltr_inline_style", variable=self.enable_ltr_style).grid(
            row=row, column=1, sticky="w", padx=12, pady=6
        )
        row += 1
        li = theme.ltr_inline_style or ThemeLtrInlineStyle()
        self.ltr_box_border = ctk.StringVar(value=str(li.boxed_border_color or ""))
        self.ltr_box_bg = ctk.StringVar(value=str(li.boxed_background or ""))
        self.ltr_mono_bg = ctk.StringVar(value=str(li.mono_background or ""))
        add("boxed_border_color (hex)", self.ltr_box_border)
        add("boxed_background (hex)", self.ltr_box_bg)
        add("mono_background (hex)", self.ltr_mono_bg)

    def _apply_close(self) -> None:
        res = self._apply()
        if res.ok:
            self.destroy()

    def _apply(self) -> ProjectSettingsResult:
        try:
            self._apply_meta()
            self._apply_theme()
            self.controller.mark_dirty()
            self._on_applied()
            return ProjectSettingsResult(ok=True, message="Applied")
        except Exception as e:
            messagebox.showerror("Invalid Settings", str(e))
            return ProjectSettingsResult(ok=False, message=str(e))

    def _apply_meta(self) -> None:
        meta = self.controller.project_file.project.meta
        meta.id = self.meta_id.get().strip()
        meta.title = self.meta_title.get().strip()
        meta.subtitle = self.meta_subtitle.get().strip() or None
        meta.author = self.meta_author.get().strip()
        meta.language = self.meta_language.get().strip()
        meta.direction = self.meta_direction.get().strip()
        meta.version = self.meta_version.get().strip() or None
        meta.created_at = self.meta_created_at.get().strip() or None
        meta.updated_at = self.meta_updated_at.get().strip() or None

    def _apply_theme(self) -> None:
        theme = self.controller.project_file.project.theme

        # Page
        theme.page.size = self.page_size.get()
        theme.page.dpi = int(self.page_dpi.get())
        theme.page.margin_mm.top = float(self.page_m_top.get())
        theme.page.margin_mm.right = float(self.page_m_right.get())
        theme.page.margin_mm.bottom = float(self.page_m_bottom.get())
        theme.page.margin_mm.left = float(self.page_m_left.get())

        # Fonts
        theme.fonts.base = self.font_base.get().strip()
        theme.fonts.mono = self.font_mono.get().strip()
        theme.fonts.math = self.font_math.get().strip() or None

        # Text (ensure it exists)
        if theme.text is None:
            from src.models.theme import ThemeText

            theme.text = ThemeText(base_size_px=14, line_height=1.6)
        theme.text.base_size_px = float(self.text_size.get())
        theme.text.line_height = float(self.text_lh.get())

        # Colors
        theme.colors.text = self.c_text.get().strip()
        theme.colors.background = self.c_bg.get().strip()
        theme.colors.muted = self.c_muted.get().strip()
        theme.colors.accent = self.c_accent.get().strip()
        theme.colors.border = self.c_border.get().strip()
        theme.colors.code_bg = self.c_code_bg.get().strip()

        # Headings optional
        def _maybe_float(s: str):
            s = s.strip()
            return float(s) if s else None

        if self.enable_headings.get():
            h = ThemeHeadings(
                h1_size_px=_maybe_float(self.h1.get()),
                h2_size_px=_maybe_float(self.h2.get()),
                h3_size_px=_maybe_float(self.h3.get()),
                h4_size_px=_maybe_float(self.h4.get()),
            )
            theme.headings = h if any(v is not None for v in (h.h1_size_px, h.h2_size_px, h.h3_size_px, h.h4_size_px)) else ThemeHeadings()
        else:
            theme.headings = None

        # Code optional
        if self.enable_code.get():
            cd = ThemeCode(font_size_px=_maybe_float(self.code_font_size.get()), background=self.code_bg.get().strip() or None)
            theme.code = cd if (cd.font_size_px is not None or cd.background is not None) else ThemeCode()
        else:
            theme.code = None

        # Tables optional
        if self.enable_tables.get():
            tb = ThemeTables(border_color=self.tbl_border.get().strip() or None, header_background=self.tbl_header_bg.get().strip() or None)
            theme.tables = tb if (tb.border_color is not None or tb.header_background is not None) else ThemeTables()
        else:
            theme.tables = None

        # LTR inline style optional
        if self.enable_ltr_style.get():
            li = ThemeLtrInlineStyle(
                boxed_border_color=self.ltr_box_border.get().strip() or None,
                boxed_background=self.ltr_box_bg.get().strip() or None,
                mono_background=self.ltr_mono_bg.get().strip() or None,
            )
            theme.ltr_inline_style = (
                li
                if any(v is not None for v in (li.boxed_border_color, li.boxed_background, li.mono_background))
                else ThemeLtrInlineStyle()
            )
        else:
            theme.ltr_inline_style = None

