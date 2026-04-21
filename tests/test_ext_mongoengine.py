import mongoengine
import pytest
from unittest.mock import MagicMock

from fastapi_pagination import Page, Params
from fastapi_pagination.api import set_page, set_params
from fastapi_pagination.ext.mongoengine import paginate


class _MockDocument(mongoengine.Document):
    meta = {"collection": "mock_docs"}


def make_mock_queryset(items, total=None):
    mock_qs = MagicMock()
    if total is not None:
        mock_qs.count.return_value = total
    mock_qs.skip.return_value.limit.return_value = items
    return mock_qs


def make_mock_model(mock_qs):
    """Return _MockDocument with objects() mocked to return mock_qs via .all()."""
    mock_objects = MagicMock()
    mock_objects.return_value.all.return_value = mock_qs
    _MockDocument.objects = mock_objects
    return _MockDocument


def test_paginate_with_queryset_returns_page():
    items = [MagicMock() for _ in range(2)]
    for i, item in enumerate(items):
        item.to_mongo.return_value = {"_id": i, "name": f"item{i}"}
    mock_qs = make_mock_queryset(items, total=2)

    with set_page(Page):
        with set_params(Params(page=1, size=10)):
            result = paginate(mock_qs)

    assert result.total == 2
    assert len(result.items) == 2
    assert result.items[0] == {"_id": 0, "name": "item0"}
    assert result.items[1] == {"_id": 1, "name": "item1"}


def test_paginate_calls_skip_and_limit_with_correct_params():
    items = [MagicMock()]
    items[0].to_mongo.return_value = {"_id": 1}
    mock_qs = make_mock_queryset(items, total=1)

    with set_page(Page):
        with set_params(Params(page=1, size=5)):
            paginate(mock_qs)

    mock_qs.skip.assert_called_once_with(0)
    mock_qs.skip.return_value.limit.assert_called_once_with(5)


def test_paginate_with_model_class_calls_objects_all():
    items = [MagicMock()]
    items[0].to_mongo.return_value = {"_id": 1, "name": "Alice"}
    mock_qs = make_mock_queryset(items, total=1)
    model = make_mock_model(mock_qs)

    with set_page(Page):
        with set_params(Params(page=1, size=10)):
            result = paginate(model)

    model.objects.assert_called_once()
    model.objects.return_value.all.assert_called_once()
    assert result.total == 1
    assert result.items == [{"_id": 1, "name": "Alice"}]


def test_paginate_items_converted_via_to_mongo():
    item = MagicMock()
    item.to_mongo.return_value = {"_id": 42, "value": "test"}
    mock_qs = make_mock_queryset([item], total=1)

    with set_page(Page):
        with set_params(Params(page=1, size=10)):
            result = paginate(mock_qs)

    item.to_mongo.assert_called_once()
    assert result.items == [{"_id": 42, "value": "test"}]


def test_paginate_empty_queryset():
    mock_qs = make_mock_queryset([], total=0)

    with set_page(Page):
        with set_params(Params(page=1, size=10)):
            result = paginate(mock_qs)

    assert result.total == 0
    assert result.items == []


def test_paginate_second_page():
    items = [MagicMock()]
    items[0].to_mongo.return_value = {"_id": 11}
    mock_qs = make_mock_queryset(items, total=11)

    with set_page(Page):
        with set_params(Params(page=2, size=10)):
            result = paginate(mock_qs)

    mock_qs.skip.assert_called_once_with(10)
    mock_qs.skip.return_value.limit.assert_called_once_with(10)
    assert result.page == 2
