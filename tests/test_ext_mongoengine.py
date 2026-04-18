from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from fastapi_pagination.ext.mongoengine import _limit_offset_flow, paginate


# --- _limit_offset_flow ---

def test_limit_offset_flow_yields_limited_query_and_returns_items():
    raw_params = MagicMock()
    raw_params.offset = 5
    raw_params.limit = 10

    item1 = MagicMock()
    item1.to_mongo.return_value = {"id": 1}
    item2 = MagicMock()
    item2.to_mongo.return_value = {"id": 2}

    query = MagicMock()
    limited_query = MagicMock()
    query.skip.return_value.limit.return_value = limited_query

    gen = _limit_offset_flow(query, raw_params)

    yielded = next(gen)
    assert yielded is limited_query
    query.skip.assert_called_once_with(5)
    query.skip.return_value.limit.assert_called_once_with(10)

    try:
        gen.send([item1, item2])
    except StopIteration as exc:
        result = exc.value

    assert result == [{"id": 1}, {"id": 2}]


def test_limit_offset_flow_returns_empty_list_for_empty_cursor():
    raw_params = MagicMock()
    raw_params.offset = 0
    raw_params.limit = 5

    query = MagicMock()

    gen = _limit_offset_flow(query, raw_params)
    next(gen)

    result = None
    try:
        gen.send([])
    except StopIteration as exc:
        result = exc.value

    assert result == []


# --- paginate ---

def test_paginate_with_queryset_calls_run_sync_flow(mocker):
    mock_run = mocker.patch(
        "fastapi_pagination.ext.mongoengine.run_sync_flow",
        return_value="paginated_result",
    )
    mock_generic_flow = mocker.patch(
        "fastapi_pagination.ext.mongoengine.generic_flow",
        return_value="flow_sentinel",
    )

    query = MagicMock()

    result = paginate(query)

    assert result == "paginated_result"
    mock_run.assert_called_once_with("flow_sentinel")
    mock_generic_flow.assert_called_once()


def test_paginate_with_document_class_converts_to_queryset(mocker):
    mock_run = mocker.patch(
        "fastapi_pagination.ext.mongoengine.run_sync_flow",
        return_value="paginated_result",
    )
    mocker.patch(
        "fastapi_pagination.ext.mongoengine.generic_flow",
        return_value="flow_sentinel",
    )

    import mongoengine

    class FakeDoc(mongoengine.Document):
        meta = {"collection": "fake_docs"}

    mock_qs = MagicMock()
    mock_objects = MagicMock()
    mock_objects.return_value.all.return_value = mock_qs
    FakeDoc.objects = mock_objects

    result = paginate(FakeDoc)

    assert result == "paginated_result"
    mock_objects.return_value.all.assert_called_once()
    mock_run.assert_called_once_with("flow_sentinel")
