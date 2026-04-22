from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .engine import validate_project_file


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sdre-validate", add_help=True)
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="Validate an SDRE project JSON file (strict).")
    v.add_argument("path", help="Path to a JSON project file.")
    v.add_argument(
        "--schema",
        default=None,
        help="Optional override path to schema/project.schema.json",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.cmd == "validate":
        report = validate_project_file(
            json_path=Path(args.path),
            schema_path=Path(args.schema) if args.schema else None,
        )
        if report.ok:
            print(f"VALIDATION PASSED: {report.file}")
            return 0
        payload = report.model_dump()
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    print("Unknown command", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

