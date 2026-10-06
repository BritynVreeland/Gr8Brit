import os
import uuid

import psycopg
import pytest
from psycopg.rows import dict_row

from bbos import db
from bbos.seed import seed

TEST_URL = os.environ.get("TEST_DATABASE_URL")


@pytest.fixture(autouse=True)
def _salt(monkeypatch):
    from bbos.settings import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("AUTHOR_HASH_SALT", "test-salt")
    yield
    get_settings.cache_clear()


@pytest.fixture
def conn():
    """A fresh, migrated, seeded database per test (requires TEST_DATABASE_URL pointing at a server with pgvector)."""
    if not TEST_URL:
        pytest.skip("TEST_DATABASE_URL not set")
    name = f"bbos_t_{uuid.uuid4().hex[:10]}"
    with psycopg.connect(TEST_URL, autocommit=True) as admin:
        admin.execute(f"create database {name}")
    url = TEST_URL.rsplit("/", 1)[0] + f"/{name}"
    try:
        with psycopg.connect(url, row_factory=dict_row) as c:
            db.migrate(c)
            seed(c)
            c.commit()
            yield c
    finally:
        with psycopg.connect(TEST_URL, autocommit=True) as admin:
            admin.execute(f"drop database if exists {name} with (force)")
