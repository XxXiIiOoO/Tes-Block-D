from __future__ import annotations

from sqlalchemy import select

from app.core.config import settings
from app.core.security import get_password_hash
from app.db import session as session_module
from app.models.project import Project
from app.models.test import Test
from app.models.user import User
from app.services.presets import PRESET_IMAGE, PRESET_PROJECT_NAME, PRESET_TESTS


#Eto otdelnyy shag test_seed_presets_creates_ready_to_run_evm_suite, chtoby ne kopipastit odno i to zhe.
def test_seed_presets_creates_ready_to_run_evm_suite(session_factory, monkeypatch):
    monkeypatch.setattr(session_module, "SessionLocal", session_factory)
    monkeypatch.setattr(session_module.settings, "seed_presets", True)
    monkeypatch.setattr(session_module.settings, "bootstrap_admin_email", "admin@example.com")

    db = session_factory()
    db.add(
        User(
            email="admin@example.com",
            username="admin",
            password_hash=get_password_hash("secret123"),
            is_admin=True,
        )
    )
    db.commit()
    db.close()

    session_module.ensure_seed_presets()
    session_module.ensure_seed_presets()

    db = session_factory()
    project = db.scalar(select(Project).where(Project.name == PRESET_PROJECT_NAME))
    assert project is not None

    tests = db.scalars(select(Test).where(Test.project_id == project.id)).all()
    assert len(tests) == len(PRESET_TESTS)
    assert len(PRESET_TESTS) >= 10
    assert {test.name for test in tests} == {preset.name for preset in PRESET_TESTS}
    assert all(test.docker_image == PRESET_IMAGE for test in tests)
    assert settings.is_docker_image_allowed(PRESET_IMAGE)
    assert all("run_preset.py" in test.command for test in tests)
    db.close()
