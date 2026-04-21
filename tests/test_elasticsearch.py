from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

# Mock elasticsearch modules before importing the extension
_es_mock = MagicMock()
_es_dsl_mock = MagicMock()
sys.modules["elasticsearch"] = _es_mock
sys.modules["elasticsearch.dsl"] = _es_dsl_mock

from fastapi_pagination.bases import CursorRawParams
from fastapi_pagination.cursor import CursorPage, CursorParams
from fastapi_pagination.default import Page, Params
from fastapi_pagination.flow import run_sync_flow
from fastapi_pagination.ext.elasticsearch import _cursor_flow, paginate


def test_cursor_flow_no_cursor():
    conn_mock = MagicMock()
    query_mock = MagicMock()
    raw_params = CursorRawParams(cursor=None, size=5)

    response_mock = MagicMock()
    response_mock.hits = [{"id": 1}, {"id": 2}]
    response_mock._scroll_id = "scroll_id_abc"

    query_mock.params.return_value.extra.return_value.execute.return_value = response_mock

    items, extra = run_sync_flow(_cursor_flow(query_mock, conn_mock, raw_params))

    query_mock.params.assert_called_once_with(scroll="1m")
    query_mock.params.return_value.extra.assert_called_once_with(size=5)
    assert items == response_mock.hits
    assert extra == {"next_": "scroll_id_abc"}


def test_cursor_flow_with_cursor():
    conn_mock = MagicMock()
    query_mock = MagicMock()
    raw_params = CursorRawParams(cursor="existing_scroll_id", size=10)

    scroll_response = {
        "_scroll_id": "next_scroll_id_xyz",
        "hits": {
            "hits": [
                {"_source": {"id": 1, "name": "item1"}},
                {"_source": {"id": 2, "name": "item2"}},
            ]
        },
    }
    conn_mock.scroll.return_value = scroll_response

    items, extra = run_sync_flow(_cursor_flow(query_mock, conn_mock, raw_params))

    conn_mock.scroll.assert_called_once_with(scroll_id="existing_scroll_id", scroll="1m")
    assert items == [{"id": 1, "name": "item1"}, {"id": 2, "name": "item2"}]
    assert extra == {"next_": "next_scroll_id_xyz"}


def test_cursor_flow_with_cursor_no_next_scroll_id():
    conn_mock = MagicMock()
    query_mock = MagicMock()
    raw_params = CursorRawParams(cursor="last_scroll_id", size=10)

    scroll_response = {
        "hits": {
            "hits": []
        },
    }
    conn_mock.scroll.return_value = scroll_response

    items, extra = run_sync_flow(_cursor_flow(query_mock, conn_mock, raw_params))

    assert items == []
    assert extra == {"next_": None}


def test_paginate_limit_offset():
    conn_mock = MagicMock()
    query_mock = MagicMock()
    params = Params(page=1, size=10)

    query_mock.using.return_value.count.return_value = 3
    query_mock.using.return_value.__getitem__.return_value.execute.return_value = [
        {"id": 1},
        {"id": 2},
        {"id": 3},
    ]

    result = paginate(conn_mock, query_mock, params=params)

    assert isinstance(result, Page)
    assert result.total == 3
    assert len(result.items) == 3


def test_paginate_cursor():
    conn_mock = MagicMock()
    query_mock = MagicMock()
    params = CursorParams(cursor=None, size=5)

    response_mock = MagicMock()
    response_mock.hits = [{"id": 10}]
    response_mock._scroll_id = "scroll_abc"

    query_mock.params.return_value.extra.return_value.execute.return_value = response_mock

    result = paginate(conn_mock, query_mock, params=params)

    assert isinstance(result, CursorPage)
    assert result.items == [{"id": 10}]
