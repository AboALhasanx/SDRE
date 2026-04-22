# SDRE (Structured Document Rendering Engine)

SDRE is a strict, JSON-first document system:

1. **JSON is the source of truth**
2. JSON is **validated strictly** (JSON Schema + Pydantic models)
3. Validated data is **generated into Typst** and compiled to **PDF**
4. A **form-based desktop GUI** (CustomTkinter) edits the same canonical JSON structure

This repository currently provides:
- Strict schema + Pydantic data models
- Validation CLI
- Typst generator (templates + generated content file)
- Build pipeline that compiles to PDF using Typst
- Desktop GUI (form-based, not WYSIWYG)

## Architecture Summary

- `schema/project.schema.json`: Draft 2020-12 JSON Schema
- `src/models/`: Pydantic v2 strict models (`ProjectFile` root)
- `src/validation/`: schema + model validation entrypoints
- `src/generator/`: renderers that convert validated models into Typst source
- `templates/`: stable Typst templates (`main.typ`, `macros.typ`)
- `src/services/`: build pipeline (validate + generate + typst compile)
- `src/ui/`: desktop GUI layer (CustomTkinter + ttk.Treeview)

## Setup

### Install Python dependencies

```powershell
python -m pip install -r requirements.txt
```

### Install Typst

Install Typst and ensure `typst` is available in your PATH.

- Typst releases: [Typst GitHub Releases](https://github.com/typst/typst/releases)
- Typst docs: [Typst Documentation](https://typst.app/docs/)

Verify:

```powershell
typst --version
```

## Example Project

The example project is:

- `examples/sample_project.json`

It is strictly valid and used by tests and by generation/build.

## CLI Usage

### Validate

```powershell
python -m src.validation.cli validate examples/sample_project.json
```

### Generate Typst Content

Writes `build/generated_content.typ`:

```powershell
python -m src.generator.engine examples/sample_project.json
```

### Build PDF (Validate + Generate + Typst Compile)

Writes:
- `build/generated_content.typ`
- `build/output.pdf`
- `build/build.log`
- `build/build_report.json`

```powershell
python -m src.services.build_service build examples/sample_project.json --mode strict
```

Modes:
- `strict`: fail immediately on any validation/build error
- `preview`: attempts to compile if it can (may use cached generated content)

## GUI Usage

Launch:

```powershell
python app.py
```

Main UI:
- Left: Subjects list
- Middle: Blocks list for the selected subject
- Right: Dynamic form editor for the selected block
- Bottom: Status + logs/reports

Required actions are available via the menu:
- New/Open/Save/Save As
- Project Settings (edit Meta + Theme)
- Validate
- Build Preview / Build Strict
- Open Output Folder / Open Generated Typst / Open Last Build Report

## Recommended Fonts

Typst will warn if a font family isn’t installed. Recommended:
- Arabic base font: `Noto Sans Arabic`
- Monospace: `JetBrains Mono` or `Consolas`
- Math: `STIX Two Math`

## Known Limitations (MVP)

- Form-based editing only (no WYSIWYG, no rich text editor)
- No GUI editing for every possible future theme option yet; current UI covers the core theme structure
- Typst compilation depends on local font availability

## Build Artifacts

The `build/` directory is used for generated and build outputs:
- `generated_content.typ` (generated)
- `output.pdf` (Typst output)
- `build.log` and `build_report.json`

