"""Tests for fastapi_pagination.ext.mongoengine.paginate"""

import sys
from unittest.mock import MagicMock

import pytest

from fastapi_pagination.default import Params


class MockTopLevelDocumentMetaclass(type):
    """Mock for MongoEngine's TopLevelDocumentMetaclass."""
    pass


class MockItem:
    """Mock for a MongoEngine document item with to_mongo() method."""

    def __init__(self, value):
        self._value = value

    def to_mongo(self):
        return self._value


class MockQuerySet:
    """Mock for MongoEngine's QuerySet."""

    def __class_getitem__(cls, item):
        return cls

    def __init__(self, items):
        self._items = list(items)
        self._offset = 0
        self._limit = None

    def skip(self, offset):
        qs = MockQuerySet(self._items)
        qs._offset = offset if offset is not None else 0
        qs._limit = self._limit
        return qs

    def limit(self, limit):
        qs = MockQuerySet(self._items)
        qs._offset = self._offset
        qs._limit = limit
        return qs

    def count(self):
        return len(self._items)

    def all(self):
        return MockQuerySet(self._items)

    def __iter__(self):
        items = self._items[self._offset:]
        if self._limit is not None and self._limit > 0:
            items = items[:self._limit]
        return iter(items)


# Set up mock mongoengine modules before importing fastapi_pagination.ext.mongoengine
_mock_mongoengine_metaclasses = MagicMock()
_mock_mongoengine_metaclasses.TopLevelDocumentMetaclass = MockTopLevelDocumentMetaclass

_mock_mongoengine_base = MagicMock()
_mock_mongoengine_base.metaclasses = _mock_mongoengine_metaclasses

_mock_mongoengine = MagicMock()
_mock_mongoengine.QuerySet = MockQuerySet
_mock_mongoengine.base = _mock_mongoengine_base

sys.modules.setdefault("mongoengine", _mock_mongoengine)
sys.modules.setdefault("mongoengine.base", _mock_mongoengine_base)
sys.modules.setdefault("mongoengine.base.metaclasses", _mock_mongoengine_metaclasses)

from fastapi_pagination.ext.mongoengine import paginate  # noqa: E402


def make_model_class(items):
    """Create a mock MongoEngine model class using the mock metaclass."""
    mock_items = list(items)

    class TestDocument(metaclass=MockTopLevelDocumentMetaclass):
        @classmethod
        def objects(cls):
            return MockQuerySet(mock_items)

    return TestDocument


@pytest.fixture
def params():
    return Params(page=1, size=5)


def test_paginate_with_queryset(params):
    items = [MockItem(i) for i in range(10)]
    query_set = MockQuerySet(items)
    result = paginate(query_set, params=params)
    assert result.total == 10
    assert len(result.items) == 5


def test_paginate_with_model_class(params):
    items = [MockItem(i) for i in range(8)]
    TestDocument = make_model_class(items)
    result = paginate(TestDocument, params=params)
    assert result.total == 8
    assert len(result.items) == 5


def test_paginate_model_class_calls_objects_all():
    mock_qs = MockQuerySet([MockItem(i) for i in range(3)])
    mock_objects = MagicMock()
    mock_objects.return_value.all.return_value = mock_qs

    class TestDocument(metaclass=MockTopLevelDocumentMetaclass):
        objects = mock_objects

    result = paginate(TestDocument, params=Params(page=1, size=10))
    mock_objects.assert_called_once()
    mock_objects.return_value.all.assert_called_once()
    assert result.total == 3


def test_paginate_queryset_does_not_call_objects_all():
    mock_manager = MagicMock()
    items = [MockItem(i) for i in range(5)]
    query_set = MockQuerySet(items)
    result = paginate(query_set, params=Params(page=1, size=10))
    mock_manager.all.assert_not_called()
    assert result.total == 5


def test_paginate_empty_queryset():
    query_set = MockQuerySet([])
    result = paginate(query_set, params=Params(page=1, size=10))
    assert result.total == 0
    assert result.items == []


def test_paginate_items_converted_via_to_mongo():
    items = [MockItem({"id": i, "name": f"item_{i}"}) for i in range(3)]
    query_set = MockQuerySet(items)
    result = paginate(query_set, params=Params(page=1, size=10))
    assert result.total == 3
    assert result.items == [
        {"id": 0, "name": "item_0"},
        {"id": 1, "name": "item_1"},
        {"id": 2, "name": "item_2"},
    ]


def test_paginate_second_page():
    items = [MockItem(i) for i in range(20)]
    query_set = MockQuerySet(items)
    result = paginate(query_set, params=Params(page=2, size=5))
    assert result.total == 20
    assert result.items == list(range(5, 10))
