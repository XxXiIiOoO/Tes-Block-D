from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


from app.api.deps import get_db  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.services.rate_limit import clear_rate_limit_state  # noqa: E402
from app import models  # noqa: F401, E402


#Eto otdelnyy shag session_factory, chtoby ne kopipastit odno i to zhe.
@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    Base.metadata.create_all(bind=engine)

    yield TestingSessionLocal

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


#Funkciya client zakryvaet konkretnuyu zadachu v etom meste.
@pytest.fixture()
def client(session_factory, monkeypatch):
    import app.main as main_module
    import app.api.routes.auth as auth_module

    monkeypatch.setattr(main_module, "init_db", lambda: None)
    monkeypatch.setattr(auth_module.settings, "email_delivery_mode", "demo")
    monkeypatch.setattr(auth_module.settings, "expose_verification_token_in_response", True)
    monkeypatch.setattr(auth_module.settings, "email_2fa_enabled", False)
    clear_rate_limit_state()

    #Eto otdelnyy shag override_get_db, chtoby ne kopipastit odno i to zhe.
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
