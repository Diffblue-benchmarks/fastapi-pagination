from __future__ import annotations

import pytest

from fastapi_pagination.bases import RawParams
from fastapi_pagination.ext.raw_sql import (
    _unwrap_params,
    create_count_query_from_text,
    create_paginate_query_from_text,
)


class TestUnwrapParams:
    def test_returns_raw_params_directly(self):
        raw = RawParams(limit=10, offset=5)
        result = _unwrap_params(raw)
        assert result is raw

    def test_unwraps_abstract_params(self):
        from fastapi_pagination import Params

        params = Params(page=2, size=10)
        result = _unwrap_params(params)
        assert isinstance(result, RawParams)
        assert result.limit == 10
        assert result.offset == 10


class TestCreatePaginateQueryFromText:
    def test_with_limit_and_offset(self):
        raw = RawParams(limit=10, offset=20)
        result = create_paginate_query_from_text("SELECT * FROM table", raw)
        assert result == "SELECT * FROM table  LIMIT 10 OFFSET 20"

    def test_with_limit_only(self):
        raw = RawParams(limit=5, offset=None)
        result = create_paginate_query_from_text("SELECT * FROM table", raw)
        assert result == "SELECT * FROM table  LIMIT 5"

    def test_with_offset_only(self):
        raw = RawParams(limit=None, offset=10)
        result = create_paginate_query_from_text("SELECT * FROM table", raw)
        assert result == "SELECT * FROM table  OFFSET 10"

    def test_with_no_limit_no_offset(self):
        raw = RawParams(limit=None, offset=None)
        result = create_paginate_query_from_text("SELECT * FROM table", raw)
        assert result == "SELECT * FROM table"

    def test_with_abstract_params(self):
        from fastapi_pagination import Params

        params = Params(page=1, size=10)
        result = create_paginate_query_from_text("SELECT id FROM items", params)
        assert "LIMIT 10" in result
        assert "OFFSET 0" in result


class TestCreateCountQueryFromText:
    def test_wraps_query_in_count(self):
        query = "SELECT * FROM items"
        result = create_count_query_from_text(query)
        assert result == "SELECT count(*) FROM (SELECT * FROM items) AS __count_query__"

    def test_wraps_complex_query(self):
        query = "SELECT id, name FROM users WHERE active = true ORDER BY name"
        result = create_count_query_from_text(query)
        assert result.startswith("SELECT count(*) FROM (")
        assert query in result
        assert result.endswith(") AS __count_query__")
