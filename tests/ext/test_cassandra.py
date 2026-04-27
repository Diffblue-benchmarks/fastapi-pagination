from typing import TypeVar
from unittest.mock import MagicMock, patch

import pytest

from fastapi_pagination.api import set_page, set_params
from fastapi_pagination.bases import CursorRawParams
from fastapi_pagination.cursor import CursorPage as BaseCursorPage
from fastapi_pagination.cursor import CursorParams
from fastapi_pagination.customization import CustomizedPage, UseIncludeTotal
from fastapi_pagination.ext.cassandra import paginate

T = TypeVar("T")
CursorPage = CustomizedPage[BaseCursorPage[T], UseIncludeTotal(False)]


@pytest.fixture
def mock_cassandra_connection():
    """Mock the Cassandra connection."""
    mock_cursor = MagicMock()
    mock_cursor.current_rows = [{"id": 1, "name": "item1"}, {"id": 2, "name": "item2"}]
    mock_cursor.paging_state = None

    mock_session = MagicMock()
    mock_session.execute.return_value = mock_cursor

    mock_conn = MagicMock()
    mock_conn.session = mock_session

    with patch("fastapi_pagination.ext.cassandra.connection") as mock_connection:
        mock_connection.get_connection.return_value = mock_conn
        yield mock_conn, mock_cursor, mock_session


@pytest.fixture
def mock_cassandra_model():
    """Mock the Cassandra Model."""
    mock_model = MagicMock()
    mock_model.filter.return_value = "SELECT * FROM test_table"
    return mock_model


@pytest.fixture
def cursor_params_no_total():
    """CursorParams with include_total=False to satisfy Cassandra constraint."""
    params = CursorParams(size=10)
    raw = params.to_raw_params()
    raw.include_total = False
    return params, raw


def test_paginate_basic(mock_cassandra_connection, mock_cassandra_model):
    """Test basic pagination with default cursor params."""
    mock_conn, mock_cursor, mock_session = mock_cassandra_connection

    params = CursorParams(size=10)

    with patch("fastapi_pagination.ext.cassandra.verify_params") as mock_verify:
        raw_params = CursorRawParams(cursor=None, size=10, include_total=False)
        mock_verify.return_value = (params, raw_params)

        with patch("fastapi_pagination.ext.cassandra.SimpleStatement") as mock_stmt:
            with set_params(params), set_page(CursorPage):
                result = paginate(mock_cassandra_model)

    assert result is not None
    mock_cassandra_model.filter.assert_called_once_with()
    mock_session.execute.assert_called_once()


def test_paginate_with_query_filter(mock_cassandra_connection, mock_cassandra_model):
    """Test pagination with a query filter."""
    mock_conn, mock_cursor, mock_session = mock_cassandra_connection

    params = CursorParams(size=5)

    with patch("fastapi_pagination.ext.cassandra.verify_params") as mock_verify:
        raw_params = CursorRawParams(cursor=None, size=5, include_total=False)
        mock_verify.return_value = (params, raw_params)

        with patch("fastapi_pagination.ext.cassandra.SimpleStatement"):
            with set_params(params), set_page(CursorPage):
                result = paginate(mock_cassandra_model, query_filter={"name": "test"})

    assert result is not None
    mock_cassandra_model.filter.assert_called_once_with(name="test")


def test_paginate_returns_page_items(mock_cassandra_connection, mock_cassandra_model):
    """Test that paginate returns page with items from cursor."""
    mock_conn, mock_cursor, mock_session = mock_cassandra_connection
    mock_cursor.current_rows = [{"id": 1}, {"id": 2}, {"id": 3}]
    mock_cursor.paging_state = b"next_page_state"

    params = CursorParams(size=3)

    with patch("fastapi_pagination.ext.cassandra.verify_params") as mock_verify:
        raw_params = CursorRawParams(cursor=None, size=3, include_total=False)
        mock_verify.return_value = (params, raw_params)

        with patch("fastapi_pagination.ext.cassandra.SimpleStatement"):
            with set_params(params), set_page(CursorPage):
                result = paginate(mock_cassandra_model)

    assert result.items == [{"id": 1}, {"id": 2}, {"id": 3}]


