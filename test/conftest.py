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
from app import models  # noqa: F401, E402


#Tut gotovlyu otdelnyu in-memory bazu pod testy.
@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    Base.metadata.create_all(bind=engine)

    yield testing_session

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


#Tut podmenyayu zavisimost bazy i podnimayu TestClient.
@pytest.fixture()
def client(session_factory, monkeypatch):
    import app.main as main_module
    import app.api.routes.auth as auth_module

    monkeypatch.setattr(main_module, "init_db", lambda: None)
    monkeypatch.setattr(auth_module.settings, "email_delivery_mode", "demo")
    monkeypatch.setattr(auth_module.settings, "expose_verification_token_in_response", True)
    monkeypatch.setattr(auth_module.settings, "email_2fa_enabled", False)
    auth_module._rate_limit_store.clear()

    #Tut lokalnyy get_db, chtoby API rabotalo na testovoy baze.
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
