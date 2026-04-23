import sys
from unittest.mock import MagicMock

import pytest

# Mock elasticsearch modules before importing the extension (not installed in test env)
sys.modules.setdefault("elasticsearch", MagicMock())
sys.modules.setdefault("elasticsearch.dsl", MagicMock())

from fastapi_pagination.api import set_page  # noqa: E402
from fastapi_pagination.bases import CursorRawParams  # noqa: E402
from fastapi_pagination.default import Page, Params  # noqa: E402
from fastapi_pagination.ext.elasticsearch import _cursor_flow, paginate  # noqa: E402
from fastapi_pagination.utils import disable_installed_extensions_check  # noqa: E402


@pytest.fixture(autouse=True)
def _disable_ext_check():
    disable_installed_extensions_check()


def test_cursor_flow_no_cursor_returns_hits_and_scroll_id():
    mock_query = MagicMock()
    mock_conn = MagicMock()
    raw_params = CursorRawParams(cursor=None, size=10)

    mock_hits = [{"id": 1}, {"id": 2}]
    mock_response = MagicMock()
    mock_response.hits = mock_hits
    mock_response._scroll_id = "scroll_id_abc"
    mock_query.params.return_value.extra.return_value.execute.return_value = mock_response

    gen = _cursor_flow(mock_query, mock_conn, raw_params)
    yielded = gen.send(None)

    with pytest.raises(StopIteration) as exc_info:
        gen.send(yielded)

    items, data = exc_info.value.value
    assert items == mock_hits
    assert data == {"next_": "scroll_id_abc"}


def test_cursor_flow_no_cursor_calls_query_params_with_scroll():
    mock_query = MagicMock()
    mock_conn = MagicMock()
    raw_params = CursorRawParams(cursor=None, size=7)

    mock_response = MagicMock()
    mock_response.hits = []
    mock_response._scroll_id = "s1"
    mock_query.params.return_value.extra.return_value.execute.return_value = mock_response

    gen = _cursor_flow(mock_query, mock_conn, raw_params)
    yielded = gen.send(None)
    try:
        gen.send(yielded)
    except StopIteration:
        pass

    mock_query.params.assert_called_once_with(scroll="1m")
    mock_query.params.return_value.extra.assert_called_once_with(size=7)


def test_cursor_flow_with_cursor_returns_sources_and_scroll_id():
    mock_query = MagicMock()
    mock_conn = MagicMock()
    raw_params = CursorRawParams(cursor="existing_cursor", size=10)

    scroll_response = {
        "_scroll_id": "next_scroll_id",
        "hits": {
            "hits": [
                {"_source": {"id": 1}},
                {"_source": {"id": 2}},
            ]
        },
    }
    mock_conn.scroll.return_value = scroll_response

    gen = _cursor_flow(mock_query, mock_conn, raw_params)
    yielded = gen.send(None)

    with pytest.raises(StopIteration) as exc_info:
        gen.send(yielded)

    items, data = exc_info.value.value
    assert items == [{"id": 1}, {"id": 2}]
    assert data == {"next_": "next_scroll_id"}


def test_cursor_flow_with_cursor_calls_conn_scroll():
    mock_query = MagicMock()
    mock_conn = MagicMock()
    raw_params = CursorRawParams(cursor="my_scroll_cursor", size=10)

    mock_conn.scroll.return_value = {
        "_scroll_id": "new_scroll",
        "hits": {"hits": []},
    }

    gen = _cursor_flow(mock_query, mock_conn, raw_params)
    yielded = gen.send(None)
    try:
        gen.send(yielded)
    except StopIteration:
        pass

    mock_conn.scroll.assert_called_once_with(scroll_id="my_scroll_cursor", scroll="1m")


def test_paginate_returns_page_with_correct_total():
    mock_conn = MagicMock()
    mock_query = MagicMock()
    mock_query.using.return_value.count.return_value = 3
    mock_query.using.return_value.__getitem__.return_value.execute.return_value = [10, 20, 30]

    params = Params(page=1, size=10)

    with set_page(Page):
        result = paginate(mock_conn, mock_query, params=params)

    assert result.total == 3
    assert result.items == [10, 20, 30]


def test_paginate_returns_page_instance():
    mock_conn = MagicMock()
    mock_query = MagicMock()
    mock_query.using.return_value.count.return_value = 2
    mock_query.using.return_value.__getitem__.return_value.execute.return_value = ["a", "b"]

    params = Params(page=1, size=10)

    with set_page(Page):
        result = paginate(mock_conn, mock_query, params=params)

    assert isinstance(result, Page)
    assert result.total == 2
