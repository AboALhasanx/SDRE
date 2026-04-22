from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from src.models.blocks import (
    Block,
    BlockBulletList,
    BlockCodeBlock,
    BlockHorizontalRule,
    BlockImage,
    BlockImagePlaceholder,
    BlockMathBlock,
    BlockNote,
    BlockNumberedList,
    BlockPageBreak,
    BlockParagraph,
    BlockSection,
    BlockSubsection,
    BlockTable,
    BlockWarning,
    TableCell,
)
from src.models.inlines import InlineNode, InlineText

from .inline_editor import InlineEditor


class BlockForm(ctk.CTkFrame):
    def __init__(self, master, block: Block, on_change, **kwargs):
        super().__init__(master, **kwargs)
        self.block = block
        self.on_change = on_change

    def _changed(self) -> None:
        self.on_change()


class SectionForm(BlockForm):
    def __init__(self, master, block: BlockSection, on_change, **kwargs):
        super().__init__(master, block, on_change, **kwargs)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text=f"Section ({block.id})").grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 6))
        ctk.CTkLabel(self, text="title").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.title_var = ctk.StringVar(value=block.title)
        e = ctk.CTkEntry(self, textvariable=self.title_var)
        e.grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        e.bind("<KeyRelease>", lambda _e: self._apply())

    def _apply(self) -> None:
        self.block.title = self.title_var.get()
        self._changed()


class SubsectionForm(SectionForm):
    def __init__(self, master, block: BlockSubsection, on_change, **kwargs):
        super().__init__(master, block, on_change, **kwargs)
        self.winfo_children()[0].configure(text=f"Subsection ({block.id})")


class ParagraphForm(BlockForm):
    def __init__(self, master, block: BlockParagraph, on_change, **kwargs):
        super().__init__(master, block, on_change, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=f"Paragraph ({block.id})").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 6))
        self.editor = InlineEditor(self, block.content, on_change=self._changed)
        self.editor.grid(row=1, column=0, sticky="nsew")


class CodeBlockForm(BlockForm):
    def __init__(self, master, block: BlockCodeBlock, on_change, **kwargs):
        super().__init__(master, block, on_change, **kwargs)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(self, text=f"Code Block ({block.id})").grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 6))

        ctk.CTkLabel(self, text="lang").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.lang_var = ctk.StringVar(value=block.lang or "")
        lang = ctk.CTkEntry(self, textvariable=self.lang_var)
        lang.grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        lang.bind("<KeyRelease>", lambda _e: self._apply_lang())

        ctk.CTkLabel(self, text="value").grid(row=2, column=0, sticky="nw", padx=8, pady=6)
        self.text = ctk.CTkTextbox(self)
        self.text.grid(row=2, column=1, sticky="nsew", padx=8, pady=6)
        self.text.insert("1.0", block.value)
        self.text.bind("<KeyRelease>", lambda _e: self._apply_value())

    def _apply_lang(self) -> None:
        v = self.lang_var.get().strip()
        self.block.lang = v if v else None
        self._changed()

    def _apply_value(self) -> None:
        self.block.value = self.text.get("1.0", "end-1c")
        self._changed()


class MathBlockForm(BlockForm):
    def __init__(self, master, block: BlockMathBlock, on_change, **kwargs):
        super().__init__(master, block, on_change, **kwargs)
        self.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self, text=f"Math Block ({block.id})").grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 6))
        ctk.CTkLabel(self, text="value").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.var = ctk.StringVar(value=block.value)
        e = ctk.CTkEntry(self, textvariable=self.var)
        e.grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        e.bind("<KeyRelease>", lambda _e: self._apply())

    def _apply(self) -> None:
        self.block.value = self.var.get()
        self._changed()


