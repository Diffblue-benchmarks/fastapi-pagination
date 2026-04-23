import sys
from unittest.mock import MagicMock

import pytest

# Mock cassandra modules before importing the extension
_mock_cassandra = MagicMock()
_mock_cassandra_cluster = MagicMock()
_mock_cassandra_cqlengine = MagicMock()
_mock_cassandra_cqlengine_connection = MagicMock()
_mock_cassandra_cqlengine_models = MagicMock()

sys.modules.setdefault("cassandra", _mock_cassandra)
sys.modules.setdefault("cassandra.cluster", _mock_cassandra_cluster)
sys.modules.setdefault("cassandra.cqlengine", _mock_cassandra_cqlengine)
sys.modules.setdefault("cassandra.cqlengine.connection", _mock_cassandra_cqlengine_connection)
sys.modules.setdefault("cassandra.cqlengine.models", _mock_cassandra_cqlengine_models)

from fastapi_pagination.bases import CursorRawParams  # noqa: E402
from fastapi_pagination.cursor import CursorParams  # noqa: E402


@pytest.fixture(autouse=True)
def reset_cassandra_module():
    # Remove cached module so patches take effect per-test
    sys.modules.pop("fastapi_pagination.ext.cassandra", None)
    yield
    sys.modules.pop("fastapi_pagination.ext.cassandra", None)


@pytest.fixture
def mock_model(mocker):
    model = mocker.MagicMock()
    model.filter.return_value = mocker.MagicMock(__str__=lambda self: "SELECT * FROM test_table")
    return model


@pytest.fixture
def mock_cursor_result():
    cursor = MagicMock()
    cursor.current_rows = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    cursor.paging_state = None
    return cursor


@pytest.fixture
def mock_connection(mock_cursor_result):
    conn = MagicMock()
    conn.session.execute.return_value = mock_cursor_result
    return conn


@pytest.fixture
def cursor_params():
    return CursorParams(cursor=None, size=10)


@pytest.fixture
def raw_params_no_total():
    return CursorRawParams(cursor=None, size=10, include_total=False)


def test_paginate_basic(mocker, mock_model, mock_connection, mock_cursor_result, cursor_params, raw_params_no_total):
    import fastapi_pagination.ext.cassandra as cassandra_ext
    mocker.patch.object(cassandra_ext, "verify_params", return_value=(cursor_params, raw_params_no_total))
    mocker.patch.object(cassandra_ext, "create_page", return_value=MagicMock())
    mocker.patch.object(cassandra_ext.connection, "get_connection", return_value=mock_connection)

    result = cassandra_ext.paginate(mock_model, params=cursor_params)

    assert result is not None
    mock_model.filter.assert_called()


def test_paginate_uses_query_filter(mocker, mock_model, mock_connection, mock_cursor_result, cursor_params, raw_params_no_total):
    import fastapi_pagination.ext.cassandra as cassandra_ext
    mocker.patch.object(cassandra_ext, "verify_params", return_value=(cursor_params, raw_params_no_total))
    mocker.patch.object(cassandra_ext, "create_page", return_value=MagicMock())
    mock_get_conn = MagicMock(return_value=mock_connection)
    mocker.patch.object(cassandra_ext.connection, "get_connection", mock_get_conn)

    query_filter = {"status": "active", "age": 30}
    cassandra_ext.paginate(mock_model, query_filter=query_filter, params=cursor_params)

    mock_model.filter.assert_called_once_with(**query_filter)


def test_paginate_defaults_empty_query_filter(mocker, mock_model, mock_connection, mock_cursor_result, cursor_params, raw_params_no_total):
    import fastapi_pagination.ext.cassandra as cassandra_ext
    mocker.patch.object(cassandra_ext, "verify_params", return_value=(cursor_params, raw_params_no_total))
    mocker.patch.object(cassandra_ext, "create_page", return_value=MagicMock())
    mocker.patch.object(cassandra_ext.connection, "get_connection", return_value=mock_connection)

    cassandra_ext.paginate(mock_model, query_filter=None, params=cursor_params)

    mock_model.filter.assert_called_once_with()


def test_paginate_passes_paging_state(mocker, mock_model, mock_cursor_result, cursor_params):
    paging_state = b"some_paging_state"
    raw_params = CursorRawParams(cursor=paging_state, size=5, include_total=False)

    conn = MagicMock()
    conn.session.execute.return_value = mock_cursor_result

    import fastapi_pagination.ext.cassandra as cassandra_ext
    mocker.patch.object(cassandra_ext, "verify_params", return_value=(cursor_params, raw_params))
    mocker.patch.object(cassandra_ext, "create_page", return_value=MagicMock())
    mocker.patch.object(cassandra_ext.connection, "get_connection", return_value=conn)

    cassandra_ext.paginate(mock_model, params=cursor_params)

    call_kwargs = conn.session.execute.call_args
    assert call_kwargs.kwargs["paging_state"] == paging_state


