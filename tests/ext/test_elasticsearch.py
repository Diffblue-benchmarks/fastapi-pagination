from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

# Mock elasticsearch modules before importing the module under test
_elasticsearch_mock = MagicMock()
_elasticsearch_dsl_mock = MagicMock()
sys.modules.setdefault("elasticsearch", _elasticsearch_mock)
sys.modules.setdefault("elasticsearch.dsl", _elasticsearch_dsl_mock)
# Remove any previously cached import so we re-import with our mocks
sys.modules.pop("fastapi_pagination.ext.elasticsearch", None)

from fastapi_pagination.bases import CursorRawParams
from fastapi_pagination.ext.elasticsearch import _cursor_flow, paginate
from fastapi_pagination.flow import run_sync_flow


def _make_cursor_raw_params(cursor=None, size=10, include_total=False):
    return CursorRawParams(cursor=cursor, size=size, include_total=include_total)


# --- _cursor_flow: no cursor branch (lines 25-28) ---

def test_cursor_flow_no_cursor_returns_hits_and_scroll_id():
    query = MagicMock()
    conn = MagicMock()
    raw_params = _make_cursor_raw_params(cursor=None, size=5)

    mock_response = MagicMock()
    mock_response.hits = ["item1", "item2"]
    mock_response._scroll_id = "scroll-id-123"
    query.params.return_value.extra.return_value.execute.return_value = mock_response

    items, extra = run_sync_flow(_cursor_flow(query, conn, raw_params))

    assert items == ["item1", "item2"]
    assert extra == {"next_": "scroll-id-123"}
    query.params.assert_called_once_with(scroll="1m")
    query.params.return_value.extra.assert_called_once_with(size=5)


def test_cursor_flow_no_cursor_uses_raw_params_size():
    query = MagicMock()
    conn = MagicMock()
    raw_params = _make_cursor_raw_params(cursor=None, size=20)

    mock_response = MagicMock()
    mock_response.hits = []
    mock_response._scroll_id = "sid"
    query.params.return_value.extra.return_value.execute.return_value = mock_response

    items, extra = run_sync_flow(_cursor_flow(query, conn, raw_params))

    query.params.return_value.extra.assert_called_once_with(size=20)
    assert extra == {"next_": "sid"}


# --- _cursor_flow: with cursor branch (lines 30-32) ---

def test_cursor_flow_with_cursor_calls_scroll_and_returns_sources():
    query = MagicMock()
    conn = MagicMock()
    scroll_id = "existing-scroll-id"
    raw_params = _make_cursor_raw_params(cursor=scroll_id, size=5)

    mock_response = {
        "_scroll_id": "new-scroll-id-456",
        "hits": {
            "hits": [
                {"_source": {"id": 1}},
                {"_source": {"id": 2}},
            ]
        },
    }
    conn.scroll.return_value = mock_response

    items, extra = run_sync_flow(_cursor_flow(query, conn, raw_params))

    assert items == [{"id": 1}, {"id": 2}]
    assert extra == {"next_": "new-scroll-id-456"}
    conn.scroll.assert_called_once_with(scroll_id=scroll_id, scroll="1m")


def test_cursor_flow_with_cursor_empty_hits():
    query = MagicMock()
    conn = MagicMock()
    raw_params = _make_cursor_raw_params(cursor="cur-abc", size=5)

    mock_response = {
        "_scroll_id": None,
        "hits": {"hits": []},
    }
    conn.scroll.return_value = mock_response

    items, extra = run_sync_flow(_cursor_flow(query, conn, raw_params))

    assert items == []
    assert extra == {"next_": None}


def test_cursor_flow_with_cursor_missing_scroll_id():
    query = MagicMock()
    conn = MagicMock()
    raw_params = _make_cursor_raw_params(cursor="cur-xyz", size=5)

    mock_response = {
        "hits": {"hits": [{"_source": {"key": "val"}}]},
    }
    conn.scroll.return_value = mock_response

    items, extra = run_sync_flow(_cursor_flow(query, conn, raw_params))

    assert items == [{"key": "val"}]
    assert extra == {"next_": None}


# --- paginate (lines 37, 46) ---

def test_paginate_calls_run_sync_flow(mocker):
    mock_run = mocker.patch(
        "fastapi_pagination.ext.elasticsearch.run_sync_flow",
        return_value="page_result",
    )
    conn = MagicMock()
    query = MagicMock()

    result = paginate(conn, query)

    mock_run.assert_called_once()
    assert result == "page_result"


def test_paginate_passes_additional_data(mocker):
    mock_run = mocker.patch(
        "fastapi_pagination.ext.elasticsearch.run_sync_flow",
        return_value=None,
    )
    conn = MagicMock()
    query = MagicMock()

    paginate(conn, query, additional_data={"extra": "data"})

    mock_run.assert_called_once()
