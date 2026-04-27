from unittest.mock import MagicMock

import mongoengine as me
import pytest

from fastapi_pagination.bases import RawParams
from fastapi_pagination.ext.mongoengine import _limit_offset_flow, paginate


class _FakeDocument(me.Document):
    meta = {"collection": "fake_docs"}


def test_limit_offset_flow_skips_and_limits():
    mock_item1 = MagicMock()
    mock_item1.to_mongo.return_value = {"_id": 1}
    mock_item2 = MagicMock()
    mock_item2.to_mongo.return_value = {"_id": 2}

    mock_cursor = [mock_item1, mock_item2]
    mock_query = MagicMock()
    mock_query.skip.return_value.limit.return_value = mock_cursor

    raw_params = RawParams(limit=10, offset=5)

    gen = _limit_offset_flow(mock_query, raw_params)
    yielded = next(gen)

    mock_query.skip.assert_called_once_with(5)
    mock_query.skip.return_value.limit.assert_called_once_with(10)
    assert yielded is mock_cursor

    try:
        gen.send(mock_cursor)
        pytest.fail("Expected StopIteration")
    except StopIteration as exc:
        result = exc.value

    assert result == [{"_id": 1}, {"_id": 2}]


def test_limit_offset_flow_empty_cursor():
    mock_query = MagicMock()
    mock_query.skip.return_value.limit.return_value = []

    raw_params = RawParams(limit=5, offset=0)

    gen = _limit_offset_flow(mock_query, raw_params)
    yielded = next(gen)

    try:
        gen.send([])
        pytest.fail("Expected StopIteration")
    except StopIteration as exc:
        result = exc.value

    assert result == []


def test_paginate_with_queryset(mocker):
    mock_queryset = MagicMock()
    mock_page = MagicMock()
    mocker.patch("fastapi_pagination.ext.mongoengine.run_sync_flow", return_value=mock_page)

    result = paginate(mock_queryset)

    assert result is mock_page


def test_paginate_with_document_class_calls_objects_all(mocker):
    mock_page = MagicMock()
    mock_qs = MagicMock()
    run_sync_mock = mocker.patch("fastapi_pagination.ext.mongoengine.run_sync_flow", return_value=mock_page)

    # objects in mongoengine is a descriptor; when called as query.objects(), it returns a QuerySet
    # We mock objects so that objects() returns a mock whose .all() returns mock_qs
    objects_callable = MagicMock(return_value=MagicMock(all=MagicMock(return_value=mock_qs)))
    mocker.patch.object(_FakeDocument, "objects", objects_callable)

    result = paginate(_FakeDocument)

    objects_callable.assert_called_once()
    objects_callable.return_value.all.assert_called_once()
    assert result is mock_page
    run_sync_mock.assert_called_once()


def test_paginate_passes_params_and_transformer(mocker):
    from fastapi_pagination.default import Params

    mock_queryset = MagicMock()
    mock_page = MagicMock()
    run_sync_mock = mocker.patch("fastapi_pagination.ext.mongoengine.run_sync_flow", return_value=mock_page)

    params = Params(page=1, size=5)
    transformer = MagicMock()

    result = paginate(mock_queryset, params=params, transformer=transformer)

    assert result is mock_page
    run_sync_mock.assert_called_once()
