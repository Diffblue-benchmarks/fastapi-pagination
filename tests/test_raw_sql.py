from __future__ import annotations

import pytest

from fastapi_pagination.bases import RawParams
from fastapi_pagination.ext.raw_sql import (
    _unwrap_params,
    create_count_query_from_text,
    create_paginate_query_from_text,
)


class _FakeParams:
    """Minimal AbstractParams-like implementation for testing _unwrap_params."""

    def __init__(self, limit, offset):
        self._limit = limit
        self._offset = offset

    def to_raw_params(self):
        return RawParams(limit=self._limit, offset=self._offset)


# RawParams already has as_limit_offset via BaseRawParams; we need to check if it has the method
# Looking at the source, RawParams is already a limit-offset type, so as_limit_offset returns self.


def test_unwrap_params_with_raw_params():
    raw = RawParams(limit=10, offset=5)
    result = _unwrap_params(raw)
    assert result is raw


def test_unwrap_params_with_abstract_params():
    params = _FakeParams(limit=20, offset=10)
    result = _unwrap_params(params)
    assert isinstance(result, RawParams)
    assert result.limit == 20
    assert result.offset == 10


def test_create_paginate_query_with_limit_and_offset():
    result = create_paginate_query_from_text("SELECT * FROM items", RawParams(limit=10, offset=5))
    assert result == "SELECT * FROM items  LIMIT 10 OFFSET 5"


def test_create_paginate_query_with_limit_only():
    result = create_paginate_query_from_text("SELECT * FROM items", RawParams(limit=10, offset=None))
    assert result == "SELECT * FROM items  LIMIT 10"


def test_create_paginate_query_with_offset_only():
    result = create_paginate_query_from_text("SELECT * FROM items", RawParams(limit=None, offset=5))
    assert result == "SELECT * FROM items  OFFSET 5"


def test_create_paginate_query_with_no_limit_or_offset():
    result = create_paginate_query_from_text("SELECT * FROM items", RawParams(limit=None, offset=None))
    assert result == "SELECT * FROM items"


def test_create_count_query_from_text():
    result = create_count_query_from_text("SELECT * FROM items")
    assert result == "SELECT count(*) FROM (SELECT * FROM items) AS __count_query__"


def test_create_count_query_from_text_with_complex_query():
    query = "SELECT id, name FROM users WHERE active = 1"
    result = create_count_query_from_text(query)
    assert result == f"SELECT count(*) FROM ({query}) AS __count_query__"
