import pytest

from fastapi_pagination.limit_offset import LimitOffsetPage, LimitOffsetParams
from fastapi_pagination.bases import RawParams


def test_limit_offset_params_to_raw_params_default():
    params = LimitOffsetParams()
    raw = params.to_raw_params()
    assert isinstance(raw, RawParams)
    assert raw.limit == 50
    assert raw.offset == 0


def test_limit_offset_params_to_raw_params_custom():
    params = LimitOffsetParams(limit=10, offset=20)
    raw = params.to_raw_params()
    assert raw.limit == 10
    assert raw.offset == 20


def test_limit_offset_params_to_raw_params_min_values():
    params = LimitOffsetParams(limit=1, offset=0)
    raw = params.to_raw_params()
    assert raw.limit == 1
    assert raw.offset == 0


def test_limit_offset_page_create_basic():
    items = [1, 2, 3]
    params = LimitOffsetParams(limit=10, offset=0)
    page = LimitOffsetPage.create(items=items, params=params, total=3)
    assert page.items == items
    assert page.limit == 10
    assert page.offset == 0
    assert page.total == 3


def test_limit_offset_page_create_with_offset():
    items = [4, 5, 6]
    params = LimitOffsetParams(limit=3, offset=3)
    page = LimitOffsetPage.create(items=items, params=params, total=10)
    assert page.items == items
    assert page.limit == 3
    assert page.offset == 3
    assert page.total == 10


def test_limit_offset_page_create_empty_items():
    items = []
    params = LimitOffsetParams(limit=50, offset=0)
    page = LimitOffsetPage.create(items=items, params=params, total=0)
    assert page.items == []
    assert page.total == 0
