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

from fastapi_pagination.ext.sqlalchemy import _old_paginate_sign


def make_mock_query(session=None):
    query = MagicMock()
    query.session = session if session is not None else MagicMock()
    query._statement_20.return_value = MagicMock()
    return query


def test_old_paginate_sign_raises_when_session_is_none():
    query = MagicMock()
    query.session = None

    with pytest.raises(ValueError, match="query.session is None"):
        _old_paginate_sign(query)


def test_old_paginate_sign_returns_tuple():
    query = make_mock_query()

    result = _old_paginate_sign(query)

    assert isinstance(result, tuple)
    assert len(result) == 10


def test_old_paginate_sign_session_in_result():
    session = MagicMock()
    query = make_mock_query(session=session)

    result = _old_paginate_sign(query)

    assert result[2] is session


def test_old_paginate_sign_count_query_is_none():
    query = make_mock_query()

    result = _old_paginate_sign(query)

    assert result[1] is None


def test_old_paginate_sign_default_params():
    query = make_mock_query()

    result = _old_paginate_sign(query)

    assert result[3] is None  # params
    assert result[4] is None  # transformer
    assert result[5] is None  # additional_data
    assert result[6] is True  # unique
    assert result[7] is True  # subquery_count
    assert result[8] is None  # unwrap_mode
    assert result[9] is None  # config


def test_old_paginate_sign_with_params():
    query = make_mock_query()
    params = MagicMock()

    result = _old_paginate_sign(query, params=params)

    assert result[3] is params


def test_old_paginate_sign_with_subquery_count_false():
    query = make_mock_query()

    result = _old_paginate_sign(query, subquery_count=False)

    assert result[7] is False


def test_old_paginate_sign_with_unique_false():
    query = make_mock_query()

    result = _old_paginate_sign(query, unique=False)

    assert result[6] is False


def test_old_paginate_sign_with_transformer():
    query = make_mock_query()
    transformer = MagicMock()

    result = _old_paginate_sign(query, transformer=transformer)

    assert result[4] is transformer


def test_old_paginate_sign_with_additional_data():
    query = make_mock_query()
    additional_data = MagicMock()

    result = _old_paginate_sign(query, additional_data=additional_data)

    assert result[5] is additional_data


def test_old_paginate_sign_with_unwrap_mode():
    query = make_mock_query()

    result = _old_paginate_sign(query, unwrap_mode="auto")

    assert result[8] == "auto"


def test_old_paginate_sign_with_config():
    query = make_mock_query()
    config = MagicMock()

    result = _old_paginate_sign(query, config=config)

    assert result[9] is config


def test_old_paginate_sign_query_is_prepared():
    session = MagicMock()
    query = make_mock_query(session=session)
    prepared_query = MagicMock()
    query._statement_20.return_value = prepared_query

    result = _old_paginate_sign(query)

    assert result[0] is prepared_query