def test_paginate_with_paging_state(mock_cassandra_connection, mock_cassandra_model):
    """Test pagination with an existing cursor/paging state."""
    mock_conn, mock_cursor, mock_session = mock_cassandra_connection
    mock_cursor.current_rows = [{"id": 4}]
    mock_cursor.paging_state = b"next_state"

    params = CursorParams(size=1)
    existing_cursor = b"existing_cursor"

    with patch("fastapi_pagination.ext.cassandra.verify_params") as mock_verify:
        raw_params = CursorRawParams(cursor=existing_cursor, size=1, include_total=False)
        mock_verify.return_value = (params, raw_params)

        with patch("fastapi_pagination.ext.cassandra.SimpleStatement"):
            with set_params(params), set_page(CursorPage):
                result = paginate(mock_cassandra_model)

    execute_call_kwargs = mock_session.execute.call_args
    assert execute_call_kwargs.kwargs["paging_state"] == existing_cursor


def test_paginate_include_total_raises(mock_cassandra_model):
    """Test that include_total=True raises AssertionError for Cassandra."""
    params = CursorParams(size=10)

    with patch("fastapi_pagination.ext.cassandra.verify_params") as mock_verify:
        raw_params = CursorRawParams(cursor=None, size=10, include_total=True)
        mock_verify.return_value = (params, raw_params)

        with set_params(params), set_page(CursorPage):
            with pytest.raises(AssertionError, match="Cassandra does not support total count"):
                paginate(mock_cassandra_model)


def test_paginate_with_transformer(mock_cassandra_connection, mock_cassandra_model):
    """Test pagination with a transformer function."""
    mock_conn, mock_cursor, mock_session = mock_cassandra_connection
    mock_cursor.current_rows = [{"id": 1, "name": "item1"}]

    params = CursorParams(size=10)

    def transformer(items):
        return [{"id": item["id"]} for item in items]

    with patch("fastapi_pagination.ext.cassandra.verify_params") as mock_verify:
        raw_params = CursorRawParams(cursor=None, size=10, include_total=False)
        mock_verify.return_value = (params, raw_params)

        with patch("fastapi_pagination.ext.cassandra.SimpleStatement"):
            with set_params(params), set_page(CursorPage):
                result = paginate(mock_cassandra_model, transformer=transformer)

    assert result.items == [{"id": 1}]


def test_paginate_with_additional_data(mock_cassandra_connection, mock_cassandra_model):
    """Test pagination with additional_data passed to create_page."""
    mock_conn, mock_cursor, mock_session = mock_cassandra_connection
    mock_cursor.current_rows = []

    params = CursorParams(size=10)

    with patch("fastapi_pagination.ext.cassandra.verify_params") as mock_verify:
        raw_params = CursorRawParams(cursor=None, size=10, include_total=False)
        mock_verify.return_value = (params, raw_params)

        with patch("fastapi_pagination.ext.cassandra.SimpleStatement"):
            with set_params(params), set_page(CursorPage):
                result = paginate(mock_cassandra_model, additional_data={})

    assert result is not None


def test_paginate_none_query_filter(mock_cassandra_connection, mock_cassandra_model):
    """Test that None query_filter is treated as empty dict."""
    mock_conn, mock_cursor, mock_session = mock_cassandra_connection

    params = CursorParams(size=10)

    with patch("fastapi_pagination.ext.cassandra.verify_params") as mock_verify:
        raw_params = CursorRawParams(cursor=None, size=10, include_total=False)
        mock_verify.return_value = (params, raw_params)

        with patch("fastapi_pagination.ext.cassandra.SimpleStatement"):
            with set_params(params), set_page(CursorPage):
                result = paginate(mock_cassandra_model, query_filter=None)

    mock_cassandra_model.filter.assert_called_once_with()
    assert result is not None
