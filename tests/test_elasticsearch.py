import sys
from unittest.mock import MagicMock

# Inject mock elasticsearch modules before importing the module under test
# to handle environments where elasticsearch-dsl is not installed
if "elasticsearch" not in sys.modules:
    sys.modules["elasticsearch"] = MagicMock()
    sys.modules["elasticsearch.dsl"] = MagicMock()

import pytest

from fastapi_pagination.bases import CursorRawParams
from fastapi_pagination.ext.elasticsearch import _cursor_flow, paginate
from fastapi_pagination.flow import run_sync_flow


def test_cursor_flow_no_cursor_returns_hits_and_scroll_id():
    query = MagicMock()
    conn = MagicMock()
    raw_params = CursorRawParams(cursor=None, size=5, include_total=False)

    mock_response = MagicMock()
    mock_response.hits = ["item1", "item2"]
    mock_response._scroll_id = "scroll_id_123"

    query.params.return_value.extra.return_value.execute.return_value = mock_response

    gen = _cursor_flow(query, conn, raw_params)
    items, extra = run_sync_flow(gen)

    assert items == ["item1", "item2"]
    assert extra == {"next_": "scroll_id_123"}
    query.params.assert_called_once_with(scroll="1m")
    query.params.return_value.extra.assert_called_once_with(size=5)


def test_cursor_flow_no_cursor_uses_raw_params_size():
    query = MagicMock()
    conn = MagicMock()
    raw_params = CursorRawParams(cursor=None, size=20, include_total=False)

    mock_response = MagicMock()
    mock_response.hits = []
    mock_response._scroll_id = "abc"

    query.params.return_value.extra.return_value.execute.return_value = mock_response

    gen = _cursor_flow(query, conn, raw_params)
    items, extra = run_sync_flow(gen)

    query.params.return_value.extra.assert_called_once_with(size=20)
    assert extra == {"next_": "abc"}


def test_cursor_flow_with_cursor_returns_sources_and_scroll_id():
    query = MagicMock()
    conn = MagicMock()
    raw_params = CursorRawParams(cursor="my_scroll_id", size=5, include_total=False)

    next_scroll_id = "next_scroll_id_456"
    mock_response = {
        "_scroll_id": next_scroll_id,
        "hits": {
            "hits": [
                {"_source": {"id": 1, "name": "a"}},
                {"_source": {"id": 2, "name": "b"}},
            ]
        },
    }
    conn.scroll.return_value = mock_response

    gen = _cursor_flow(query, conn, raw_params)
    items, extra = run_sync_flow(gen)

    assert items == [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]
    assert extra == {"next_": next_scroll_id}
    conn.scroll.assert_called_once_with(scroll_id="my_scroll_id", scroll="1m")


def test_cursor_flow_with_cursor_missing_scroll_id():
    query = MagicMock()
    conn = MagicMock()
    raw_params = CursorRawParams(cursor="existing_scroll", size=3, include_total=False)

    mock_response = {
        "hits": {
            "hits": [
                {"_source": {"val": 42}},
            ]
        },
    }
    conn.scroll.return_value = mock_response

    gen = _cursor_flow(query, conn, raw_params)
    items, extra = run_sync_flow(gen)

    assert items == [{"val": 42}]
    assert extra == {"next_": None}


def test_paginate_returns_run_sync_flow_result(mocker):
    conn = MagicMock()
    query = MagicMock()

    mock_generic_flow = mocker.patch("fastapi_pagination.ext.elasticsearch.generic_flow")
    mock_run_sync_flow = mocker.patch("fastapi_pagination.ext.elasticsearch.run_sync_flow")
    mock_run_sync_flow.return_value = "page_result"

    result = paginate(conn, query)

    assert result == "page_result"
    mock_run_sync_flow.assert_called_once_with(mock_generic_flow.return_value)


def test_paginate_passes_params_and_options_to_generic_flow(mocker):
    conn = MagicMock()
    query = MagicMock()
    params = MagicMock()
    transformer = MagicMock()
    additional_data = {"extra_key": "extra_value"}
    config = MagicMock()

    mock_generic_flow = mocker.patch("fastapi_pagination.ext.elasticsearch.generic_flow")
    mock_run_sync_flow = mocker.patch("fastapi_pagination.ext.elasticsearch.run_sync_flow")
    mock_run_sync_flow.return_value = "page_result"

    result = paginate(conn, query, params=params, transformer=transformer, additional_data=additional_data, config=config)

    assert result == "page_result"
    call_kwargs = mock_generic_flow.call_args.kwargs
    assert call_kwargs["params"] is params
    assert call_kwargs["transformer"] is transformer
    assert call_kwargs["additional_data"] is additional_data
    assert call_kwargs["config"] is config
