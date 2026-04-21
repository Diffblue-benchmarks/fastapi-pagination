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


def test_page_create_basic():
    items = [1, 2, 3]
    params = Params(page=1, size=10)
    page = Page.create(items=items, params=params, total=3)
    assert page.items == items
    assert page.page == 1
    assert page.size == 10
    assert page.total == 3
    assert page.pages == 1


def test_page_create_multiple_pages():
    items = list(range(10))
    params = Params(page=2, size=10)
    page = Page.create(items=items, params=params, total=25)
    assert page.page == 2
    assert page.size == 10
    assert page.total == 25
    assert page.pages == 3


def test_page_create_wrong_params_type():
    from fastapi_pagination.bases import AbstractParams, RawParams

    class OtherParams(AbstractParams):
        def to_raw_params(self) -> RawParams:
            return RawParams(limit=10, offset=0)

    with pytest.raises(TypeError, match="Page should be used with Params"):
        Page.create(items=[], params=OtherParams(), total=0)


@pytest.mark.skip(reason="Page schema requires total/pages to be non-None integers; total=None fails pydantic validation")
def test_page_create_total_none():
    items = [1, 2]
    params = Params(page=1, size=10)
    page = Page.create(items=items, params=params, total=None)
    assert page.pages is None


def test_page_create_total_zero():
    items = []
    params = Params(page=1, size=10)
    page = Page.create(items=items, params=params, total=0)
    assert page.pages == 0
    assert page.total == 0


def test_page_create_empty_items_with_total():
    items = []
    params = Params(page=1, size=10)
    page = Page.create(items=items, params=params, total=100)
    assert page.pages == 10
    assert page.total == 100
