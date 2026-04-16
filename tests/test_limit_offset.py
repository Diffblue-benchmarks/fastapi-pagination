from __future__ import annotations

import pytest

from fastapi_pagination.limit_offset import LimitOffsetPage, LimitOffsetParams
from fastapi_pagination.bases import RawParams


def test_limit_offset_params_to_raw_params_defaults():
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


def test_limit_offset_page_create_basic():
    items = [1, 2, 3]
    params = LimitOffsetParams(limit=10, offset=0)
    page = LimitOffsetPage.create(items, params, total=3)
    assert page.items == items
    assert page.total == 3
    assert page.limit == 10
    assert page.offset == 0


def test_limit_offset_page_create_with_offset():
    items = ["a", "b"]
    params = LimitOffsetParams(limit=5, offset=10)
    page = LimitOffsetPage.create(items, params, total=12)
    assert list(page.items) == items
    assert page.limit == 5
    assert page.offset == 10
    assert page.total == 12