class ImageForm(BlockForm):
    def __init__(self, master, block: BlockImage, on_change, **kwargs):
        super().__init__(master, block, on_change, **kwargs)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(self, text=f"Image ({block.id})").grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 6))
        ctk.CTkLabel(self, text="src").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.src_var = ctk.StringVar(value=block.src)
        src = ctk.CTkEntry(self, textvariable=self.src_var)
        src.grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        src.bind("<KeyRelease>", lambda _e: self._apply_src())

        ctk.CTkLabel(self, text="alt").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        self.alt_var = ctk.StringVar(value=block.alt or "")
        alt = ctk.CTkEntry(self, textvariable=self.alt_var)
        alt.grid(row=2, column=1, sticky="ew", padx=8, pady=6)
        alt.bind("<KeyRelease>", lambda _e: self._apply_alt())

        ctk.CTkLabel(self, text="caption").grid(row=3, column=0, sticky="nw", padx=8, pady=6)
        if block.caption is None:
            block.caption = [InlineText(type="text", value="")]
        self.cap = InlineEditor(self, block.caption, on_change=self._changed)
        self.cap.grid(row=3, column=1, sticky="nsew", padx=8, pady=6)

    def _apply_src(self) -> None:
        self.block.src = self.src_var.get()
        self._changed()

    def _apply_alt(self) -> None:
        v = self.alt_var.get().strip()
        self.block.alt = v if v else None
        self._changed()


class ImagePlaceholderForm(BlockForm):
    def __init__(self, master, block: BlockImagePlaceholder, on_change, **kwargs):
        super().__init__(master, block, on_change, **kwargs)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text=f"Image Placeholder ({block.id})").grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 6))

        ctk.CTkLabel(self, text="label").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.label_var = ctk.StringVar(value=block.label or "")
        label = ctk.CTkEntry(self, textvariable=self.label_var)
        label.grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        label.bind("<KeyRelease>", lambda _e: self._apply())

        self.border_var = ctk.BooleanVar(value=bool(block.border) if block.border is not None else True)
        cb = ctk.CTkCheckBox(self, text="border", variable=self.border_var, command=self._apply)
        cb.grid(row=2, column=1, sticky="w", padx=8, pady=6)

        ctk.CTkLabel(self, text="reserve_height_mm").grid(row=3, column=0, sticky="w", padx=8, pady=6)
        self.h_var = ctk.StringVar(value=str(block.reserve_height_mm or ""))
        h = ctk.CTkEntry(self, textvariable=self.h_var)
        h.grid(row=3, column=1, sticky="ew", padx=8, pady=6)
        h.bind("<KeyRelease>", lambda _e: self._apply())

        ctk.CTkLabel(self, text="aspect_ratio").grid(row=4, column=0, sticky="w", padx=8, pady=6)
        self.ar_var = ctk.StringVar(value=str(block.aspect_ratio or ""))
        ar = ctk.CTkEntry(self, textvariable=self.ar_var)
        ar.grid(row=4, column=1, sticky="ew", padx=8, pady=6)
        ar.bind("<KeyRelease>", lambda _e: self._apply())

        ctk.CTkLabel(self, text="caption").grid(row=5, column=0, sticky="nw", padx=8, pady=6)
        if block.caption is None:
            block.caption = [InlineText(type="text", value="")]
        self.cap = InlineEditor(self, block.caption, on_change=self._changed)
        self.cap.grid(row=5, column=1, sticky="nsew", padx=8, pady=6)

    def _apply(self) -> None:
        v = self.label_var.get().strip()
        self.block.label = v if v else None
        self.block.border = bool(self.border_var.get())
        # numeric fields: allow blank; keep None
        hv = self.h_var.get().strip()
        arv = self.ar_var.get().strip()
        self.block.reserve_height_mm = float(hv) if hv else None
        self.block.aspect_ratio = float(arv) if arv else None
        self._changed()


class NoteForm(BlockForm):
    def __init__(self, master, block: BlockNote, on_change, **kwargs):
        super().__init__(master, block, on_change, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=f"Note ({block.id})").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 6))
        self.editor = InlineEditor(self, block.content, on_change=self._changed)
        self.editor.grid(row=1, column=0, sticky="nsew")


class WarningForm(NoteForm):
    def __init__(self, master, block: BlockWarning, on_change, **kwargs):
        super().__init__(master, block, on_change, **kwargs)
        self.winfo_children()[0].configure(text=f"Warning ({block.id})")


