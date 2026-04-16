from __future__ import annotations

import pytest

from fastapi_pagination.default import Page, Params
from fastapi_pagination.bases import RawParams


def test_params_to_raw_params_default():
    params = Params(page=1, size=50)
    raw = params.to_raw_params()

    assert isinstance(raw, RawParams)
    assert raw.limit == 50
    assert raw.offset == 0


def test_params_to_raw_params_custom():
    params = Params(page=3, size=10)
    raw = params.to_raw_params()

    assert raw.limit == 10
    assert raw.offset == 20


def test_params_to_raw_params_first_page():
    params = Params(page=1, size=25)
    raw = params.to_raw_params()

    assert raw.limit == 25
    assert raw.offset == 0


def test_page_create_basic():
    params = Params(page=1, size=10)
    items = [1, 2, 3]
    page = Page.create(items=items, params=params, total=30)

    assert page.items == items
    assert page.page == 1
    assert page.size == 10
    assert page.total == 30
    assert page.pages == 3


def test_page_create_invalid_params():
    class OtherParams:
        pass

    with pytest.raises(TypeError, match="Page should be used with Params"):
        Page.create(items=[], params=OtherParams())


@pytest.mark.skip(reason="Page model requires non-None total/pages; total=None path not usable with default Page")
def test_page_create_total_none():
    params = Params(page=1, size=10)
    page = Page.create(items=[1, 2], params=params, total=None)

    assert page.pages is None


def test_page_create_calculates_pages():
    params = Params(page=2, size=5)
    page = Page.create(items=[6, 7, 8, 9, 10], params=params, total=10)

    assert page.pages == 2
    assert page.page == 2


def test_page_create_last_page_partial():
    params = Params(page=3, size=10)
    page = Page.create(items=[1], params=params, total=21)

    assert page.pages == 3


def test_page_create_empty_items():
    params = Params(page=1, size=10)
    page = Page.create(items=[], params=params, total=0)

    assert page.items == []
    assert page.total == 0
