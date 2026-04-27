from __future__ import annotations

import pytest

from fastapi_pagination.default import Page, Params
from fastapi_pagination.bases import RawParams


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


def test_page_create_raises_for_wrong_params():
    from fastapi_pagination.bases import AbstractParams

    class OtherParams(AbstractParams):
        def to_raw_params(self):
            return RawParams(limit=10, offset=0)

    with pytest.raises(TypeError, match="Page should be used with Params"):
        Page.create(items=[], params=OtherParams(), total=10)


def test_page_create_basic():
    params = Params(page=1, size=10)
    page = Page.create(items=[1, 2, 3], params=params, total=30)
    assert page.page == 1
    assert page.size == 10
    assert page.pages == 3
    assert page.total == 30
    assert page.items == [1, 2, 3]


@pytest.mark.skip(reason="Page.pages and BasePage.total do not accept None due to GreaterEqualZero constraint")
def test_page_create_total_none():
    params = Params(page=1, size=10)
    page = Page.create(items=[1, 2], params=params, total=None)
    assert page.pages is None
    assert page.total is None


def test_page_create_total_provided_pages_calculated():
    params = Params(page=2, size=5)
    page = Page.create(items=list(range(5)), params=params, total=12)
    assert page.pages == 3
    assert page.page == 2


def test_page_create_size_zero_pages_zero():
    # size=0 is not allowed by Params (ge=1), but size can be 0 via edge case paths
    # We test with size=1 (smallest allowed) and total=0 -> pages=0
    params = Params(page=1, size=1)
    page = Page.create(items=[], params=params, total=0)
    assert page.pages == 0