class ListForm(BlockForm):
    def __init__(self, master, block: BlockBulletList | BlockNumberedList, on_change, **kwargs):
        super().__init__(master, block, on_change, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text=f"{block.type} ({block.id})").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 6))

        self.tree = ttk.Treeview(self, columns=["text"], show="headings", height=8)
        self.tree.heading("text", text="item")
        self.tree.column("text", width=480, stretch=True)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

        btns = ctk.CTkFrame(self)
        btns.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        ctk.CTkButton(btns, text="Add", width=80, command=self._add).grid(row=0, column=0, padx=(0, 6))
        ctk.CTkButton(btns, text="Edit", width=80, command=self._edit).grid(row=0, column=1, padx=(0, 6))
        ctk.CTkButton(btns, text="Delete", width=80, command=self._delete).grid(row=0, column=2, padx=(0, 6))
        ctk.CTkButton(btns, text="Up", width=60, command=lambda: self._move(-1)).grid(row=0, column=3, padx=(0, 6))
        ctk.CTkButton(btns, text="Down", width=60, command=lambda: self._move(1)).grid(row=0, column=4, padx=(0, 6))

        self._refresh()

    def _item_summary(self, nodes: list[InlineNode]) -> str:
        # A compact preview for list items.
        parts = []
        for n in nodes:
            if hasattr(n, "value"):
                parts.append(str(getattr(n, "value")))
        s = "".join(parts)
        return s[:160]

    def _refresh(self) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for i, item in enumerate(self.block.items):
            self.tree.insert("", "end", iid=str(i), values=(self._item_summary(item),))

    def _sel(self) -> int | None:
        s = self.tree.selection()
        if not s:
            return None
        return int(s[0])

    def _commit(self) -> None:
        self._refresh()
        self._changed()

    def _add(self) -> None:
        self.block.items.append([InlineText(type="text", value="")])
        self._commit()

    def _delete(self) -> None:
        i = self._sel()
        if i is None:
            return
        del self.block.items[i]
        if not self.block.items:
            self.block.items.append([InlineText(type="text", value="")])
        self._commit()

    def _move(self, delta: int) -> None:
        i = self._sel()
        if i is None:
            return
        j = i + delta
        if j < 0 or j >= len(self.block.items):
            return
        self.block.items[i], self.block.items[j] = self.block.items[j], self.block.items[i]
        self._commit()
        self.tree.selection_set(str(j))

    def _edit(self) -> None:
        i = self._sel()
        if i is None:
            return
        nodes = self.block.items[i]
        win = ctk.CTkToplevel(self)
        win.title("Edit List Item")
        win.geometry("620x340")
        win.grid_columnconfigure(0, weight=1)
        win.grid_rowconfigure(0, weight=1)
        editor = InlineEditor(win, nodes, on_change=lambda: None)
        editor.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        ctk.CTkButton(win, text="Done", command=lambda: (win.destroy(), self._commit())).grid(
            row=1, column=0, sticky="e", padx=8, pady=(0, 8)
        )
        win.grab_set()


class PageBreakForm(BlockForm):
    def __init__(self, master, block: BlockPageBreak, on_change, **kwargs):
        super().__init__(master, block, on_change, **kwargs)
        ctk.CTkLabel(self, text=f"Page Break ({block.id})").grid(row=0, column=0, sticky="w", padx=8, pady=8)
        ctk.CTkLabel(self, text="No editable fields.").grid(row=1, column=0, sticky="w", padx=8, pady=6)


class HorizontalRuleForm(BlockForm):
    def __init__(self, master, block: BlockHorizontalRule, on_change, **kwargs):
        super().__init__(master, block, on_change, **kwargs)
        ctk.CTkLabel(self, text=f"Horizontal Rule ({block.id})").grid(row=0, column=0, sticky="w", padx=8, pady=8)
        ctk.CTkLabel(self, text="No editable fields.").grid(row=1, column=0, sticky="w", padx=8, pady=6)


