from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.generator.engine import generate_content
from src.models.project import ProjectFile
from src.validation.errors import ErrorItem
from src.validation.engine import load_json
from src.validation.schema_layer import load_schema, validate_instance, validate_schema

from .typst_runner import TypstResult, compile_to_pdf, find_typst

Mode = Literal["strict", "preview"]


class BuildReport(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    ok: bool
    mode: Mode
    source_file: str
    generated_typst_file: str
    template_file: str
    output_pdf: str
    stage: str
    stdout: str = ""
    stderr: str = ""
    errors: list[ErrorItem] = Field(default_factory=list)
    timings_ms: dict[str, int] = Field(default_factory=dict)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _paths() -> dict[str, Path]:
    root = _repo_root()
    build = root / "build"
    return {
        "root": root,
        "build": build,
        "generated": build / "generated_content.typ",
        "template_main": root / "templates" / "main.typ",
        "template_macros": root / "templates" / "macros.typ",
        "output_pdf": build / "output.pdf",
        "log": build / "build.log",
        "report": build / "build_report.json",
        "schema": root / "schema" / "project.schema.json",
    }


def _write_log(log_path: Path, report: BuildReport) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"ok={report.ok} mode={report.mode} stage={report.stage}\n")
    if report.stdout:
        lines.append("=== stdout ===\n")
        lines.append(report.stdout.rstrip() + "\n")
    if report.stderr:
        lines.append("=== stderr ===\n")
        lines.append(report.stderr.rstrip() + "\n")
    if report.errors:
        lines.append("=== errors ===\n")
        for e in report.errors:
            lines.append(f"{e.code} {e.severity} {e.path}: {e.message}\n")
            if e.hint:
                lines.append(f"  hint: {e.hint}\n")
    log_path.write_text("".join(lines), encoding="utf-8")


def _write_report(report_path: Path, report: BuildReport) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _err(code: str, message: str, hint: str = "", path: str = "/") -> ErrorItem:
    return ErrorItem(code=code, severity="error", path=path, message=message, hint=hint)


def _normalize_pydantic(e: ValidationError) -> list[ErrorItem]:
    out: list[ErrorItem] = []
    for item in e.errors():
        loc = item.get("loc", ())
        parts = list(loc) if isinstance(loc, tuple) else [loc]
        # reuse JSON pointer helper from validation.errors
        from src.validation.errors import json_pointer_from_parts

        out.append(
            ErrorItem(
                code="model.validation",
                severity="error",
                path=json_pointer_from_parts(parts),
                message=str(item.get("msg", "Validation error")),
                hint=f"Pydantic error type: {item.get('type', 'validation_error')}",
            )
        )
    return out


