import sys
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

# Mock pony modules before importing fastapi_pagination.ext.pony
_pony_mock = MagicMock()
_pony_orm_mock = MagicMock()
_pony_orm_core_mock = MagicMock()

sys.modules.setdefault("pony", _pony_mock)
sys.modules.setdefault("pony.orm", _pony_orm_mock)
sys.modules.setdefault("pony.orm.core", _pony_orm_core_mock)

from fastapi_pagination.bases import RawParams  # noqa: E402
from fastapi_pagination.ext.pony import paginate  # noqa: E402
from fastapi_pagination.limit_offset import LimitOffsetParams  # noqa: E402


def _make_mock_query(items=None, count=0):
    if items is None:
        items = []
    query = MagicMock()
    query.count.return_value = count
    query.fetch.return_value.to_list.return_value = items
    return query


def test_paginate_basic(mocker):
    items = [{"id": 1}, {"id": 2}]
    query = _make_mock_query(items=items, count=2)
    params = LimitOffsetParams(limit=10, offset=0)
    raw_params = RawParams(limit=10, offset=0, include_total=True)

    mocker.patch("fastapi_pagination.flows.verify_params", return_value=(params, raw_params))

    page_result = MagicMock()
    mocker.patch("fastapi_pagination.flows.create_page", return_value=page_result)
    mocker.patch("fastapi_pagination.flows.apply_items_transformer", return_value=items)

    result = paginate(query, params=params)

    assert result is page_result
    query.count.assert_called_once()
    query.fetch.assert_called_once_with(10, 0)


def test_paginate_empty_result(mocker):
    query = _make_mock_query(items=[], count=0)
    params = LimitOffsetParams(limit=10, offset=0)
    raw_params = RawParams(limit=10, offset=0, include_total=True)

    mocker.patch("fastapi_pagination.flows.verify_params", return_value=(params, raw_params))

    page_result = MagicMock()
    mocker.patch("fastapi_pagination.flows.create_page", return_value=page_result)
    mocker.patch("fastapi_pagination.flows.apply_items_transformer", return_value=[])

    result = paginate(query, params=params)

    assert result is page_result
    query.count.assert_called_once()


def test_paginate_with_offset(mocker):
    items = [{"id": 3}]
    query = _make_mock_query(items=items, count=3)
    params = LimitOffsetParams(limit=1, offset=2)
    raw_params = RawParams(limit=1, offset=2, include_total=True)

    mocker.patch("fastapi_pagination.flows.verify_params", return_value=(params, raw_params))

    page_result = MagicMock()
    mocker.patch("fastapi_pagination.flows.create_page", return_value=page_result)
    mocker.patch("fastapi_pagination.flows.apply_items_transformer", return_value=items)

    result = paginate(query, params=params)

    assert result is page_result
    query.fetch.assert_called_once_with(1, 2)


def test_paginate_without_total(mocker):
    items = [{"id": 1}]
    query = _make_mock_query(items=items, count=1)
    params = LimitOffsetParams(limit=10, offset=0)
    raw_params = RawParams(limit=10, offset=0, include_total=False)

    mocker.patch("fastapi_pagination.flows.verify_params", return_value=(params, raw_params))

    page_result = MagicMock()
    mocker.patch("fastapi_pagination.flows.create_page", return_value=page_result)
    mocker.patch("fastapi_pagination.flows.apply_items_transformer", return_value=items)

    result = paginate(query, params=params)

    assert result is page_result
    query.count.assert_not_called()


def test_paginate_with_transformer(mocker):
    items = [{"id": 1}, {"id": 2}]
    transformed = [{"id": 10}, {"id": 20}]
    query = _make_mock_query(items=items, count=2)
    params = LimitOffsetParams(limit=10, offset=0)
    raw_params = RawParams(limit=10, offset=0, include_total=True)

    mocker.patch("fastapi_pagination.flows.verify_params", return_value=(params, raw_params))

    page_result = MagicMock()
    mock_create_page = mocker.patch("fastapi_pagination.flows.create_page", return_value=page_result)
    mocker.patch("fastapi_pagination.flows.apply_items_transformer", return_value=transformed)

    def transformer(i):
        return [{"id": x["id"] * 10} for x in i]

    result = paginate(query, params=params, transformer=transformer)

    assert result is page_result
