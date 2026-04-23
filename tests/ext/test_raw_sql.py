"""Tests for fastapi_pagination.ext.raw_sql."""

from __future__ import annotations

import pytest

from fastapi_pagination.bases import AbstractParams, BaseRawParams, RawParams
from fastapi_pagination.ext.raw_sql import (
    _unwrap_params,
    create_count_query_from_text,
    create_paginate_query_from_text,
)


class _MockAbstractParams(AbstractParams):
    """Minimal AbstractParams implementation that returns a RawParams."""

    def __init__(self, limit=10, offset=0):
        self._limit = limit
        self._offset = offset

    def to_raw_params(self) -> RawParams:
        return RawParams(limit=self._limit, offset=self._offset)


class _MockAbstractParamsNoLimitOffset(AbstractParams):
    """AbstractParams that returns a RawParams with None values."""

    def to_raw_params(self) -> RawParams:
        return RawParams(limit=None, offset=None)


# ---------------------------------------------------------------------------
# _unwrap_params
# ---------------------------------------------------------------------------


def test_unwrap_params_with_raw_params_returns_same():
    raw = RawParams(limit=5, offset=10)
    result = _unwrap_params(raw)
    assert result is raw


def test_unwrap_params_with_abstract_params_returns_raw():
    params = _MockAbstractParams(limit=20, offset=5)
    result = _unwrap_params(params)
    assert isinstance(result, RawParams)
    assert result.limit == 20
    assert result.offset == 5


# ---------------------------------------------------------------------------
# create_paginate_query_from_text
# ---------------------------------------------------------------------------


def test_create_paginate_query_with_limit_and_offset():
    raw = RawParams(limit=10, offset=0)
    result = create_paginate_query_from_text("SELECT * FROM users", raw)
    assert result == "SELECT * FROM users  LIMIT 10 OFFSET 0"


def test_create_paginate_query_with_limit_only():
    raw = RawParams(limit=5, offset=None)
    result = create_paginate_query_from_text("SELECT * FROM items", raw)
    assert result == "SELECT * FROM items  LIMIT 5"


def test_create_paginate_query_with_offset_only():
    raw = RawParams(limit=None, offset=20)
    result = create_paginate_query_from_text("SELECT * FROM items", raw)
    assert result == "SELECT * FROM items  OFFSET 20"


def test_create_paginate_query_with_no_limit_no_offset():
    raw = RawParams(limit=None, offset=None)
    result = create_paginate_query_from_text("SELECT * FROM items", raw)
    assert result == "SELECT * FROM items"


def test_create_paginate_query_with_abstract_params():
    params = _MockAbstractParams(limit=3, offset=6)
    result = create_paginate_query_from_text("SELECT id FROM orders", params)
    assert result == "SELECT id FROM orders  LIMIT 3 OFFSET 6"


# ---------------------------------------------------------------------------
# create_count_query_from_text
# ---------------------------------------------------------------------------


def test_create_count_query_wraps_in_subquery():
    query = "SELECT * FROM users WHERE active = true"
    result = create_count_query_from_text(query)
    assert result == f"SELECT count(*) FROM ({query}) AS __count_query__"


def test_create_count_query_simple():
    result = create_count_query_from_text("SELECT id FROM posts")
    assert result == "SELECT count(*) FROM (SELECT id FROM posts) AS __count_query__"
