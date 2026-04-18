from unittest.mock import MagicMock

import pytest

from fastapi_pagination import Page, Params
from fastapi_pagination.api import set_page
from fastapi_pagination.bases import CursorRawParams
from fastapi_pagination.cursor import CursorPage, CursorParams
from fastapi_pagination.ext.elasticsearch import _cursor_flow, paginate


# --- _cursor_flow ---


def test_cursor_flow_no_cursor_returns_hits_and_scroll_id():
    query = MagicMock()
    conn = MagicMock()
    raw_params = CursorRawParams(cursor=None, size=5)

    mock_response = MagicMock()
    mock_response.hits = ["item1", "item2"]
    mock_response._scroll_id = "scroll-id-abc"

    gen = _cursor_flow(query, conn, raw_params)
    gen.send(None)  # advance to first yield

    with pytest.raises(StopIteration) as exc_info:
        gen.send(mock_response)

    items, data = exc_info.value.value
    assert items == ["item1", "item2"]
    assert data == {"next_": "scroll-id-abc"}


def test_cursor_flow_no_cursor_calls_scroll_execute():
    query = MagicMock()
    conn = MagicMock()
    raw_params = CursorRawParams(cursor=None, size=10)

    mock_response = MagicMock()
    mock_response.hits = []
    mock_response._scroll_id = "sid"

    gen = _cursor_flow(query, conn, raw_params)
    yielded = gen.send(None)

    # yielded should be the result of query.params(scroll="1m").extra(size=10).execute()
    assert yielded is query.params.return_value.extra.return_value.execute.return_value
    query.params.assert_called_once_with(scroll="1m")
    query.params.return_value.extra.assert_called_once_with(size=10)

    with pytest.raises(StopIteration):
        gen.send(mock_response)


def test_cursor_flow_with_cursor_uses_scroll():
    query = MagicMock()
    conn = MagicMock()
    raw_params = CursorRawParams(cursor="existing-scroll-id", size=5)

    response = {
        "_scroll_id": "new-scroll-id",
        "hits": {"hits": [{"_source": {"id": 1}}, {"_source": {"id": 2}}]},
    }

    gen = _cursor_flow(query, conn, raw_params)
    yielded = gen.send(None)

    # yielded should be conn.scroll(...)
    assert yielded is conn.scroll.return_value
    conn.scroll.assert_called_once_with(scroll_id="existing-scroll-id", scroll="1m")

    with pytest.raises(StopIteration) as exc_info:
        gen.send(response)

    items, data = exc_info.value.value
    assert items == [{"id": 1}, {"id": 2}]
    assert data == {"next_": "new-scroll-id"}


def test_cursor_flow_with_cursor_extracts_source_fields():
    query = MagicMock()
    conn = MagicMock()
    raw_params = CursorRawParams(cursor="scroll-id", size=3)

    response = {
        "_scroll_id": "next-scroll",
        "hits": {
            "hits": [
                {"_source": {"name": "Alice", "age": 30}},
                {"_source": {"name": "Bob", "age": 25}},
            ]
        },
    }

    gen = _cursor_flow(query, conn, raw_params)
    gen.send(None)

    with pytest.raises(StopIteration) as exc_info:
        gen.send(response)

    items, data = exc_info.value.value
    assert items == [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
    assert data["next_"] == "next-scroll"


# --- paginate ---


def test_paginate_with_cursor_params_no_cursor():
    conn = MagicMock()
    query = MagicMock()
    params = CursorParams(size=5)

    mock_response = MagicMock()
    mock_response.hits = ["doc1", "doc2"]
    mock_response._scroll_id = "scroll-id-123"
    query.params.return_value.extra.return_value.execute.return_value = mock_response
    query.using.return_value.count.return_value = 2

    with set_page(CursorPage):
        result = paginate(conn, query, params)

    assert result.items == ["doc1", "doc2"]
    assert result.next_page is not None


def test_paginate_with_limit_offset_params():
    conn = MagicMock()
    query = MagicMock()
    params = Params(page=1, size=5)

    query.using.return_value.count.return_value = 3
    query.using.return_value.__getitem__.return_value.execute.return_value = ["a", "b", "c"]

    with set_page(Page):
        result = paginate(conn, query, params)

    assert result.items == ["a", "b", "c"]
    assert result.total == 3
    assert result.page == 1
    assert result.size == 5


def test_paginate_with_additional_data():
    conn = MagicMock()
    query = MagicMock()
    params = Params(page=1, size=2)

    query.using.return_value.count.return_value = 1
    query.using.return_value.__getitem__.return_value.execute.return_value = ["x"]

    with set_page(Page):
        result = paginate(conn, query, params, additional_data={})

    assert result.items == ["x"]
