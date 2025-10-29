from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.main import app as fastapi_app

import app.models  # noqa: F401


@pytest.fixture()
def engine() -> Generator:
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)
    yield test_engine


@pytest.fixture()
def client(engine) -> Generator[TestClient, None, None]:
    def get_test_session() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    fastapi_app.dependency_overrides[get_session] = get_test_session
    test_client = TestClient(fastapi_app)
    yield test_client
    fastapi_app.dependency_overrides.clear()
