import pytest

from fastapi_pagination.bases import RawParams
from fastapi_pagination.limit_offset import LimitOffsetPage, LimitOffsetParams


def test_to_raw_params_default():
    params = LimitOffsetParams()
    raw = params.to_raw_params()

    assert isinstance(raw, RawParams)
    assert raw.limit == 50
    assert raw.offset == 0


def test_to_raw_params_custom():
    params = LimitOffsetParams(limit=10, offset=20)
    raw = params.to_raw_params()

    assert isinstance(raw, RawParams)
    assert raw.limit == 10
    assert raw.offset == 20


def test_limit_offset_page_create_basic():
    params = LimitOffsetParams(limit=5, offset=0)
    items = [1, 2, 3, 4, 5]
    page = LimitOffsetPage.create(items, params, total=20)

    assert page.items == items
    assert page.total == 20
    assert page.limit == 5
    assert page.offset == 0


def test_limit_offset_page_create_with_offset():
    params = LimitOffsetParams(limit=3, offset=6)
    items = [7, 8, 9]
    page = LimitOffsetPage.create(items, params, total=10)

    assert page.items == items
    assert page.limit == 3
    assert page.offset == 6
    assert page.total == 10


def test_limit_offset_page_create_empty():
    params = LimitOffsetParams(limit=10, offset=0)
    items = []
    page = LimitOffsetPage.create(items, params, total=0)

    assert page.items == []
    assert page.total == 0
    assert page.limit == 10
    assert page.offset == 0
