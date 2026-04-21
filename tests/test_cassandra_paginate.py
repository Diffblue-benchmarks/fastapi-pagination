import sys
from unittest.mock import MagicMock

import pytest

# Mock cassandra modules before fastapi_pagination.ext.cassandra is imported,
# since cassandra-driver/scylla-driver is an optional dependency.
for _mod in [
    "cassandra",
    "cassandra.cluster",
    "cassandra.cqlengine",
    "cassandra.cqlengine.models",
    "cassandra.cqlengine.connection",
]:
    sys.modules.setdefault(_mod, MagicMock())

from fastapi_pagination.api import set_page
from fastapi_pagination.cursor import CursorPage
from fastapi_pagination.customization import CustomizedPage, UseIncludeTotal
from fastapi_pagination.ext.cassandra import paginate

# CursorPage variant compatible with cassandra (no total count required)
TestPage = CustomizedPage[CursorPage, UseIncludeTotal(include_total=False)]


@pytest.fixture
def mock_conn(mocker):
    conn = MagicMock()
    mocker.patch(
        "fastapi_pagination.ext.cassandra.connection.get_connection",
        return_value=conn,
    )
    return conn


@pytest.fixture
def mock_cursor(mock_conn):
    cursor = MagicMock()
    cursor.current_rows = []
    cursor.paging_state = None
    mock_conn.session.execute.return_value = cursor
    return cursor


@pytest.fixture
def mock_model():
    model = MagicMock()
    model.filter.return_value = "SELECT * FROM test_table"
    return model


@pytest.fixture
def params():
    return TestPage.__params_type__()


def test_paginate_basic(mock_cursor, mock_model, params):
    mock_cursor.current_rows = [{"id": 1}, {"id": 2}]

    with set_page(TestPage):
        result = paginate(mock_model, params=params)

    assert list(result.items) == [{"id": 1}, {"id": 2}]
    mock_model.filter.assert_called_once_with()


def test_paginate_with_query_filter(mock_conn, mock_cursor, mock_model, params):
    mock_cursor.current_rows = [{"id": 1}]
    query_filter = {"status": "active"}

    with set_page(TestPage):
        result = paginate(mock_model, query_filter=query_filter, params=params)

    assert list(result.items) == [{"id": 1}]
    mock_model.filter.assert_called_once_with(status="active")
    execute_kwargs = mock_conn.session.execute.call_args.kwargs
    assert execute_kwargs["parameters"] == {"0": "active"}


def test_paginate_none_query_filter_defaults_to_empty(mock_conn, mock_cursor, mock_model, params):
    mock_cursor.current_rows = []

    with set_page(TestPage):
        paginate(mock_model, query_filter=None, params=params)

    mock_model.filter.assert_called_once_with()
    execute_kwargs = mock_conn.session.execute.call_args.kwargs
    assert execute_kwargs["parameters"] == {}


def test_paginate_passes_paging_state_to_execute(mock_conn, mock_cursor, mock_model, params):
    mock_cursor.current_rows = []

    with set_page(TestPage):
        paginate(mock_model, params=params)

    execute_kwargs = mock_conn.session.execute.call_args.kwargs
    assert execute_kwargs["paging_state"] is None


def test_paginate_returns_next_page_when_paging_state_present(mock_cursor, mock_model, params):
    mock_cursor.current_rows = [{"id": 1}]
    mock_cursor.paging_state = b"some_paging_state"

    with set_page(TestPage):
        result = paginate(mock_model, params=params)

    assert result.next_page is not None


def test_paginate_no_next_page_when_no_paging_state(mock_cursor, mock_model, params):
    mock_cursor.current_rows = [{"id": 1}]
    mock_cursor.paging_state = None

    with set_page(TestPage):
        result = paginate(mock_model, params=params)

    assert result.next_page is None


def test_paginate_with_transformer(mock_cursor, mock_model, params):
    mock_cursor.current_rows = [{"id": 1, "value": "hello"}]

    def transformer(items):
        return [dict(item, value=item["value"].upper()) for item in items]

    with set_page(TestPage):
        result = paginate(mock_model, params=params, transformer=transformer)

    assert list(result.items) == [{"id": 1, "value": "HELLO"}]


def test_paginate_empty_results(mock_cursor, mock_model, params):
    mock_cursor.current_rows = []

    with set_page(TestPage):
        result = paginate(mock_model, params=params)

    assert list(result.items) == []
