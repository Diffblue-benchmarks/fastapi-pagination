from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Mock sqlalchemy and related modules before importing fastapi_pagination.ext.sqlalchemy
# to handle environments where sqlalchemy is not installed
for _mod in [
    "sqlalchemy",
    "sqlalchemy.engine",
    "sqlalchemy.exc",
    "sqlalchemy.orm",
    "sqlalchemy.sql",
    "sqlalchemy.sql.elements",
    "sqlalchemy.ext",
    "sqlalchemy.ext.asyncio",
    "sqlalchemy.util",
    "sqlakeyset",
    "sqlakeyset.asyncio",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

import pytest

from fastapi_pagination.ext.sqlalchemy import _new_paginate_sign


def make_mock_query():
    query = MagicMock()
    query._statement_20.return_value = MagicMock()
    return query


def test_new_paginate_sign_basic():
    conn = MagicMock()
    query = make_mock_query()

    result = _new_paginate_sign(conn, query)

    assert result[2] is conn
    assert result[3] is None  # params
    assert result[4] is None  # transformer
    assert result[5] is None  # additional_data
    assert result[6] is True  # unique
    assert result[7] is True  # subquery_count
    assert result[8] is None  # unwrap_mode
    assert result[9] is None  # config


def test_new_paginate_sign_returns_tuple():
    conn = MagicMock()
    query = make_mock_query()

    result = _new_paginate_sign(conn, query)

    assert isinstance(result, tuple)
    assert len(result) == 10


def test_new_paginate_sign_with_count_query():
    conn = MagicMock()
    query = make_mock_query()
    count_query = make_mock_query()

    result = _new_paginate_sign(conn, query, count_query=count_query)

    assert result[2] is conn
    assert result[1] is not None  # count_query was prepared and returned


def test_new_paginate_sign_with_none_count_query():
    conn = MagicMock()
    query = make_mock_query()

    result = _new_paginate_sign(conn, query, count_query=None)

    assert result[1] is None


def test_new_paginate_sign_with_params():
    conn = MagicMock()
    query = make_mock_query()
    params = MagicMock()

    result = _new_paginate_sign(conn, query, params=params)

    assert result[3] is params


def test_new_paginate_sign_with_subquery_count_false():
    conn = MagicMock()
    query = make_mock_query()

    result = _new_paginate_sign(conn, query, subquery_count=False)

    assert result[7] is False


def test_new_paginate_sign_with_unique_false():
    conn = MagicMock()
    query = make_mock_query()

    result = _new_paginate_sign(conn, query, unique=False)

    assert result[6] is False


def test_new_paginate_sign_with_transformer():
    conn = MagicMock()
    query = make_mock_query()
    transformer = MagicMock()

    result = _new_paginate_sign(conn, query, transformer=transformer)

    assert result[4] is transformer


def test_new_paginate_sign_with_additional_data():
    conn = MagicMock()
    query = make_mock_query()
    additional_data = MagicMock()

    result = _new_paginate_sign(conn, query, additional_data=additional_data)

    assert result[5] is additional_data


def test_new_paginate_sign_with_unwrap_mode():
    conn = MagicMock()
    query = make_mock_query()

    result = _new_paginate_sign(conn, query, unwrap_mode="auto")

    assert result[8] == "auto"


def test_new_paginate_sign_with_config():
    conn = MagicMock()
    query = make_mock_query()
    config = MagicMock()

    result = _new_paginate_sign(conn, query, config=config)

    assert result[9] is config


def test_new_paginate_sign_query_is_prepared():
    conn = MagicMock()
    query = make_mock_query()
    prepared_query = MagicMock()
    query._statement_20.return_value = prepared_query

    result = _new_paginate_sign(conn, query)

    # _prepare_query calls _statement_20 if available, result should be the prepared query
    assert result[0] is not None
