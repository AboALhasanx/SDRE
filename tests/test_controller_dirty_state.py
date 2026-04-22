from src.ui.controllers.app_controller import AppController


def test_dirty_state_flips_and_updated_at_changes():
    c = AppController()
    old = c.project_file.project.meta.updated_at
    assert c.dirty is False
    c.mark_dirty()
    assert c.dirty is True
    assert c.project_file.project.meta.updated_at != old

