from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Mock external dependencies that may not be installed in this environment.
# These mocks must be inserted into sys.modules BEFORE any imports from
# fastapi_pagination.ext.databases so that the module can be loaded.
# ---------------------------------------------------------------------------

if "databases" not in sys.modules:
    sys.modules["databases"] = MagicMock()

# SQLAlchemy is an optional dependency; mock its submodules so the import
# chain in fastapi_pagination.ext.sqlalchemy doesn't fail.
_SA_MODS = [
    "sqlalchemy",
    "sqlalchemy.sql",
    "sqlalchemy.sql.elements",
    "sqlalchemy.engine",
    "sqlalchemy.exc",
    "sqlalchemy.orm",
    "sqlalchemy.util",
    "sqlalchemy.ext",
    "sqlalchemy.ext.asyncio",
]
for _mod_name in _SA_MODS:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = MagicMock()

# Mock fastapi_pagination.ext.sqlalchemy to avoid loading the real module
# (which requires sqlalchemy) while still providing the two functions used
# by fastapi_pagination.ext.databases.
if "fastapi_pagination.ext.sqlalchemy" not in sys.modules:
    _mock_ext_sa = MagicMock()
    sys.modules["fastapi_pagination.ext.sqlalchemy"] = _mock_ext_sa

# ---------------------------------------------------------------------------
# Now it is safe to import the module under test.
# ---------------------------------------------------------------------------
from fastapi_pagination.api import set_params
from fastapi_pagination.default import Page, Params
from fastapi_pagination.ext.databases import _to_mappings, apaginate, paginate

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_row(**kwargs):
    row = MagicMock()
    row._mapping = kwargs
    return row


def _make_db(total: int, rows: list) -> MagicMock:
    db = MagicMock()
    db.fetch_val = AsyncMock(return_value=total)
    db.fetch_all = AsyncMock(return_value=rows)
    return db


# ---------------------------------------------------------------------------
# Tests for _to_mappings
# ---------------------------------------------------------------------------

class TestToMappings:
    def test_converts_items_to_dicts(self):
        row1 = _make_row(id=1, name="Alice")
        row2 = _make_row(id=2, name="Bob")

        result = _to_mappings([row1, row2])

        assert result == [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

    def test_empty_sequence(self):
        result = _to_mappings([])

        assert result == []

    def test_single_item(self):
        row = _make_row(value=42)

        result = _to_mappings([row])

        assert result == [{"value": 42}]


# ---------------------------------------------------------------------------
# Tests for apaginate
# ---------------------------------------------------------------------------

class TestApaginate:
    async def test_convert_to_mapping_true_by_default(self):
        rows = [_make_row(id=1), _make_row(id=2)]
        db = _make_db(total=2, rows=rows)
        query = MagicMock()
        params = Params(page=1, size=10)

        with set_params(params):
            result = await apaginate(db, query)

        assert result.total == 2
        assert len(result.items) == 2
        assert result.items[0] == {"id": 1}
        assert result.items[1] == {"id": 2}

    async def test_convert_to_mapping_false(self):
        row = _make_row(id=99)
        db = _make_db(total=1, rows=[row])
        query = MagicMock()
        params = Params(page=1, size=10)

        with set_params(params):
            result = await apaginate(db, query, convert_to_mapping=False)

        assert result.total == 1
        assert result.items[0] is row

    async def test_explicit_params_argument(self):
        db = _make_db(total=0, rows=[])
        query = MagicMock()
        params = Params(page=1, size=5)

        result = await apaginate(db, query, params=params)

        assert result.total == 0
        assert result.items == []

    async def test_inner_transformer_set_when_convert_to_mapping(self):
        rows = [_make_row(x=10)]
        db = _make_db(total=1, rows=rows)
        query = MagicMock()
        params = Params(page=1, size=10)

        with set_params(params):
            result = await apaginate(db, query, convert_to_mapping=True)

        assert result.items == [{"x": 10}]


# ---------------------------------------------------------------------------
# Tests for paginate
# ---------------------------------------------------------------------------

class TestPaginate:
    async def test_delegates_to_apaginate(self):
        rows = [_make_row(id=10)]
        db = _make_db(total=1, rows=rows)
        query = MagicMock()
        params = Params(page=1, size=5)

        with set_params(params):
            result = await paginate(db, query)

        assert result.total == 1
        assert result.items == [{"id": 10}]

    async def test_delegates_with_convert_to_mapping_false(self):
        row = _make_row(id=7)
        db = _make_db(total=1, rows=[row])
        query = MagicMock()
        params = Params(page=1, size=10)

        with set_params(params):
            result = await paginate(db, query, convert_to_mapping=False)

        assert result.total == 1
        assert result.items[0] is row
