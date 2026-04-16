from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from fastapi_pagination.bases import CursorRawParams
from fastapi_pagination.default import Page, Params
from fastapi_pagination.ext.elasticsearch import _cursor_flow, paginate
from fastapi_pagination.flow import run_sync_flow


def test_cursor_flow_no_cursor_returns_hits_and_scroll_id():
    mock_query = MagicMock()
    mock_conn = MagicMock()
    mock_response = MagicMock()
    mock_response.hits = ["item1", "item2"]
    mock_response._scroll_id = "scroll_id_abc"
    mock_query.params.return_value.extra.return_value.execute.return_value = mock_response

    raw_params = CursorRawParams(cursor=None, size=10)
    items, data = run_sync_flow(_cursor_flow(mock_query, mock_conn, raw_params))

    assert items == ["item1", "item2"]
    assert data == {"next_": "scroll_id_abc"}
    mock_query.params.assert_called_once_with(scroll="1m")
    mock_query.params.return_value.extra.assert_called_once_with(size=10)


def test_cursor_flow_no_cursor_uses_raw_params_size():
    mock_query = MagicMock()
    mock_conn = MagicMock()
    mock_response = MagicMock()
    mock_response.hits = []
    mock_response._scroll_id = "sid"
    mock_query.params.return_value.extra.return_value.execute.return_value = mock_response

    raw_params = CursorRawParams(cursor=None, size=25)
    run_sync_flow(_cursor_flow(mock_query, mock_conn, raw_params))

    mock_query.params.return_value.extra.assert_called_once_with(size=25)


def test_cursor_flow_with_cursor_uses_conn_scroll():
    mock_query = MagicMock()
    mock_conn = MagicMock()
    mock_response = {
        "_scroll_id": "scroll_id_xyz",
        "hits": {
            "hits": [
                {"_source": {"id": 1}},
                {"_source": {"id": 2}},
            ]
        },
    }
    mock_conn.scroll.return_value = mock_response

    raw_params = CursorRawParams(cursor="existing_cursor", size=10)
    items, data = run_sync_flow(_cursor_flow(mock_query, mock_conn, raw_params))

    assert items == [{"id": 1}, {"id": 2}]
    assert data == {"next_": "scroll_id_xyz"}
    mock_conn.scroll.assert_called_once_with(scroll_id="existing_cursor", scroll="1m")


def test_cursor_flow_with_cursor_missing_scroll_id():
    mock_query = MagicMock()
    mock_conn = MagicMock()
    mock_response = {
        "hits": {"hits": []},
    }
    mock_conn.scroll.return_value = mock_response

    raw_params = CursorRawParams(cursor="some_cursor", size=5)
    items, data = run_sync_flow(_cursor_flow(mock_query, mock_conn, raw_params))

    assert items == []
    assert data == {"next_": None}


def test_paginate_with_limit_offset_params():
    mock_conn = MagicMock()
    mock_query = MagicMock()

    mock_items = [{"id": 1}, {"id": 2}]
    mock_query.using.return_value.count.return_value = 2
    mock_query.using.return_value.__getitem__.return_value.execute.return_value = mock_items

    params = Params(page=1, size=10)
    result = paginate(mock_conn, mock_query, params=params)

    assert result is not None
    assert isinstance(result, Page)
    assert result.total == 2
    assert result.items == mock_items


def test_paginate_returns_correct_page_metadata():
    mock_conn = MagicMock()
    mock_query = MagicMock()

    mock_items = [{"id": i} for i in range(3)]
    mock_query.using.return_value.count.return_value = 3
    mock_query.using.return_value.__getitem__.return_value.execute.return_value = mock_items

    params = Params(page=1, size=10)
    result = paginate(mock_conn, mock_query, params=params)

    assert result.page == 1
    assert result.size == 10
    assert result.total == 3
