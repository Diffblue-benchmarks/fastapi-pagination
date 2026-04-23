from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Mock pony.orm before importing the module under test, as pony may not be
# installed in this environment.
# ---------------------------------------------------------------------------

if "pony" not in sys.modules:
    sys.modules["pony"] = MagicMock()
if "pony.orm" not in sys.modules:
    sys.modules["pony.orm"] = MagicMock()
if "pony.orm.core" not in sys.modules:
    sys.modules["pony.orm.core"] = MagicMock()

# ---------------------------------------------------------------------------
# Now it is safe to import the module under test.
# ---------------------------------------------------------------------------

from fastapi_pagination.api import set_params
from fastapi_pagination.default import Page, Params
from fastapi_pagination.ext.pony import paginate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_query(total: int, items: list) -> MagicMock:
    query = MagicMock()
    query.count.return_value = total
    fetch_result = MagicMock()
    fetch_result.to_list.return_value = items
    query.fetch.return_value = fetch_result
    return query


# ---------------------------------------------------------------------------
# Tests for paginate
# ---------------------------------------------------------------------------

class TestPaginate:
    def test_returns_page_with_items(self):
        items = [{"id": 1}, {"id": 2}]
        query = _make_query(total=2, items=items)
        params = Params(page=1, size=10)

        with set_params(params):
            result = paginate(query)

        assert result.total == 2
        assert result.items == items

    def test_explicit_params_argument(self):
        items = [{"id": 10}]
        query = _make_query(total=1, items=items)
        params = Params(page=1, size=5)

        result = paginate(query, params=params)

        assert result.total == 1
        assert result.items == items

    def test_empty_result(self):
        query = _make_query(total=0, items=[])
        params = Params(page=1, size=10)

        result = paginate(query, params=params)

        assert result.total == 0
        assert result.items == []

    def test_fetch_called_with_correct_limit_and_offset(self):
        query = _make_query(total=100, items=list(range(10)))
        params = Params(page=3, size=10)

        result = paginate(query, params=params)

        query.fetch.assert_called_once_with(10, 20)
        assert result.total == 100

    def test_count_called_once(self):
        query = _make_query(total=5, items=[1, 2, 3])
        params = Params(page=1, size=10)

        paginate(query, params=params)

        query.count.assert_called_once_with()

    def test_returns_page_instance(self):
        query = _make_query(total=3, items=[1, 2, 3])
        params = Params(page=1, size=10)

        result = paginate(query, params=params)

        assert isinstance(result, Page)
