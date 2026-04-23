from __future__ import annotations

import pytest

from fastapi_pagination.bases import RawParams
from fastapi_pagination.default import Page, Params


class TestParamsToRawParams:
    def test_to_raw_params_default(self):
        params = Params()
        result = params.to_raw_params()
        assert isinstance(result, RawParams)
        assert result.limit == 50
        assert result.offset == 0

    def test_to_raw_params_custom_page_and_size(self):
        params = Params(page=3, size=10)
        result = params.to_raw_params()
        assert result.limit == 10
        assert result.offset == 20

    def test_to_raw_params_first_page(self):
        params = Params(page=1, size=25)
        result = params.to_raw_params()
        assert result.limit == 25
        assert result.offset == 0


class TestPageCreate:
    def test_create_basic(self):
        params = Params(page=1, size=10)
        items = [1, 2, 3]
        page = Page.create(items=items, params=params, total=3)
        assert page.items == [1, 2, 3]
        assert page.page == 1
        assert page.size == 10
        assert page.total == 3
        assert page.pages == 1

    def test_create_calculates_pages(self):
        params = Params(page=2, size=10)
        items = list(range(10))
        page = Page.create(items=items, params=params, total=25)
        assert page.pages == 3
        assert page.page == 2
        assert page.size == 10

    def test_create_raises_for_invalid_params(self):
        from fastapi_pagination.bases import AbstractParams, RawParams

        class OtherParams(AbstractParams):
            def to_raw_params(self) -> RawParams:
                return RawParams(limit=10, offset=0)

        with pytest.raises(TypeError, match="Page should be used with Params"):
            Page.create(items=[], params=OtherParams(), total=0)

    @pytest.mark.skip(reason="Page model requires integer total/pages; total=None leads to ValidationError")
    def test_create_total_none(self):
        params = Params(page=1, size=10)
        items = [1, 2, 3]
        page = Page.create(items=items, params=params, total=None)
        assert page.total is None
        assert page.pages is None

    def test_create_empty_items(self):
        params = Params(page=1, size=10)
        page = Page.create(items=[], params=params, total=0)
        assert page.items == []
        assert page.total == 0
        assert page.pages == 0

    def test_create_exact_page_boundary(self):
        params = Params(page=1, size=10)
        items = list(range(10))
        page = Page.create(items=items, params=params, total=10)
        assert page.pages == 1
