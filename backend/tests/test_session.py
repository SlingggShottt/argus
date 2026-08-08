"""Tests for the session factory. Uses an in-memory SQLite engine instead of
the real Postgres connection from settings — get_db()/init_db() only need to
prove their generic session-lifecycle logic here, not Postgres itself."""

from unittest import mock

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.db import session as session_module

EXPECTED_TABLES = {
    "sales_records",
    "inventory",
    "forecasts",
    "risk_flags",
    "recommendations",
}


def test_get_db_closes_session_after_use(monkeypatch):
    test_engine = create_engine("sqlite:///:memory:")
    test_session_local = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    monkeypatch.setattr(session_module, "SessionLocal", test_session_local)

    gen = session_module.get_db()
    db = next(gen)
    close_spy = mock.Mock(wraps=db.close)
    db.close = close_spy

    with pytest.raises(StopIteration):
        next(gen)

    close_spy.assert_called_once()


def test_get_db_closes_session_even_if_caller_raises(monkeypatch):
    test_engine = create_engine("sqlite:///:memory:")
    test_session_local = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    monkeypatch.setattr(session_module, "SessionLocal", test_session_local)

    gen = session_module.get_db()
    db = next(gen)
    close_spy = mock.Mock(wraps=db.close)
    db.close = close_spy

    with pytest.raises(RuntimeError):
        gen.throw(RuntimeError("simulated route handler failure"))

    close_spy.assert_called_once()


def test_init_db_creates_all_tables(monkeypatch):
    test_engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(session_module, "engine", test_engine)

    session_module.init_db()

    assert set(inspect(test_engine).get_table_names()) == EXPECTED_TABLES
