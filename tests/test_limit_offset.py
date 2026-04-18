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
    assert raw.limit == 10
    assert raw.offset == 20


def test_limit_offset_page_create():
    params = LimitOffsetParams(limit=10, offset=5)
    items = [1, 2, 3]
    page = LimitOffsetPage.create(items=items, params=params, total=100)
    assert page.items == items
    assert page.total == 100
    assert page.limit == 10
    assert page.offset == 5


def test_limit_offset_page_create_default_params():
    params = LimitOffsetParams()
    items = ["a", "b"]
    page = LimitOffsetPage.create(items=items, params=params, total=2)
    assert page.items == items
    assert page.total == 2
    assert page.limit == 50
    assert page.offset == 0
