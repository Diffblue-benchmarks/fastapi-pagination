"""Tests for fastapi_pagination.ext.cassandra.paginate"""
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

# Provide mock cassandra modules before importing the extension
_cassandra_pkg = types.ModuleType("cassandra")
_cassandra_cluster = types.ModuleType("cassandra.cluster")
_cassandra_cqlengine = types.ModuleType("cassandra.cqlengine")
_cassandra_cqlengine_connection = types.ModuleType("cassandra.cqlengine.connection")
_cassandra_cqlengine_models = types.ModuleType("cassandra.cqlengine.models")

_cassandra_cluster.SimpleStatement = MagicMock()
_cassandra_cqlengine_connection.get_connection = MagicMock()

class _Model:
    pass

_cassandra_cqlengine_models.Model = _Model

_cassandra_pkg.cluster = _cassandra_cluster
_cassandra_pkg.cqlengine = _cassandra_cqlengine
_cassandra_cqlengine.connection = _cassandra_cqlengine_connection
_cassandra_cqlengine.models = _cassandra_cqlengine_models

sys.modules.setdefault("cassandra", _cassandra_pkg)
sys.modules.setdefault("cassandra.cluster", _cassandra_cluster)
sys.modules.setdefault("cassandra.cqlengine", _cassandra_cqlengine)
sys.modules.setdefault("cassandra.cqlengine.connection", _cassandra_cqlengine_connection)
sys.modules.setdefault("cassandra.cqlengine.models", _cassandra_cqlengine_models)

from fastapi_pagination.bases import CursorRawParams  # noqa: E402
from fastapi_pagination.cursor import CursorPage, CursorParams  # noqa: E402
from fastapi_pagination.customization import CustomizedPage, UseIncludeTotal  # noqa: E402
from fastapi_pagination.ext.cassandra import paginate  # noqa: E402

# CursorPage without required total (Cassandra doesn't support count queries)
_CassandraCursorPage = CustomizedPage[CursorPage, UseIncludeTotal(False)]
_CassandraCursorParams = _CassandraCursorPage.__params_type__


def make_cursor_params(cursor=None, size=10):
    return _CassandraCursorParams(cursor=cursor, size=size)


def _make_mock_model(query_filter=None):
    """Create a mock Cassandra Model class."""
    mock_model = MagicMock()
    mock_model.filter.return_value = "SELECT * FROM table"
    return mock_model


def _make_mock_connection(rows=None, paging_state=None):
    """Create a mock Cassandra connection."""
    mock_cursor = MagicMock()
    mock_cursor.current_rows = rows if rows is not None else []
    mock_cursor.paging_state = paging_state

    mock_session = MagicMock()
    mock_session.execute.return_value = mock_cursor

    mock_conn = MagicMock()
    mock_conn.session = mock_session

    return mock_conn, mock_cursor


@pytest.fixture
def mock_connection():
    mock_conn, mock_cursor = _make_mock_connection(rows=[{"id": 1}, {"id": 2}], paging_state=None)
    with patch("fastapi_pagination.ext.cassandra.connection") as mock_connection_module:
        mock_connection_module.get_connection.return_value = mock_conn
        yield mock_connection_module, mock_conn, mock_cursor


def test_paginate_basic(mock_connection):
    """Test basic paginate call returns a page."""
    _, mock_conn, mock_cursor = mock_connection
    mock_model = _make_mock_model()

    with patch("fastapi_pagination.ext.cassandra.SimpleStatement") as mock_stmt:
        result = paginate(mock_model, params=make_cursor_params())

    assert result is not None
    mock_conn.session.execute.assert_called_once()


def test_paginate_with_query_filter(mock_connection):
    """Test paginate with a query filter dict."""
    _, mock_conn, mock_cursor = mock_connection
    mock_model = _make_mock_model()
    query_filter = {"name": "Alice"}

    with patch("fastapi_pagination.ext.cassandra.SimpleStatement"):
        result = paginate(mock_model, query_filter=query_filter, params=make_cursor_params())

    assert result is not None
    mock_model.filter.assert_called_once_with(**query_filter)


def test_paginate_without_query_filter(mock_connection):
    """Test paginate defaults to empty query_filter dict."""
    _, mock_conn, mock_cursor = mock_connection
    mock_model = _make_mock_model()

    with patch("fastapi_pagination.ext.cassandra.SimpleStatement"):
        result = paginate(mock_model, params=make_cursor_params())

    mock_model.filter.assert_called_once_with()


def test_paginate_paging_state_passed_to_execute(mock_connection):
    """Test that cursor paging_state is passed to session.execute."""
    _, mock_conn, mock_cursor = mock_connection
    mock_model = _make_mock_model()

    with patch("fastapi_pagination.ext.cassandra.SimpleStatement"):
        paginate(mock_model, params=make_cursor_params(cursor=None))

    call_kwargs = mock_conn.session.execute.call_args
    assert "paging_state" in call_kwargs.kwargs


def test_paginate_items_from_current_rows(mock_connection):
    """Test that items are taken from cursor.current_rows."""
    rows = [{"id": 1}, {"id": 2}, {"id": 3}]
    mock_conn, mock_cursor = _make_mock_connection(rows=rows)

    mock_connection_module = mock_connection[0]
    mock_connection_module.get_connection.return_value = mock_conn

    mock_model = _make_mock_model()

    with patch("fastapi_pagination.ext.cassandra.SimpleStatement"):
        result = paginate(mock_model, params=make_cursor_params())

    assert result.items == rows


def test_paginate_with_transformer(mock_connection):
    """Test paginate applies transformer to items."""
    _, mock_conn, mock_cursor = mock_connection
    mock_cursor.current_rows = [{"id": 1}]
    mock_model = _make_mock_model()

    transformed = [{"id": 1, "extra": "data"}]
    transformer = lambda items: transformed  # noqa: E731

    with patch("fastapi_pagination.ext.cassandra.SimpleStatement"):
        result = paginate(mock_model, params=make_cursor_params(), transformer=transformer)

    assert result.items == transformed


def test_paginate_with_additional_data(mock_connection):
    """Test paginate passes additional_data to create_page."""
    _, mock_conn, mock_cursor = mock_connection
    mock_model = _make_mock_model()

    with patch("fastapi_pagination.ext.cassandra.SimpleStatement"):
        # additional_data fields must match the page schema; just test it doesn't raise
        result = paginate(mock_model, params=make_cursor_params(), additional_data={})

    assert result is not None


def test_paginate_simple_statement_fetch_size(mock_connection):
    """Test SimpleStatement is created with correct fetch_size from params."""
    _, mock_conn, mock_cursor = mock_connection
    mock_model = _make_mock_model()
    size = 25

    with patch("fastapi_pagination.ext.cassandra.SimpleStatement") as mock_stmt_cls:
        paginate(mock_model, params=make_cursor_params(size=size))

    mock_stmt_cls.assert_called_once()
    _, kwargs = mock_stmt_cls.call_args
    assert kwargs.get("fetch_size") == size


def test_paginate_get_connection_called(mock_connection):
    """Test that connection.get_connection() is called."""
    mock_connection_module, mock_conn, _ = mock_connection
    mock_model = _make_mock_model()

    with patch("fastapi_pagination.ext.cassandra.SimpleStatement"):
        paginate(mock_model, params=make_cursor_params())

    mock_connection_module.get_connection.assert_called_once()
