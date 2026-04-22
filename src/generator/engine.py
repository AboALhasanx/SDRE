from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.models.project import ProjectFile
from src.validation.schema_layer import load_schema, validate_instance, validate_schema

from .project_renderer import render_project_file


def generate_content(project_file: ProjectFile, out_path: str | Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    content = render_project_file(project_file)
    out_path.write_text(content, encoding="utf-8")
    return out_path


def _load_and_validate_to_model(json_path: Path, schema_path: Path) -> ProjectFile:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    schema = load_schema(schema_path)

    schema_errors = validate_schema(schema)
    if schema_errors:
        raise ValueError(f"Schema invalid: {schema_errors[0].message}")

    instance_errors = validate_instance(schema, data)
    if instance_errors:
        first = instance_errors[0]
        raise ValueError(f"Schema validation failed at {first.path}: {first.message}")

    return ProjectFile.model_validate(data)


def _default_schema_path() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "schema" / "project.schema.json"


def _default_out_path() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "build" / "generated_content.typ"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="sdre-generate", add_help=True)
    p.add_argument("json_path", help="Path to a validated SDRE project JSON file.")
    p.add_argument("--schema", default=None, help="Optional schema override path.")
    p.add_argument("--out", default=None, help="Output .typ path (default: build/generated_content.typ).")
    args = p.parse_args(argv)

    json_path = Path(args.json_path)
    schema_path = Path(args.schema) if args.schema else _default_schema_path()
    out_path = Path(args.out) if args.out else _default_out_path()

    try:
        pf = _load_and_validate_to_model(json_path, schema_path)
    except Exception as e:
        print(f"GENERATION FAILED (validation): {e}", file=sys.stderr)
        return 2

    generate_content(pf, out_path)
    print(f"GENERATED: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

