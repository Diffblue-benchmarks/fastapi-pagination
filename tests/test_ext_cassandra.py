from unittest.mock import MagicMock, patch

import pytest

from fastapi_pagination.api import set_page, set_params
from fastapi_pagination.bases import CursorRawParams
from fastapi_pagination.cursor import CursorPage as _CursorPage
from fastapi_pagination.cursor import CursorParams
from fastapi_pagination.customization import CustomizedPage, UseOptionalFields

CursorPage = CustomizedPage[_CursorPage, UseOptionalFields()]


class NoCursorParams(CursorParams):
    def to_raw_params(self) -> CursorRawParams:
        raw = super().to_raw_params()
        return CursorRawParams(cursor=raw.cursor, size=raw.size, include_total=False)


def _make_mock_model(rows=None):
    model = MagicMock()
    model.filter.return_value = "SELECT * FROM table WHERE x = ?"
    return model


def _make_mock_cursor(rows=None, paging_state=None):
    cursor = MagicMock()
    cursor.current_rows = rows if rows is not None else [{"id": 1}, {"id": 2}]
    cursor.paging_state = paging_state
    return cursor


def _make_mock_connection(cursor):
    conn = MagicMock()
    conn.session.execute.return_value = cursor
    return conn


def test_paginate_basic():
    model = _make_mock_model()
    mock_cursor = _make_mock_cursor()
    mock_conn = _make_mock_connection(mock_cursor)
    params = NoCursorParams(size=10)

    with set_page(CursorPage), set_params(params):
        with patch("fastapi_pagination.ext.cassandra.connection.get_connection", return_value=mock_conn):
            with patch("fastapi_pagination.ext.cassandra.SimpleStatement") as mock_stmt:
                from fastapi_pagination.ext.cassandra import paginate

                result = paginate(model)

    assert result is not None
    mock_stmt.assert_called_once()
    mock_conn.session.execute.assert_called_once()


def test_paginate_no_query_filter_defaults_to_empty_dict():
    model = _make_mock_model()
    mock_cursor = _make_mock_cursor(rows=[])
    mock_conn = _make_mock_connection(mock_cursor)
    params = NoCursorParams(size=5)

    with set_page(CursorPage), set_params(params):
        with patch("fastapi_pagination.ext.cassandra.connection.get_connection", return_value=mock_conn):
            with patch("fastapi_pagination.ext.cassandra.SimpleStatement"):
                from fastapi_pagination.ext.cassandra import paginate

                result = paginate(model, query_filter=None)

    assert result is not None
    model.filter.assert_called_once_with()


def test_paginate_with_query_filter():
    model = _make_mock_model()
    mock_cursor = _make_mock_cursor(rows=[{"id": 42}])
    mock_conn = _make_mock_connection(mock_cursor)
    params = NoCursorParams(size=10)
    query_filter = {"name": "alice"}

    with set_page(CursorPage), set_params(params):
        with patch("fastapi_pagination.ext.cassandra.connection.get_connection", return_value=mock_conn):
            with patch("fastapi_pagination.ext.cassandra.SimpleStatement"):
                from fastapi_pagination.ext.cassandra import paginate

                result = paginate(model, query_filter=query_filter)

    model.filter.assert_called_once_with(**query_filter)
    assert result is not None


def test_paginate_passes_paging_state_to_execute():
    model = _make_mock_model()
    paging_state = b"next-page-token"
    mock_cursor = _make_mock_cursor(paging_state=paging_state)
    mock_conn = _make_mock_connection(mock_cursor)
    params = NoCursorParams(size=10)

    with set_page(CursorPage), set_params(params):
        with patch("fastapi_pagination.ext.cassandra.connection.get_connection", return_value=mock_conn):
            with patch("fastapi_pagination.ext.cassandra.SimpleStatement"):
                from fastapi_pagination.ext.cassandra import paginate

                result = paginate(model)

    call_kwargs = mock_conn.session.execute.call_args
    assert call_kwargs is not None
    assert result is not None


def test_paginate_with_transformer():
    model = _make_mock_model()
    mock_cursor = _make_mock_cursor(rows=[{"id": 1}, {"id": 2}])
    mock_conn = _make_mock_connection(mock_cursor)
    params = NoCursorParams(size=10)

    def transformer(items):
        return [{"id": item["id"] * 10} for item in items]

    with set_page(CursorPage), set_params(params):
        with patch("fastapi_pagination.ext.cassandra.connection.get_connection", return_value=mock_conn):
            with patch("fastapi_pagination.ext.cassandra.SimpleStatement"):
                from fastapi_pagination.ext.cassandra import paginate

                result = paginate(model, transformer=transformer)

    assert result.items == [{"id": 10}, {"id": 20}]


def test_paginate_with_additional_data():
    model = _make_mock_model()
    mock_cursor = _make_mock_cursor(rows=[])
    mock_conn = _make_mock_connection(mock_cursor)
    params = NoCursorParams(size=10)

    with set_page(CursorPage), set_params(params):
        with patch("fastapi_pagination.ext.cassandra.connection.get_connection", return_value=mock_conn):
            with patch("fastapi_pagination.ext.cassandra.SimpleStatement"):
                from fastapi_pagination.ext.cassandra import paginate

                result = paginate(model, additional_data={})

    assert result is not None


def test_paginate_asserts_no_total():
    from fastapi_pagination.ext.cassandra import paginate

    model = _make_mock_model()
    # Use default CursorParams which has include_total=True
    params = CursorParams(size=10)

    with set_page(CursorPage), set_params(params):
        with patch("fastapi_pagination.ext.cassandra.connection.get_connection"):
            with patch("fastapi_pagination.ext.cassandra.SimpleStatement"):
                with pytest.raises(AssertionError, match="Cassandra does not support total count"):
                    paginate(model)


def test_paginate_uses_fetch_size_from_params():
    model = _make_mock_model()
    mock_cursor = _make_mock_cursor(rows=[])
    mock_conn = _make_mock_connection(mock_cursor)
    params = NoCursorParams(size=25)

    with set_page(CursorPage), set_params(params):
        with patch("fastapi_pagination.ext.cassandra.connection.get_connection", return_value=mock_conn):
            with patch("fastapi_pagination.ext.cassandra.SimpleStatement") as mock_stmt:
                from fastapi_pagination.ext.cassandra import paginate

                paginate(model)

    _, kwargs = mock_stmt.call_args
    assert kwargs.get("fetch_size") == 25