def test_paginate_passes_next_paging_state_to_create_page(mocker, mock_model, mock_cursor_result, cursor_params, raw_params_no_total):
    next_paging_state = b"next_page_state"
    mock_cursor_result.paging_state = next_paging_state

    conn = MagicMock()
    conn.session.execute.return_value = mock_cursor_result

    import fastapi_pagination.ext.cassandra as cassandra_ext
    mocker.patch.object(cassandra_ext, "verify_params", return_value=(cursor_params, raw_params_no_total))
    mock_create_page = mocker.patch.object(cassandra_ext, "create_page", return_value=MagicMock())
    mocker.patch.object(cassandra_ext.connection, "get_connection", return_value=conn)

    cassandra_ext.paginate(mock_model, params=cursor_params)

    call_kwargs = mock_create_page.call_args
    assert call_kwargs.kwargs.get("next_") == next_paging_state


def test_paginate_with_transformer(mocker, mock_model, mock_connection, mock_cursor_result, cursor_params, raw_params_no_total):
    import fastapi_pagination.ext.cassandra as cassandra_ext
    mocker.patch.object(cassandra_ext, "verify_params", return_value=(cursor_params, raw_params_no_total))
    mock_create_page = mocker.patch.object(cassandra_ext, "create_page", return_value=MagicMock())
    mocker.patch.object(cassandra_ext.connection, "get_connection", return_value=mock_connection)

    transformer = lambda items: [{"id": item["id"]} for item in items]

    cassandra_ext.paginate(mock_model, params=cursor_params, transformer=transformer)

    items_arg = mock_create_page.call_args.args[0]
    assert all("name" not in item for item in items_arg)


def test_paginate_with_additional_data(mocker, mock_model, mock_connection, mock_cursor_result, cursor_params, raw_params_no_total):
    import fastapi_pagination.ext.cassandra as cassandra_ext
    mocker.patch.object(cassandra_ext, "verify_params", return_value=(cursor_params, raw_params_no_total))
    mock_create_page = mocker.patch.object(cassandra_ext, "create_page", return_value=MagicMock())
    mocker.patch.object(cassandra_ext.connection, "get_connection", return_value=mock_connection)

    additional_data = {"extra_key": "extra_value"}
    cassandra_ext.paginate(mock_model, params=cursor_params, additional_data=additional_data)

    call_kwargs = mock_create_page.call_args.kwargs
    assert call_kwargs.get("extra_key") == "extra_value"


def test_paginate_assert_fails_when_include_total(mocker, mock_model, cursor_params):
    raw_params_with_total = CursorRawParams(cursor=None, size=10, include_total=True)

    import fastapi_pagination.ext.cassandra as cassandra_ext
    mocker.patch.object(cassandra_ext, "verify_params", return_value=(cursor_params, raw_params_with_total))

    with pytest.raises(AssertionError, match="Cassandra does not support total count"):
        cassandra_ext.paginate(mock_model, params=cursor_params)


def test_paginate_simple_statement_uses_fetch_size(mocker, mock_model, mock_connection, mock_cursor_result, cursor_params):
    raw_params = CursorRawParams(cursor=None, size=25, include_total=False)

    import fastapi_pagination.ext.cassandra as cassandra_ext
    mocker.patch.object(cassandra_ext, "verify_params", return_value=(cursor_params, raw_params))
    mocker.patch.object(cassandra_ext, "create_page", return_value=MagicMock())
    mocker.patch.object(cassandra_ext.connection, "get_connection", return_value=mock_connection)
    mock_stmt_cls = mocker.patch.object(cassandra_ext, "SimpleStatement", return_value=MagicMock())

    cassandra_ext.paginate(mock_model, params=cursor_params)

    call_kwargs = mock_stmt_cls.call_args
    assert call_kwargs.kwargs.get("fetch_size") == 25


def test_paginate_items_from_cursor(mocker, mock_model, mock_cursor_result, cursor_params, raw_params_no_total):
    rows = [{"id": 10}, {"id": 20}, {"id": 30}]
    mock_cursor_result.current_rows = rows

    conn = MagicMock()
    conn.session.execute.return_value = mock_cursor_result

    import fastapi_pagination.ext.cassandra as cassandra_ext
    mocker.patch.object(cassandra_ext, "verify_params", return_value=(cursor_params, raw_params_no_total))
    mock_create_page = mocker.patch.object(cassandra_ext, "create_page", return_value=MagicMock())
    mocker.patch.object(cassandra_ext.connection, "get_connection", return_value=conn)

    cassandra_ext.paginate(mock_model, params=cursor_params)

    items_passed = mock_create_page.call_args.args[0]
    assert items_passed == rows
