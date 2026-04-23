from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from src.ui.controllers.app_controller import AppController
from src.ui.forms.block_forms import make_block_form
from src.ui.forms.json_import_panel import JsonImportPanel
from src.ui.forms.project_settings import ProjectSettingsDialog
from src.ui.state import project_state as ps
from src.ui.widgets.log_panel import LogPanel


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SDRE")
        self.geometry("1200x720")
        self.minsize(980, 640)

        self.controller = AppController()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)

        self._build_menu()
        self._build_layout()
        self._refresh_all()
        self._update_title()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_menu(self) -> None:
        m = tk.Menu(self)
        self.config(menu=m)

        file_m = tk.Menu(m, tearoff=0)
        m.add_cascade(label="File", menu=file_m)
        file_m.add_command(label="New Project", command=self._new_project)
        file_m.add_command(label="Open Project...", command=self._open_project)
        file_m.add_separator()
        file_m.add_command(label="Save", command=self._save)
        file_m.add_command(label="Save As...", command=self._save_as)
        file_m.add_separator()
        file_m.add_command(label="Project Settings...", command=self._project_settings)
        file_m.add_separator()
        file_m.add_command(label="Open Output Folder", command=self._open_output_folder)
        file_m.add_command(label="Open Generated Typst", command=self._open_generated_typst)
        file_m.add_command(label="Open Preview PDF", command=self._open_preview_pdf)
        file_m.add_command(label="Open Build Report", command=self._open_build_report)
        file_m.add_separator()
        file_m.add_command(label="Exit", command=self._on_close)

        act_m = tk.Menu(m, tearoff=0)
        m.add_cascade(label="Actions", menu=act_m)
        act_m.add_command(label="Validate", command=self._validate)
        act_m.add_separator()
        act_m.add_command(label="Generate Typst Only", command=self._generate_typst_only)
        act_m.add_command(label="Build Preview", command=lambda: self._build("preview"))
        act_m.add_command(label="Build Strict", command=lambda: self._build("strict"))

    def _build_layout(self) -> None:
        # Top: three-pane layout. Bottom: logs.
        top = ctk.CTkFrame(self)
        top.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        top.grid_columnconfigure(0, weight=0)
        top.grid_columnconfigure(1, weight=0)
        top.grid_columnconfigure(2, weight=1)
        top.grid_rowconfigure(0, weight=1)

        # Subjects panel
        self.subj_panel = ctk.CTkFrame(top, width=260)
        self.subj_panel.grid(row=0, column=0, sticky="ns", padx=(0, 8))
        self.subj_panel.grid_rowconfigure(1, weight=1)
        self.subj_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.subj_panel, text="Subjects").grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        self.subjects = ttk.Treeview(self.subj_panel, columns=["title"], show="headings", height=18)
        self.subjects.heading("title", text="title")
        self.subjects.column("title", width=220, stretch=True)
        self.subjects.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.subjects.bind("<<TreeviewSelect>>", lambda _e: self._on_subject_selected())
        sy = ttk.Scrollbar(self.subj_panel, orient=tk.VERTICAL, command=self.subjects.yview)
        self.subjects.configure(yscrollcommand=sy.set)
        sy.grid(row=1, column=1, sticky="ns", pady=(0, 8))

        subj_btns = ctk.CTkFrame(self.subj_panel)
        subj_btns.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
        ctk.CTkButton(subj_btns, text="Add", width=70, command=self._add_subject).grid(row=0, column=0, padx=(0, 6))
        ctk.CTkButton(subj_btns, text="Delete", width=70, command=self._delete_subject).grid(row=0, column=1, padx=(0, 6))
        ctk.CTkButton(subj_btns, text="Up", width=55, command=lambda: self._move_subject("up")).grid(row=0, column=2, padx=(0, 6))
        ctk.CTkButton(subj_btns, text="Down", width=55, command=lambda: self._move_subject("down")).grid(row=0, column=3, padx=(0, 6))
        ctk.CTkButton(subj_btns, text="Edit", width=55, command=self._edit_subject).grid(row=0, column=4)

        # Blocks panel
        self.block_panel = ctk.CTkFrame(top, width=320)
        self.block_panel.grid(row=0, column=1, sticky="ns", padx=(0, 8))
        self.block_panel.grid_rowconfigure(1, weight=1)
        self.block_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.block_panel, text="Blocks").grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        self.blocks = ttk.Treeview(self.block_panel, columns=["type", "preview"], show="headings", height=18)
        self.blocks.heading("type", text="type")
        self.blocks.heading("preview", text="preview")
        self.blocks.column("type", width=110, stretch=False)
        self.blocks.column("preview", width=170, stretch=True)
        self.blocks.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.blocks.bind("<<TreeviewSelect>>", lambda _e: self._on_block_selected())
        by = ttk.Scrollbar(self.block_panel, orient=tk.VERTICAL, command=self.blocks.yview)
        self.blocks.configure(yscrollcommand=by.set)
        by.grid(row=1, column=1, sticky="ns", pady=(0, 8))

        block_btns = ctk.CTkFrame(self.block_panel)
        block_btns.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
        ctk.CTkButton(block_btns, text="Add", width=70, command=self._add_block).grid(row=0, column=0, padx=(0, 6))
        ctk.CTkButton(block_btns, text="Delete", width=70, command=self._delete_block).grid(row=0, column=1, padx=(0, 6))
        ctk.CTkButton(block_btns, text="Up", width=55, command=lambda: self._move_block("up")).grid(row=0, column=2, padx=(0, 6))
        ctk.CTkButton(block_btns, text="Down", width=55, command=lambda: self._move_block("down")).grid(row=0, column=3, padx=(0, 6))

        # Editor panel
        self.editor_panel = ctk.CTkFrame(top)
        self.editor_panel.grid(row=0, column=2, sticky="nsew")
        self.editor_panel.grid_columnconfigure(0, weight=1)
        self.editor_panel.grid_rowconfigure(0, weight=1)

        self.editor_tabs = ctk.CTkTabview(self.editor_panel)
        self.editor_tabs.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.editor_tabs.add("Block Editor")
        self.editor_tabs.add("JSON Import")

        self.block_editor_tab = self.editor_tabs.tab("Block Editor")
        self.block_editor_tab.grid_columnconfigure(0, weight=1)
        self.block_editor_tab.grid_rowconfigure(0, weight=1)

        self.json_tab = self.editor_tabs.tab("JSON Import")
        self.json_tab.grid_columnconfigure(0, weight=1)
        self.json_tab.grid_rowconfigure(0, weight=1)

        self.editor_placeholder = ctk.CTkLabel(self.block_editor_tab, text="Select a block to edit.", anchor="center")
        self.editor_placeholder.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.current_form = None

        self.json_import_panel = JsonImportPanel(
            self.json_tab,
            on_validate=self._validate_json_input,
            on_import=self._import_json_input,
            on_load_file=self._load_json_from_file_into_workspace,
        )
        self.json_import_panel.grid(row=0, column=0, sticky="nsew")

        # Build/preview action bar
        actions = ctk.CTkFrame(self)
        actions.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        actions.grid_columnconfigure(1, weight=1)
        actions.grid_columnconfigure(3, weight=1)

        self.output_dir_var = ctk.StringVar(value=self.controller.get_output_dir_display())
        self.output_name_var = ctk.StringVar(value=self.controller.custom_filename)
        self.auto_name_var = tk.BooleanVar(value=self.controller.use_auto_name)

        ctk.CTkLabel(actions, text="Output directory").grid(row=0, column=0, padx=(8, 6), pady=(8, 4), sticky="w")
        self.output_dir_entry = ctk.CTkEntry(actions, textvariable=self.output_dir_var)
        self.output_dir_entry.grid(row=0, column=1, padx=(0, 6), pady=(8, 4), sticky="ew")
        ctk.CTkButton(actions, text="Browse...", width=95, command=self._browse_output_dir).grid(row=0, column=2, padx=(0, 8), pady=(8, 4))

        ctk.CTkLabel(actions, text="File name").grid(row=0, column=3, padx=(0, 6), pady=(8, 4), sticky="w")
        self.output_name_entry = ctk.CTkEntry(actions, textvariable=self.output_name_var, width=240)
        self.output_name_entry.grid(row=0, column=4, padx=(0, 6), pady=(8, 4), sticky="ew")
        self.auto_name_check = ctk.CTkCheckBox(actions, text="Auto name", variable=self.auto_name_var, command=self._on_auto_name_toggled)
        self.auto_name_check.grid(row=0, column=5, padx=(0, 6), pady=(8, 4), sticky="w")
        ctk.CTkButton(actions, text="Reset", width=80, command=self._reset_output_settings).grid(row=0, column=6, padx=(0, 8), pady=(8, 4))

        ctk.CTkButton(actions, text="Generate Typst Only", command=self._generate_typst_only).grid(row=1, column=0, padx=(8, 6), pady=(4, 8), sticky="w")
        ctk.CTkButton(actions, text="Build Preview PDF", command=lambda: self._build("preview")).grid(row=1, column=1, padx=(0, 6), pady=(4, 8), sticky="w")
        ctk.CTkButton(actions, text="Build Strict PDF", command=lambda: self._build("strict")).grid(row=1, column=2, padx=(0, 8), pady=(4, 8), sticky="w")
        ctk.CTkButton(actions, text="Open Generated Typst", command=self._open_generated_typst).grid(row=1, column=3, padx=(0, 6), pady=(4, 8), sticky="w")
        ctk.CTkButton(actions, text="Open Preview PDF", command=self._open_preview_pdf).grid(row=1, column=4, padx=(0, 6), pady=(4, 8), sticky="w")
        ctk.CTkButton(actions, text="Open Build Report", command=self._open_build_report).grid(row=1, column=5, padx=(0, 8), pady=(4, 8), sticky="w")
        self._sync_output_controls()

        # Bottom logs
        self.logs = LogPanel(self)
        self.logs.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))

    def _update_title(self) -> None:
        path = str(self.controller.path) if self.controller.path else "Untitled"
        dirty = "*" if self.controller.dirty else ""
        self.title(f"SDRE - {path}{dirty}")

    def _on_close(self) -> None:
        if self.controller.dirty:
            ok = messagebox.askyesno("Unsaved changes", "You have unsaved changes. Quit anyway?")
            if not ok:
                return
        self.destroy()

    # ---- selection helpers
    def _selected_subject_id(self) -> str | None:
        sel = self.subjects.selection()
        return sel[0] if sel else None

    def _selected_block_id(self) -> str | None:
        sel = self.blocks.selection()
        return sel[0] if sel else None

    # ---- refresh
    def _refresh_subjects(self) -> None:
        for iid in self.subjects.get_children():
            self.subjects.delete(iid)
        for s in self.controller.project_file.project.subjects:
            self.subjects.insert("", "end", iid=s.id, values=(s.title,))

    def _block_preview(self, b) -> str:
        if hasattr(b, "title"):
            return str(getattr(b, "title"))
        if hasattr(b, "value"):
            v = str(getattr(b, "value"))
            return v[:80].replace("\n", " ")
        if hasattr(b, "src"):
            return str(getattr(b, "src"))
        if hasattr(b, "content"):
            # inline preview
            out = []
            for n in getattr(b, "content"):
                if hasattr(n, "value"):
                    out.append(str(getattr(n, "value")))
            return "".join(out)[:80]
        return ""

    def _refresh_blocks(self) -> None:
        for iid in self.blocks.get_children():
            self.blocks.delete(iid)
        sid = self._selected_subject_id()
        if not sid:
            return
        s = ps.get_subject(self.controller.project_file, sid)
        for b in s.blocks:
            self.blocks.insert("", "end", iid=b.id, values=(b.type, self._block_preview(b)))

    def _refresh_editor(self) -> None:
        if self.current_form is not None:
            self.current_form.destroy()
            self.current_form = None
        self.editor_placeholder.grid_forget()

        sid = self._selected_subject_id()
        bid = self._selected_block_id()
        if not sid or not bid:
            self.editor_placeholder.configure(text="Select a block to edit.")
            self.editor_placeholder.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
            return
        block = ps.get_block(self.controller.project_file, sid, bid)
        self.current_form = make_block_form(self.block_editor_tab, block, on_change=self._on_model_changed)
        self.current_form.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

    def _refresh_all(self) -> None:
        self._refresh_subjects()
        # preserve selection if possible
        subs = self.controller.project_file.project.subjects
        if subs:
            if not self.subjects.selection():
                self.subjects.selection_set(subs[0].id)
        self._refresh_blocks()
        self._refresh_editor()

    def _on_subject_selected(self) -> None:
        self._refresh_blocks()
        self._refresh_editor()

    def _on_block_selected(self) -> None:
        self._refresh_editor()

    def _on_model_changed(self) -> None:
        self.controller.mark_dirty()
        self._update_title()
        self._refresh_blocks()
        self.logs.set_status("Edited (unsaved)")

    # ---- output settings
    def _sync_output_controls(self) -> None:
        self.output_dir_var.set(self.controller.get_output_dir_display())
        self.output_name_var.set(self.controller.custom_filename)
        self.auto_name_var.set(self.controller.use_auto_name)
        entry_state = "disabled" if self.controller.use_auto_name else "normal"
        self.output_name_entry.configure(state=entry_state)

    def _pull_output_settings_from_ui(self) -> None:
        self.controller.set_output_dir(self.output_dir_var.get())
        self.controller.set_custom_filename(self.output_name_var.get())
        self.controller.set_use_auto_name(bool(self.auto_name_var.get()))
        entry_state = "disabled" if self.controller.use_auto_name else "normal"
        self.output_name_entry.configure(state=entry_state)

    def _browse_output_dir(self) -> None:
        current_dir = self.output_dir_var.get().strip() or str(self.controller.get_default_output_dir())
        selected = filedialog.askdirectory(title="Select Output Directory", initialdir=current_dir)
        if not selected:
            return
        self.output_dir_var.set(selected)
        self.controller.set_output_dir(selected)
        self.logs.set_status(f"Output directory set: {selected}")

    def _on_auto_name_toggled(self) -> None:
        self.controller.set_use_auto_name(bool(self.auto_name_var.get()))
        entry_state = "disabled" if self.controller.use_auto_name else "normal"
        self.output_name_entry.configure(state=entry_state)

    def _reset_output_settings(self) -> None:
        self.controller.reset_output_settings()
        self._sync_output_controls()
        self.logs.set_status("Output settings reset to default")

    # ---- file actions
    def _new_project(self) -> None:
        if self.controller.dirty:
            ok = messagebox.askyesno("Unsaved changes", "Discard unsaved changes and create a new project?")
            if not ok:
                return
        self.controller.new_project()
        self._refresh_all()
        self._update_title()
        self.logs.clear()
        self.logs.set_status("New project")

    def _open_project(self) -> None:
        if self.controller.dirty:
            ok = messagebox.askyesno("Unsaved changes", "Discard unsaved changes and open another project?")
            if not ok:
                return
        path = filedialog.askopenfilename(
            title="Open Project",
            filetypes=[("SDRE Project", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        rep = self.controller.open_project(path)
        self.logs.clear()
        if rep.ok:
            self.logs.append(f"Opened: {path}")
            self.logs.set_status("Project loaded")
            self._refresh_all()
            self._update_title()
        else:
            self.logs.append("Open failed (validation).")
            self.logs.append(json.dumps(rep.model_dump(), ensure_ascii=False, indent=2))
            self.logs.set_status("Open failed")

    def _save(self) -> None:
        try:
            if self.controller.path is None:
                return self._save_as()
            self.controller.save()
            self._update_title()
            self.logs.set_status("Saved")
            self.logs.append(f"Saved: {self.controller.path}")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    def _save_as(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save As",
            defaultextension=".json",
            filetypes=[("SDRE Project", "*.json")],
        )
        if not path:
            return
        try:
            self.controller.save_as(path)
            self._update_title()
            self.logs.set_status("Saved")
            self.logs.append(f"Saved: {path}")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    def _project_settings(self) -> None:
        def _applied():
            self._update_title()
            self._refresh_blocks()
            self.logs.set_status("Project settings updated (unsaved)")

        ProjectSettingsDialog(self, controller=self.controller, on_applied=_applied)

    def _validate(self) -> None:
        rep = self.controller.validate_current_file()
        self.logs.clear()
        if rep.ok:
            self.logs.append("VALIDATION PASSED")
            self.logs.set_status("Validation passed")
        else:
            self.logs.append("VALIDATION FAILED")
            self.logs.append(json.dumps(rep.model_dump(), ensure_ascii=False, indent=2))
            self.logs.set_status(f"Validation failed at {rep.stage}")

    def _validate_json_input(self, text: str):
        rep = self.controller.validate_json_text(text)
        if rep.ok:
            self.logs.set_status("JSON workspace validation: passed")
        else:
            self.logs.set_status(f"JSON workspace validation failed at {rep.stage}")
        return rep

    def _import_json_input(self, text: str):
        rep = self.controller.import_json_text(text)
        if rep.ok:
            self._refresh_all()
            self._update_title()
            self.logs.clear()
            self.logs.append("Imported JSON into project state.")
            self.logs.set_status("JSON imported (unsaved)")
        else:
            self.logs.clear()
            self.logs.append("JSON import failed.")
            self.logs.append(json.dumps(rep.model_dump(), ensure_ascii=False, indent=2))
            self.logs.set_status(f"JSON import failed at {rep.stage}")
        return rep

    def _load_json_from_file_into_workspace(self) -> tuple[str, str] | None:
        path = filedialog.askopenfilename(
            title="Load JSON Into Workspace",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return None
        try:
            text = Path(path).read_text(encoding="utf-8")
        except Exception as e:
            messagebox.showerror("Load failed", str(e))
            return None
        self.logs.set_status(f"Loaded JSON workspace file: {path}")
        return (path, text)

    def _generate_typst_only(self) -> None:
        self.logs.clear()
        try:
            rep = self.controller.generate_typst_only()
        except Exception as e:
            messagebox.showerror("Generate failed", str(e))
            return

        if rep.ok:
            p = self.controller.generated_typst_path()
            self.logs.append("GENERATE TYPST: OK")
            self.logs.append(f"Output: {p}")
            self.logs.set_status("Generated Typst only")
            return

        self.logs.append("GENERATE TYPST: FAILED")
        self.logs.append(json.dumps(rep.model_dump(), ensure_ascii=False, indent=2))
        self.logs.set_status(f"Generate failed at {rep.stage}")

    def _build(self, mode: str) -> None:
        self.logs.clear()
        try:
            self._pull_output_settings_from_ui()
            rep = self.controller.build(mode)
        except Exception as e:
            messagebox.showerror("Build failed", str(e))
            return
        self.logs.append(json.dumps(rep.model_dump(), ensure_ascii=False, indent=2))
        if rep.ok:
            self.logs.set_status(f"Build {mode}: OK")
            self.logs.append(f"Output: {rep.output_pdf}")
        else:
            self.logs.set_status(f"Build {mode}: FAILED at {rep.stage}")

    def _open_output_folder(self) -> None:
        try:
            self._pull_output_settings_from_ui()
            p = self.controller.open_output_folder()
            self.logs.set_status(f"Opened output folder: {p}")
        except Exception as e:
            messagebox.showerror("Failed", str(e))

    def _open_generated_typst(self) -> None:
        try:
            p = self.controller.open_generated_typst()
            self.logs.set_status(f"Opened: {p}")
        except Exception as e:
            messagebox.showerror("Failed", str(e))

    def _open_preview_pdf(self) -> None:
        try:
            p = self.controller.open_preview_pdf()
            self.logs.set_status(f"Opened: {p}")
        except Exception as e:
            messagebox.showerror("Failed", str(e))

    def _open_build_report(self) -> None:
        try:
            p = self.controller.open_build_report()
            self.logs.set_status(f"Opened: {p}")
        except Exception as e:
            messagebox.showerror("Failed", str(e))

    def _open_last_build_report(self) -> None:
        self._open_build_report()

    # ---- subject ops
    def _add_subject(self) -> None:
        sid = ps.add_subject(self.controller.project_file)
        self.controller.mark_dirty()
        self._refresh_subjects()
        self.subjects.selection_set(sid)
        self._on_subject_selected()
        self._update_title()

    def _delete_subject(self) -> None:
        sid = self._selected_subject_id()
        if not sid:
            return
        ok = messagebox.askyesno("Delete Subject", f"Delete subject '{sid}'?")
        if not ok:
            return
        ps.delete_subject(self.controller.project_file, sid)
        self.controller.mark_dirty()
        self._refresh_all()
        self._update_title()

    def _move_subject(self, direction: str) -> None:
        sid = self._selected_subject_id()
        if not sid:
            return
        ps.move_subject(self.controller.project_file, sid, direction)  # type: ignore[arg-type]
        self.controller.mark_dirty()
        self._refresh_subjects()
        self.subjects.selection_set(sid)
        self._update_title()

    def _edit_subject(self) -> None:
        sid = self._selected_subject_id()
        if not sid:
            return
        s = ps.get_subject(self.controller.project_file, sid)

        win = ctk.CTkToplevel(self)
        win.title(f"Edit Subject ({sid})")
        win.geometry("520x240")
        win.resizable(False, False)
        win.grid_columnconfigure(1, weight=1)

        title_var = ctk.StringVar(value=s.title)
        desc_var = ctk.StringVar(value=s.description or "")

        ctk.CTkLabel(win, text="title").grid(row=0, column=0, padx=12, pady=(12, 6), sticky="w")
        title = ctk.CTkEntry(win, textvariable=title_var)
        title.grid(row=0, column=1, padx=12, pady=(12, 6), sticky="ew")

        ctk.CTkLabel(win, text="description").grid(row=1, column=0, padx=12, pady=6, sticky="nw")
        desc = ctk.CTkTextbox(win, height=100)
        desc.grid(row=1, column=1, padx=12, pady=6, sticky="nsew")
        desc.insert("1.0", desc_var.get())

        def _ok():
            t = title_var.get().strip()
            if not t:
                messagebox.showerror("Invalid", "title is required")
                return
            d = desc.get("1.0", "end-1c").strip()
            ps.update_subject_meta(self.controller.project_file, sid, title=t, description=(d if d else None))
            self.controller.mark_dirty()
            self._refresh_subjects()
            self.subjects.selection_set(sid)
            self._update_title()
            win.destroy()

        btns = ctk.CTkFrame(win)
        btns.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=12)
        btns.grid_columnconfigure(0, weight=1)
        btns.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(btns, text="Cancel", command=win.destroy).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(btns, text="OK", command=_ok).grid(row=0, column=1, sticky="ew", padx=(6, 0))
        win.grab_set()

    # ---- block ops
    def _add_block(self) -> None:
        sid = self._selected_subject_id()
        if not sid:
            return

        win = ctk.CTkToplevel(self)
        win.title("Add Block")
        win.geometry("420x180")
        win.resizable(False, False)
        win.grid_columnconfigure(1, weight=1)

        types = [
            "section",
            "subsection",
            "paragraph",
            "code_block",
            "math_block",
            "table",
            "image",
            "image_placeholder",
            "note",
            "warning",
            "bullet_list",
            "numbered_list",
            "page_break",
            "horizontal_rule",
        ]
        var = ctk.StringVar(value="paragraph")
        ctk.CTkLabel(win, text="type").grid(row=0, column=0, padx=12, pady=(12, 6), sticky="w")
        ctk.CTkOptionMenu(win, values=types, variable=var).grid(row=0, column=1, padx=12, pady=(12, 6), sticky="ew")

        def _ok():
            bid = ps.add_block(self.controller.project_file, sid, var.get())  # type: ignore[arg-type]
            self.controller.mark_dirty()
            win.destroy()
            self._refresh_blocks()
            self.blocks.selection_set(bid)
            self._on_block_selected()
            self._update_title()

        btns = ctk.CTkFrame(win)
        btns.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=12)
        btns.grid_columnconfigure(0, weight=1)
        btns.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(btns, text="Cancel", command=win.destroy).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(btns, text="OK", command=_ok).grid(row=0, column=1, sticky="ew", padx=(6, 0))
        win.grab_set()

    def _delete_block(self) -> None:
        sid = self._selected_subject_id()
        bid = self._selected_block_id()
        if not sid or not bid:
            return
        ok = messagebox.askyesno("Delete Block", f"Delete block '{bid}'?")
        if not ok:
            return
        ps.delete_block(self.controller.project_file, sid, bid)
        self.controller.mark_dirty()
        self._refresh_blocks()
        self._refresh_editor()
        self._update_title()

    def _move_block(self, direction: str) -> None:
        sid = self._selected_subject_id()
        bid = self._selected_block_id()
        if not sid or not bid:
            return
        ps.move_block(self.controller.project_file, sid, bid, direction)  # type: ignore[arg-type]
        self.controller.mark_dirty()
        self._refresh_blocks()
        self.blocks.selection_set(bid)
        self._update_title()
