import json
from pathlib import Path

import pytest

from src.models.project import ProjectFile
from src.ui.state import project_state as ps


def test_new_project_is_valid_model():
    pf = ps.new_project_file()
    ProjectFile.model_validate(pf.model_dump(mode="json"))


def test_open_save_helpers_roundtrip(tmp_path: Path):
    pf = ps.new_project_file()
    out = tmp_path / "p.json"
    ps.save_project_file(pf, out)
    pf2 = ps.load_project_file(out)
    assert pf2.project.meta.id == pf.project.meta.id
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert "project" in payload
    assert "subjects" in payload["project"]


def test_subject_add_remove_reorder():
    pf = ps.new_project_file()
    a = ps.add_subject(pf, title="A")
    b = ps.add_subject(pf, title="B")
    assert [s.id for s in pf.project.subjects][-2:] == [a, b]
    ps.move_subject(pf, b, "up")
    ids = [s.id for s in pf.project.subjects]
    assert ids.index(b) < ids.index(a)
    ps.delete_subject(pf, a)
    assert all(s.id != a for s in pf.project.subjects)


def test_block_add_remove_reorder():
    pf = ps.new_project_file()
    sid = pf.project.subjects[0].id
    b1 = ps.add_block(pf, sid, "code_block")
    b2 = ps.add_block(pf, sid, "math_block")
    blocks = ps.get_subject(pf, sid).blocks
    assert blocks[-2].id == b1
    assert blocks[-1].id == b2
    ps.move_block(pf, sid, b2, "up")
    blocks = ps.get_subject(pf, sid).blocks
    assert [b.id for b in blocks].index(b2) < [b.id for b in blocks].index(b1)
    ps.delete_block(pf, sid, b1)
    assert all(b.id != b1 for b in ps.get_subject(pf, sid).blocks)


def test_serialization_shape():
    pf = ps.new_project_file()
    payload = pf.model_dump(mode="json")
    assert set(payload.keys()) == {"project"}
    assert set(payload["project"].keys()) >= {"meta", "theme", "subjects"}

