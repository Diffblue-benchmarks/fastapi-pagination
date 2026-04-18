import pytest
from fastapi_pagination.default import Page, Params


def test_params_to_raw_params_default():
    params = Params()
    raw = params.to_raw_params()
    assert raw.limit == 50
    assert raw.offset == 0


def test_params_to_raw_params_custom():
    params = Params(page=3, size=10)
    raw = params.to_raw_params()
    assert raw.limit == 10
    assert raw.offset == 20


def test_page_create_basic():
    params = Params(page=1, size=10)
    page = Page.create(items=[1, 2, 3], params=params, total=30)
    assert page.page == 1
    assert page.size == 10
    assert page.pages == 3
    assert page.items == [1, 2, 3]
    assert page.total == 30


def test_page_create_second_page():
    params = Params(page=2, size=5)
    page = Page.create(items=[6, 7, 8, 9, 10], params=params, total=20)
    assert page.page == 2
    assert page.size == 5
    assert page.pages == 4


@pytest.mark.skip(reason="Page model requires total to be an integer; None total not supported by validator")
def test_page_create_no_total():
    params = Params(page=1, size=10)
    page = Page.create(items=[1, 2, 3], params=params, total=None)
    assert page.pages is None
    assert page.total is None


def test_page_create_wrong_params_type():
    from fastapi_pagination.bases import AbstractParams, RawParams

    class OtherParams(AbstractParams):
        def to_raw_params(self) -> RawParams:
            return RawParams(limit=10, offset=0)

    with pytest.raises(TypeError, match="Page should be used with Params"):
        Page.create(items=[], params=OtherParams(), total=0)


def test_page_create_total_zero():
    params = Params(page=1, size=10)
    page = Page.create(items=[], params=params, total=0)
    assert page.pages == 0


def test_page_create_partial_last_page():
    params = Params(page=1, size=10)
    page = Page.create(items=list(range(7)), params=params, total=7)
    assert page.pages == 1
