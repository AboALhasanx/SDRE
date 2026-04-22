import json
from pathlib import Path

from src.ui.state import project_state as ps


def test_save_excludes_none_fields_schema_safe(tmp_path: Path):
    pf = ps.new_project_file()
    # Ensure optional groups are None so they must not be emitted as null.
    pf.project.theme.headings = None
    pf.project.theme.code = None
    pf.project.theme.tables = None
    pf.project.theme.ltr_inline_style = None

    out = tmp_path / "p.json"
    ps.save_project_file(pf, out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    theme = payload["project"]["theme"]
    assert "headings" not in theme
    assert "code" not in theme
    assert "tables" not in theme
    assert "ltr_inline_style" not in theme


def test_meta_theme_changes_roundtrip(tmp_path: Path):
    pf = ps.new_project_file()
    pf.project.meta.title = "X"
    pf.project.meta.direction = "rtl"
    pf.project.theme.page.size = "Letter"
    pf.project.theme.colors.accent = "#123456"

    out = tmp_path / "p.json"
    ps.save_project_file(pf, out)
    pf2 = ps.load_project_file(out)
    assert pf2.project.meta.title == "X"
    assert pf2.project.meta.direction == "rtl"
    assert pf2.project.theme.page.size == "Letter"
    assert pf2.project.theme.colors.accent == "#123456"

