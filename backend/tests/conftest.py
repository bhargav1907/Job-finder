from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.models  # noqa: F401 - registers tables
from app.db import get_session
from app.main import app


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(eng)
    yield eng
    SQLModel.metadata.drop_all(eng)


@pytest.fixture
def session(engine) -> Iterator[Session]:
    with Session(engine) as db:
        yield db


@pytest.fixture
def api(session, monkeypatch):
    monkeypatch.setattr("app.main.init_db", lambda: None)

    def override():
        yield session

    app.dependency_overrides[get_session] = override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
