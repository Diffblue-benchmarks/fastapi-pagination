from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Inject mock pony modules before importing the module under test
# to handle environments where pony is not installed
if "pony" not in sys.modules:
    pony_mock = MagicMock()
    sys.modules["pony"] = pony_mock
    sys.modules["pony.orm"] = MagicMock()
    sys.modules["pony.orm.core"] = MagicMock()

import pytest

from fastapi_pagination import Page, Params, set_page, set_params
from fastapi_pagination.ext.pony import paginate


def make_mock_query(items=None, total=10):
    if items is None:
        items = [{"id": i, "name": f"item{i}"} for i in range(3)]

    query = MagicMock()
    query.count = MagicMock(return_value=total)

    fetched = MagicMock()
    fetched.to_list = MagicMock(return_value=items)
    query.fetch = MagicMock(return_value=fetched)

    return query


@pytest.fixture
def pagination_ctx():
    with set_page(Page):
        with set_params(Params(page=1, size=10)):
            yield


def test_paginate_basic(pagination_ctx):
    items = [{"id": 1}, {"id": 2}]
    query = make_mock_query(items=items, total=2)

    result = paginate(query)

    assert result.total == 2
    assert list(result.items) == items


def test_paginate_with_params(pagination_ctx):
    items = [{"id": 1}]
    query = make_mock_query(items=items, total=1)
    params = Params(page=1, size=5)

    result = paginate(query, params=params)

    assert result is not None
    assert result.total == 1


def test_paginate_with_transformer(pagination_ctx):
    items = [{"id": 1}]
    query = make_mock_query(items=items, total=1)

    def transformer(items):
        return [{"transformed": True}]

    result = paginate(query, transformer=transformer)

    assert list(result.items) == [{"transformed": True}]


def test_paginate_with_additional_data(pagination_ctx):
    items = [{"id": 1}]
    query = make_mock_query(items=items, total=1)

    result = paginate(query, additional_data={})

    assert result is not None


def test_paginate_calls_count_and_fetch(pagination_ctx):
    items = [{"id": 1}, {"id": 2}, {"id": 3}]
    query = make_mock_query(items=items, total=3)

    paginate(query)

    query.count.assert_called_once()
    query.fetch.assert_called_once()
