import json
from pathlib import Path

import pytest

import src.services.build_service as bs
from src.services.typst_runner import TypstResult


def _copy_tree(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


@pytest.fixture()
def temp_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    real_root = bs._repo_root()
    root = tmp_path / "sdre_tmp_root"
    (root / "schema").mkdir(parents=True, exist_ok=True)
    (root / "templates").mkdir(parents=True, exist_ok=True)
    (root / "build").mkdir(parents=True, exist_ok=True)

    _copy_tree(real_root / "schema" / "project.schema.json", root / "schema" / "project.schema.json")
    _copy_tree(real_root / "templates" / "main.typ", root / "templates" / "main.typ")
    _copy_tree(real_root / "templates" / "macros.typ", root / "templates" / "macros.typ")

    def _paths_override() -> dict[str, Path]:
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

    monkeypatch.setattr(bs, "_paths", _paths_override)
    return {"root": root, "build": root / "build"}


def test_typst_missing_fails_and_writes_report_and_log(temp_repo, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(bs, "find_typst", lambda: None)

    report = bs.build_pdf(source_file="examples/sample_project.json", mode="strict")
    assert report.ok is False
    assert report.stage == "typst"

    report_path = temp_repo["build"] / "build_report.json"
    log_path = temp_repo["build"] / "build.log"
    assert report_path.exists()
    assert log_path.exists()

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["ok"] is False
    assert any(e["code"] == "typst.missing" for e in payload["errors"])


def test_validation_failure_stops_build_in_strict(temp_repo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Ensure typst would be available, but should never be reached.
    monkeypatch.setattr(bs, "find_typst", lambda: "typst")
    monkeypatch.setattr(bs, "compile_to_pdf", lambda **kwargs: (_ for _ in ()).throw(AssertionError("should not compile")))

    data = json.loads(Path("examples/sample_project.json").read_text(encoding="utf-8"))
    del data["project"]["meta"]["title"]
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    report = bs.build_pdf(source_file=bad, mode="strict")
    assert report.ok is False
    assert report.stage in ("schema", "model")
    assert any(e.code.startswith("schema.") or e.code.startswith("model.") for e in report.errors)


def test_generation_failure_propagates(temp_repo, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(bs, "find_typst", lambda: "typst")
    monkeypatch.setattr(bs, "compile_to_pdf", lambda **kwargs: (_ for _ in ()).throw(AssertionError("should not compile")))

    def _boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(bs, "generate_content", _boom)

    report = bs.build_pdf(source_file="examples/sample_project.json", mode="strict")
    assert report.ok is False
    assert report.stage == "generate"
    assert any(e.code == "generator.failed" for e in report.errors)


def test_successful_build_path_with_mocked_typst(temp_repo, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(bs, "find_typst", lambda: "typst")

    def _fake_compile_to_pdf(*, typst_bin, main_typ, out_pdf, cwd, root, timeout_s=60):
        out_pdf.parent.mkdir(parents=True, exist_ok=True)
        out_pdf.write_bytes(b"%PDF-1.4\n%fake\n")
        return TypstResult(
            ok=True,
            returncode=0,
            stdout="ok",
            stderr="",
            cmd=[typst_bin, "compile", "--root", str(root), str(main_typ), str(out_pdf)],
        )

    monkeypatch.setattr(bs, "compile_to_pdf", _fake_compile_to_pdf)

    report = bs.build_pdf(source_file="examples/sample_project.json", mode="strict")
    assert report.ok is True
    assert report.stage == "ok"

    build_dir = temp_repo["build"]
    assert (build_dir / "generated_content.typ").exists()
    assert (build_dir / "output.pdf").exists()
    assert (build_dir / "build_report.json").exists()
    assert (build_dir / "build.log").exists()
