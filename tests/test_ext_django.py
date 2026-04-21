"""Tests for fastapi_pagination.ext.django.paginate"""

import sys
from unittest.mock import MagicMock

import pytest

from fastapi_pagination.default import Params


class MockModelBase(type):
    """Mock for Django's ModelBase metaclass."""
    pass


class MockQuerySet:
    """Mock for Django's QuerySet."""

    def __class_getitem__(cls, item):
        return cls

    def __init__(self, items):
        self._items = list(items)

    def count(self):
        return len(self._items)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self._items[key]
        return self._items[key]


class MockManager:
    """Mock for Django's Manager."""

    def __init__(self, items=None):
        self._items = items or []

    def all(self):
        return MockQuerySet(self._items)


# Set up mock Django modules before importing fastapi_pagination.ext.django
_mock_django_models_base = MagicMock()
_mock_django_models_base.ModelBase = MockModelBase

_mock_django_models = MagicMock()
_mock_django_models.Model = object
_mock_django_models.QuerySet = MockQuerySet
_mock_django_models.base = _mock_django_models_base

_mock_django_db = MagicMock()
_mock_django_db.models = _mock_django_models

_mock_django = MagicMock()
_mock_django.db = _mock_django_db

sys.modules.setdefault("django", _mock_django)
sys.modules.setdefault("django.db", _mock_django_db)
sys.modules.setdefault("django.db.models", _mock_django_models)
sys.modules.setdefault("django.db.models.base", _mock_django_models_base)

from fastapi_pagination.ext.django import paginate  # noqa: E402


def make_model_class(items):
    """Create a mock Django Model class with a manager returning the given items."""
    manager = MockManager(items)

    class TestModel(metaclass=MockModelBase):
        objects = manager

    return TestModel


@pytest.fixture
def params():
    return Params(page=1, size=5)


def test_paginate_with_queryset(params):
    items = list(range(10))
    query_set = MockQuerySet(items)
    result = paginate(query_set, params=params)
    assert result.total == 10
    assert len(result.items) == 5


def test_paginate_with_model_class(params):
    items = list(range(8))
    TestModel = make_model_class(items)
    result = paginate(TestModel, params=params)
    assert result.total == 8
    assert len(result.items) == 5


def test_paginate_model_class_calls_objects_all():
    mock_manager = MagicMock()
    mock_manager.all.return_value = MockQuerySet([1, 2, 3])

    class TestModel(metaclass=MockModelBase):
        objects = mock_manager

    result = paginate(TestModel, params=Params(page=1, size=10))
    mock_manager.all.assert_called_once()
    assert result.total == 3


def test_paginate_queryset_does_not_call_objects_all():
    mock_manager = MagicMock()
    items = list(range(5))
    query_set = MockQuerySet(items)
    result = paginate(query_set, params=Params(page=1, size=10))
    mock_manager.all.assert_not_called()
    assert result.total == 5


def test_paginate_empty_queryset():
    query_set = MockQuerySet([])
    result = paginate(query_set, params=Params(page=1, size=10))
    assert result.total == 0
    assert result.items == []


def test_paginate_second_page():
    items = list(range(20))
    query_set = MockQuerySet(items)
    result = paginate(query_set, params=Params(page=2, size=5))
    assert result.total == 20
    assert result.items == list(range(5, 10))
