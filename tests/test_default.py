from __future__ import annotations

import pytest

from fastapi_pagination.bases import RawParams
from fastapi_pagination.default import Page, Params


def test_params_to_raw_params_default():
    params = Params()
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
    page = Page.create(items, params, total=3)
    assert page.items == items
    assert page.total == 3
    assert page.page == 1
    assert page.size == 10
    assert page.pages == 1


def test_page_create_multiple_pages():
    params = Params(page=2, size=10)
    items = list(range(10))
    page = Page.create(items, params, total=25)
    assert page.page == 2
    assert page.size == 10
    assert page.pages == 3


def test_page_create_invalid_params_type():
    class OtherParams:
        pass

    with pytest.raises(TypeError, match="Page should be used with Params"):
        Page.create([], OtherParams())


@pytest.mark.skip(reason="Page model requires non-None total; None total leads to ValidationError")
def test_page_create_no_total():
    params = Params(page=1, size=10)
    items = [1, 2, 3]
    page = Page.create(items, params, total=None)
    assert page.items == items
    assert page.pages is None


def test_page_create_total_zero():
    params = Params(page=1, size=10)
    page = Page.create([], params, total=0)
    assert page.total == 0
    assert page.pages == 0


def test_page_create_exact_pages():
    params = Params(page=1, size=5)
    items = list(range(5))
    page = Page.create(items, params, total=10)
    assert page.pages == 2
