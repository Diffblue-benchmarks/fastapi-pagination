import sys
from unittest.mock import MagicMock, sentinel

import pytest

# Mock cassandra modules before importing fastapi_pagination.ext.cassandra
_cassandra_mock = MagicMock()
_cassandra_cluster_mock = MagicMock()
_cassandra_cqlengine_mock = MagicMock()
_cassandra_cqlengine_connection_mock = MagicMock()
_cassandra_cqlengine_models_mock = MagicMock()

sys.modules.setdefault("cassandra", _cassandra_mock)
sys.modules.setdefault("cassandra.cluster", _cassandra_cluster_mock)
sys.modules.setdefault("cassandra.cqlengine", _cassandra_cqlengine_mock)
sys.modules.setdefault("cassandra.cqlengine.connection", _cassandra_cqlengine_connection_mock)
sys.modules.setdefault("cassandra.cqlengine.models", _cassandra_cqlengine_models_mock)

from fastapi_pagination.bases import CursorRawParams  # noqa: E402
from fastapi_pagination.cursor import CursorParams  # noqa: E402
from fastapi_pagination.ext.cassandra import paginate  # noqa: E402


def _make_mock_model(query_str="SELECT * FROM test"):
    model = MagicMock()
    model.filter.return_value.__str__ = MagicMock(return_value=query_str)
    return model


def _make_mock_connection(rows=None, paging_state=None):
    if rows is None:
        rows = []
    cursor = MagicMock()
    cursor.current_rows = rows
    cursor.paging_state = paging_state

    conn = MagicMock()
    conn.session.execute.return_value = cursor
    return conn, cursor


def _setup_common_mocks(mocker, size=50, cursor_val=None, include_total=False, rows=None, paging_state=None):
    params = CursorParams()
    raw_params = CursorRawParams(cursor=cursor_val, size=size, include_total=include_total)
    mocker.patch("fastapi_pagination.ext.cassandra.verify_params", return_value=(params, raw_params))

    conn, db_cursor = _make_mock_connection(rows=rows or [], paging_state=paging_state)
    mocker.patch("fastapi_pagination.ext.cassandra.connection.get_connection", return_value=conn)
    mocker.patch("fastapi_pagination.ext.cassandra.SimpleStatement")

    page_result = MagicMock()
    mocker.patch("fastapi_pagination.ext.cassandra.create_page", return_value=page_result)

    return params, raw_params, conn, db_cursor, page_result


def test_paginate_basic(mocker):
    params, raw_params, conn, db_cursor, page_result = _setup_common_mocks(
        mocker, rows=[{"id": 1}, {"id": 2}]
    )
    mock_model = _make_mock_model()

    result = paginate(mock_model)

    assert result is page_result
    conn.session.execute.assert_called_once()


def test_paginate_with_query_filter(mocker):
    query_filter = {"name": "alice"}
    rows = [{"id": 1, "name": "alice"}]
    params, raw_params, conn, db_cursor, page_result = _setup_common_mocks(
        mocker, rows=rows, paging_state=b"next_cursor"
    )

    mock_model = _make_mock_model()
    result = paginate(mock_model, query_filter=query_filter)

    mock_model.filter.assert_called_once_with(**query_filter)
    assert result is page_result


def test_paginate_empty_query_filter(mocker):
    params, raw_params, conn, db_cursor, page_result = _setup_common_mocks(mocker, rows=[])
    mock_model = _make_mock_model()

    paginate(mock_model, query_filter={})

    mock_model.filter.assert_called_once_with()


def test_paginate_with_cursor(mocker):
    params, raw_params, conn, db_cursor, page_result = _setup_common_mocks(
        mocker, cursor_val=b"some_cursor", rows=[{"id": 10}], paging_state=b"next_page_cursor"
    )
    mock_model = _make_mock_model()

    paginate(mock_model)

    conn.session.execute.assert_called_once()
    call_kwargs = conn.session.execute.call_args[1]
    assert call_kwargs["paging_state"] == b"some_cursor"


def test_paginate_with_transformer(mocker):
    rows = [{"id": 1}, {"id": 2}]
    params, raw_params, conn, db_cursor, page_result = _setup_common_mocks(mocker, rows=rows)
    mock_model = _make_mock_model()
    db_cursor.current_rows = rows

    transformed = [{"id": 10}, {"id": 20}]
    mock_create_page = mocker.patch("fastapi_pagination.ext.cassandra.create_page", return_value=page_result)

    def transformer(items):
        return [{"id": item["id"] * 10} for item in items]

    paginate(mock_model, transformer=transformer)

    call_args = mock_create_page.call_args
    assert list(call_args[0][0]) == transformed


def test_paginate_with_additional_data(mocker):
    params, raw_params, conn, db_cursor, page_result = _setup_common_mocks(mocker, rows=[{"id": 1}])
    mock_model = _make_mock_model()
    mock_create_page = mocker.patch("fastapi_pagination.ext.cassandra.create_page", return_value=page_result)

    extra = {"extra_key": "extra_value"}
    paginate(mock_model, additional_data=extra)

    call_kwargs = mock_create_page.call_args[1]
    assert call_kwargs.get("extra_key") == "extra_value"


def test_paginate_include_total_raises(mocker):
    params = CursorParams()
    raw_params = CursorRawParams(cursor=None, size=50, include_total=True)
    mocker.patch("fastapi_pagination.ext.cassandra.verify_params", return_value=(params, raw_params))
    mock_model = _make_mock_model()

    with pytest.raises(AssertionError, match="Cassandra does not support total count"):
        paginate(mock_model)


def test_paginate_simple_statement_fetch_size(mocker):
    params, raw_params, conn, db_cursor, page_result = _setup_common_mocks(mocker, size=25, rows=[])
    mock_model = _make_mock_model()
    MockSimpleStatement = mocker.patch("fastapi_pagination.ext.cassandra.SimpleStatement")

    paginate(mock_model)

    MockSimpleStatement.assert_called_once()
    _, kwargs = MockSimpleStatement.call_args
    assert kwargs.get("fetch_size") == 25


def test_paginate_passes_next_cursor_to_create_page(mocker):
    paging_state = b"next_cursor_bytes"
    params, raw_params, conn, db_cursor, _ = _setup_common_mocks(
        mocker, rows=[{"id": 1}], paging_state=paging_state
    )
    mock_model = _make_mock_model()
    mock_create_page = mocker.patch("fastapi_pagination.ext.cassandra.create_page", return_value=MagicMock())

    paginate(mock_model)

    call_kwargs = mock_create_page.call_args[1]
    assert call_kwargs.get("next_") == paging_state
