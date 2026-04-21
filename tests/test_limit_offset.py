from fastapi_pagination.limit_offset import LimitOffsetPage, LimitOffsetParams
from fastapi_pagination.bases import RawParams


def test_to_raw_params_default():
    params = LimitOffsetParams()
    raw = params.to_raw_params()
    assert isinstance(raw, RawParams)
    assert raw.limit == 50
    assert raw.offset == 0


def test_to_raw_params_custom():
    params = LimitOffsetParams(limit=10, offset=5)
    raw = params.to_raw_params()
    assert raw.limit == 10
    assert raw.offset == 5


def test_limit_offset_page_create():
    params = LimitOffsetParams(limit=10, offset=0)
    items = [1, 2, 3]
    page = LimitOffsetPage.create(items, params, total=3)
    assert page.items == items
    assert page.limit == 10
    assert page.offset == 0
    assert page.total == 3


def test_limit_offset_page_create_with_offset():
    params = LimitOffsetParams(limit=5, offset=10)
    items = ["a", "b"]
    page = LimitOffsetPage.create(items, params, total=12)
    assert page.items == items
    assert page.limit == 5
    assert page.offset == 10
    assert page.total == 12


def test_limit_offset_page_create_empty_items():
    params = LimitOffsetParams(limit=10, offset=20)
    items = []
    page = LimitOffsetPage.create(items, params, total=20)
    assert page.items == items
    assert page.limit == 10
    assert page.offset == 20
    assert page.total == 20
