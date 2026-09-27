"""Pytest configuration for backend tests (PostgreSQL only).

Importing ``db_helper`` here enforces the DATABASE_URL_TEST requirement
for the whole session, and the module-scoped autouse fixture gives every
test module a fresh schema (drop + recreate) before its first test runs.
Tests inside one module keep sharing state exactly as written; no test
can leak rows into another module.
"""

import pytest

from db_helper import reset_test_schema


@pytest.fixture(scope="module", autouse=True)
def _fresh_schema_per_module():
    reset_test_schema()
    yield