class TableForm(BlockForm):
    def __init__(self, master, block: BlockTable, on_change, **kwargs):
        super().__init__(master, block, on_change, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text=f"Table ({block.id})").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 6))

        # caption
        cap_frame = ctk.CTkFrame(self)
        cap_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        cap_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(cap_frame, text="caption").grid(row=0, column=0, sticky="w", padx=8, pady=8)
        if block.caption is None:
            block.caption = [InlineText(type="text", value="")]
        InlineEditor(cap_frame, block.caption, on_change=self._changed).grid(row=0, column=1, sticky="ew", padx=8, pady=8)

        # rows editor (simple, row/col counts; cell content edits via dialog)
        frame = ctk.CTkFrame(self)
        frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(frame, columns=["row", "col", "preview"], show="headings", height=10)
        for c, w in (("row", 50), ("col", 50), ("preview", 420)):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, stretch=(c == "preview"))
        self.tree.grid(row=0, column=0, sticky="nsew")
        y = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=y.set)
        y.grid(row=0, column=1, sticky="ns")

        btns = ctk.CTkFrame(self)
        btns.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 8))
        ctk.CTkButton(btns, text="Add Row", width=90, command=self._add_row).grid(row=0, column=0, padx=(0, 6))
        ctk.CTkButton(btns, text="Add Col", width=90, command=self._add_col).grid(row=0, column=1, padx=(0, 6))
        ctk.CTkButton(btns, text="Edit Cell", width=90, command=self._edit_cell).grid(row=0, column=2, padx=(0, 6))

        self._refresh()

    def _preview(self, nodes: list[InlineNode]) -> str:
        parts = []
        for n in nodes:
            if hasattr(n, "value"):
                parts.append(str(getattr(n, "value")))
        s = "".join(parts)
        return s[:140]

    def _refresh(self) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for r, row in enumerate(self.block.rows):
            for c, cell in enumerate(row):
                self.tree.insert("", "end", iid=f"{r}:{c}", values=(r, c, self._preview(cell.content)))

    def _dims(self) -> tuple[int, int]:
        rows = len(self.block.rows)
        cols = len(self.block.rows[0]) if rows else 0
        return rows, cols

    def _add_row(self) -> None:
        rows, cols = self._dims()
        new_row = [TableCell(content=[InlineText(type="text", value="")]) for _ in range(max(cols, 1))]
        self.block.rows.append(new_row)
        self._refresh()
        self._changed()

    def _add_col(self) -> None:
        rows, cols = self._dims()
        if rows == 0:
            self.block.rows = [[TableCell(content=[InlineText(type="text", value="")])]]
        else:
            for r in range(rows):
                self.block.rows[r].append(TableCell(content=[InlineText(type="text", value="")]))
        self._refresh()
        self._changed()

    def _selected_cell(self) -> tuple[int, int] | None:
        sel = self.tree.selection()
        if not sel:
            return None
        iid = sel[0]
        if ":" not in iid:
            return None
        a, b = iid.split(":", 1)
        return int(a), int(b)

    def _edit_cell(self) -> None:
        rc = self._selected_cell()
        if rc is None:
            return
        r, c = rc
        cell = self.block.rows[r][c]
        win = ctk.CTkToplevel(self)
        win.title(f"Edit Cell ({r},{c})")
        win.geometry("620x340")
        win.grid_columnconfigure(0, weight=1)
        win.grid_rowconfigure(0, weight=1)
        InlineEditor(win, cell.content, on_change=lambda: None).grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        ctk.CTkButton(win, text="Done", command=lambda: (win.destroy(), self._refresh(), self._changed())).grid(
            row=1, column=0, sticky="e", padx=8, pady=(0, 8)
        )
        win.grab_set()


def make_block_form(master, block: Block, on_change) -> BlockForm:
    if isinstance(block, BlockSection):
        return SectionForm(master, block, on_change)
    if isinstance(block, BlockSubsection):
        return SubsectionForm(master, block, on_change)
    if isinstance(block, BlockParagraph):
        return ParagraphForm(master, block, on_change)
    if isinstance(block, BlockCodeBlock):
        return CodeBlockForm(master, block, on_change)
    if isinstance(block, BlockMathBlock):
        return MathBlockForm(master, block, on_change)
    if isinstance(block, BlockTable):
        return TableForm(master, block, on_change)
    if isinstance(block, BlockImage):
        return ImageForm(master, block, on_change)
    if isinstance(block, BlockImagePlaceholder):
        return ImagePlaceholderForm(master, block, on_change)
    if isinstance(block, BlockNote):
        return NoteForm(master, block, on_change)
    if isinstance(block, BlockWarning):
        return WarningForm(master, block, on_change)
    if isinstance(block, (BlockBulletList, BlockNumberedList)):
        return ListForm(master, block, on_change)
    if isinstance(block, BlockPageBreak):
        return PageBreakForm(master, block, on_change)
    if isinstance(block, BlockHorizontalRule):
        return HorizontalRuleForm(master, block, on_change)
    return BlockForm(master, block, on_change)