def build_pdf(
    *,
    source_file: str | Path,
    mode: Mode = "strict",
) -> BuildReport:
    p = _paths()
    source_file = Path(source_file)

    timings: dict[str, int] = {}
    t0 = time.perf_counter()

    def mark(name: str) -> None:
        timings[name] = int((time.perf_counter() - t0) * 1000)

    generated = p["generated"]
    template_main = p["template_main"]
    template_macros = p["template_macros"]
    out_pdf = p["output_pdf"]

    # Stage: load JSON
    stage = "load_json"
    data, load_errors = load_json(source_file)
    mark(stage)
    if load_errors:
        rep = BuildReport(
            ok=False,
            mode=mode,
            source_file=str(source_file),
            generated_typst_file=str(generated),
            template_file=str(template_main),
            output_pdf=str(out_pdf),
            stage=stage,
            errors=load_errors,
            timings_ms=timings,
        )
        _write_report(p["report"], rep)
        _write_log(p["log"], rep)
        return rep

    assert data is not None

    # Stage: schema validation
    stage = "schema"
    schema = load_schema(p["schema"])
    schema_errors = validate_schema(schema)
    if schema_errors:
        mark(stage)
        rep = BuildReport(
            ok=False,
            mode=mode,
            source_file=str(source_file),
            generated_typst_file=str(generated),
            template_file=str(template_main),
            output_pdf=str(out_pdf),
            stage=stage,
            errors=schema_errors,
            timings_ms=timings,
        )
        _write_report(p["report"], rep)
        _write_log(p["log"], rep)
        return rep

    instance_errors = validate_instance(schema, data)
    mark(stage)
    if instance_errors and mode == "strict":
        rep = BuildReport(
            ok=False,
            mode=mode,
            source_file=str(source_file),
            generated_typst_file=str(generated),
            template_file=str(template_main),
            output_pdf=str(out_pdf),
            stage=stage,
            errors=instance_errors,
            timings_ms=timings,
        )
        _write_report(p["report"], rep)
        _write_log(p["log"], rep)
        return rep

    # Stage: model validation
    stage = "model"
    project_file: ProjectFile | None = None
    model_errors: list[ErrorItem] = []
    if not instance_errors:
        try:
            project_file = ProjectFile.model_validate(data)
        except ValidationError as e:
            model_errors = _normalize_pydantic(e)
    else:
        # preview mode: schema errors exist; can't safely validate model
        model_errors = []

    mark(stage)
    if (instance_errors or model_errors) and mode == "strict":
        rep = BuildReport(
            ok=False,
            mode=mode,
            source_file=str(source_file),
            generated_typst_file=str(generated),
            template_file=str(template_main),
            output_pdf=str(out_pdf),
            stage=stage,
            errors=(instance_errors + model_errors),
            timings_ms=timings,
        )
        _write_report(p["report"], rep)
        _write_log(p["log"], rep)
        return rep

    # Stage: generate content (only if we have a validated model)
    stage = "generate"
    gen_errors: list[ErrorItem] = []
    if project_file is not None:
        try:
            generate_content(project_file, generated)
        except Exception as e:
            gen_errors = [_err("generator.failed", f"Generator failed: {e}", hint="See stack trace in console.")]
    else:
        if mode == "preview":
            if not generated.exists():
                gen_errors = [
                    _err(
                        "generator.missing_cached",
                        "Validation failed and no previously generated content exists for preview.",
                        hint="Run a successful strict build at least once, or fix validation errors.",
                    )
                ]
        else:
            gen_errors = [_err("generator.no_model", "No validated model available for generation.")]

    mark(stage)
    if gen_errors and mode == "strict":
        rep = BuildReport(
            ok=False,
            mode=mode,
            source_file=str(source_file),
            generated_typst_file=str(generated),
            template_file=str(template_main),
            output_pdf=str(out_pdf),
            stage=stage,
            errors=gen_errors,
            timings_ms=timings,
        )
        _write_report(p["report"], rep)
        _write_log(p["log"], rep)
        return rep
    if gen_errors and mode == "preview":
        # Nothing else to do; compilation is not possible without generated content.
        rep = BuildReport(
            ok=False,
            mode=mode,
            source_file=str(source_file),
            generated_typst_file=str(generated),
            template_file=str(template_main),
            output_pdf=str(out_pdf),
            stage=stage,
            errors=(instance_errors + model_errors + gen_errors),
            timings_ms=timings,
        )
        _write_report(p["report"], rep)
        _write_log(p["log"], rep)
        return rep

    # Stage: templates
    stage = "templates"
    tpl_errors: list[ErrorItem] = []
    if not template_main.exists():
        tpl_errors.append(_err("templates.missing", f"Missing template: {template_main}"))
    if not template_macros.exists():
        tpl_errors.append(_err("templates.missing", f"Missing template: {template_macros}"))
    if not generated.exists():
        tpl_errors.append(_err("generated.missing", f"Missing generated file: {generated}"))

    mark(stage)
    if tpl_errors and mode == "strict":
        rep = BuildReport(
            ok=False,
            mode=mode,
            source_file=str(source_file),
            generated_typst_file=str(generated),
            template_file=str(template_main),
            output_pdf=str(out_pdf),
            stage=stage,
            errors=tpl_errors,
            timings_ms=timings,
        )
        _write_report(p["report"], rep)
        _write_log(p["log"], rep)
        return rep
    if tpl_errors and mode == "preview":
        rep = BuildReport(
            ok=False,
            mode=mode,
            source_file=str(source_file),
            generated_typst_file=str(generated),
            template_file=str(template_main),
            output_pdf=str(out_pdf),
            stage=stage,
            errors=(instance_errors + model_errors + gen_errors + tpl_errors),
            timings_ms=timings,
        )
        _write_report(p["report"], rep)
        _write_log(p["log"], rep)
        return rep

    # Stage: typst availability
    stage = "typst"
    typst_bin = find_typst()
    mark(stage)
    typst_errors: list[ErrorItem] = []
    if not typst_bin:
        typst_errors.append(
            _err(
                "typst.missing",
                "Typst binary not found in PATH.",
                hint="Install Typst and ensure `typst` is available in PATH.",
            )
        )
        rep = BuildReport(
            ok=False,
            mode=mode,
            source_file=str(source_file),
            generated_typst_file=str(generated),
            template_file=str(template_main),
            output_pdf=str(out_pdf),
            stage=stage,
            errors=(instance_errors + model_errors + gen_errors + tpl_errors + typst_errors),
            timings_ms=timings,
        )
        _write_report(p["report"], rep)
        _write_log(p["log"], rep)
        return rep

    # Stage: compile
    stage = "compile"
    compile_start = time.perf_counter()
    res: TypstResult = compile_to_pdf(
        typst_bin=typst_bin,
        main_typ=template_main,
        out_pdf=out_pdf,
        cwd=p["root"],
        root=p["root"],
        timeout_s=120,
    )
    timings["compile_ms"] = int((time.perf_counter() - compile_start) * 1000)
    mark(stage)

    compile_errors: list[ErrorItem] = []
    if not res.ok:
        compile_errors.append(
            _err(
                "typst.compile_failed",
                f"Typst compile failed with exit code {res.returncode}.",
                hint="See stderr for Typst diagnostics.",
            )
        )

    ok = res.ok and not tpl_errors and not typst_errors
    stage_final = "ok" if ok else "compile"
    rep = BuildReport(
        ok=ok,
        mode=mode,
        source_file=str(source_file),
        generated_typst_file=str(generated),
        template_file=str(template_main),
        output_pdf=str(out_pdf),
        stage=stage_final,
        stdout=res.stdout,
        stderr=res.stderr,
        errors=(instance_errors + model_errors + gen_errors + tpl_errors + typst_errors + compile_errors),
        timings_ms=timings,
    )
    _write_report(p["report"], rep)
    _write_log(p["log"], rep)
    return rep


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sdre-build", add_help=True)
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="Validate, generate Typst, and compile PDF.")
    b.add_argument("path", help="Path to a project JSON file.")
    b.add_argument("--mode", choices=["strict", "preview"], default="strict")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.cmd == "build":
        rep = build_pdf(source_file=args.path, mode=args.mode)
        if rep.ok:
            print(f"BUILD PASSED: {rep.output_pdf}")
            return 0
        # build_service always writes report/log; just point to the report.
        print(f"BUILD FAILED at stage '{rep.stage}'. See build/build_report.json", flush=True)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
