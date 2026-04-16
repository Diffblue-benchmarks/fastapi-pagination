from __future__ import annotations

import pytest

from fastapi_pagination.bases import AbstractParams, BaseRawParams, RawParams
from fastapi_pagination.ext.raw_sql import (
    _unwrap_params,
    create_count_query_from_text,
    create_paginate_query_from_text,
)


class MockAbstractParams(AbstractParams):
    def __init__(self, limit=10, offset=0):
        self._limit = limit
        self._offset = offset

    def to_raw_params(self) -> BaseRawParams:
        return RawParams(limit=self._limit, offset=self._offset)


def test_unwrap_params_with_raw_params():
    raw = RawParams(limit=5, offset=10)
    result = _unwrap_params(raw)
    assert result is raw


def test_unwrap_params_with_abstract_params():
    params = MockAbstractParams(limit=20, offset=5)
    result = _unwrap_params(params)
    assert isinstance(result, RawParams)
    assert result.limit == 20
    assert result.offset == 5


def test_create_paginate_query_from_text_with_limit_and_offset():
    raw = RawParams(limit=10, offset=5)
    result = create_paginate_query_from_text("SELECT * FROM t", raw)
    assert result == "SELECT * FROM t  LIMIT 10 OFFSET 5"


def test_create_paginate_query_from_text_with_limit_only():
    raw = RawParams(limit=10, offset=None)
    result = create_paginate_query_from_text("SELECT * FROM t", raw)
    assert result == "SELECT * FROM t  LIMIT 10"


def test_create_paginate_query_from_text_with_offset_only():
    raw = RawParams(limit=None, offset=5)
    result = create_paginate_query_from_text("SELECT * FROM t", raw)
    assert result == "SELECT * FROM t  OFFSET 5"


def test_create_paginate_query_from_text_with_no_limit_no_offset():
    raw = RawParams(limit=None, offset=None)
    result = create_paginate_query_from_text("SELECT * FROM t", raw)
    assert result == "SELECT * FROM t"


def test_create_paginate_query_from_text_with_abstract_params():
    params = MockAbstractParams(limit=15, offset=30)
    result = create_paginate_query_from_text("SELECT id FROM items", params)
    assert "LIMIT 15" in result
    assert "OFFSET 30" in result


def test_create_count_query_from_text():
    result = create_count_query_from_text("SELECT * FROM users")
    assert result == "SELECT count(*) FROM (SELECT * FROM users) AS __count_query__"


def test_create_count_query_from_text_complex_query():
    query = "SELECT id, name FROM items WHERE active = true"
    result = create_count_query_from_text(query)
    assert result == f"SELECT count(*) FROM ({query}) AS __count_query__"
