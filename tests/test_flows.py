from __future__ import annotations

import pytest

from fastapi_pagination.config import Config
from fastapi_pagination.cursor import CursorPage, CursorParams
from fastapi_pagination.default import Page, Params
from fastapi_pagination.flow import run_sync_flow
from fastapi_pagination.flows import create_page_flow, generic_flow


def _make_lo_flow(items):
    def lo_flow(raw_params):
        if False:
            yield
        return items

    return lo_flow


def _make_total_flow(total):
    def total_flow():
        if False:
            yield
        return total

    return total_flow


def _make_cursor_flow(items, extra_data=None):
    def cursor_flow(raw_params):
        if False:
            yield
        return (items, extra_data)

    return cursor_flow


def test_create_page_flow_basic():
    params = Params(page=1, size=10)
    items = [1, 2, 3]

    result = run_sync_flow(create_page_flow(items, params, total=3))

    assert isinstance(result, Page)
    assert list(result.items) == items
    assert result.total == 3


def test_create_page_flow_uses_default_create_page_when_no_factory():
    params = Params(page=1, size=10)
    items = ["a", "b"]

    result = run_sync_flow(create_page_flow(items, params, total=2))

    assert isinstance(result, Page)
    assert result.total == 2
    assert result.page == 1
    assert result.size == 10


def test_create_page_flow_with_config_page_cls():
    params = Params(page=1, size=5)
    items = [10, 20, 30]
    config = Config(page_cls=Page)

    result = run_sync_flow(create_page_flow(items, params, total=3, config=config))

    assert isinstance(result, Page)
    assert list(result.items) == items


def test_create_page_flow_with_config_without_page_cls():
    params = Params(page=1, size=5)
    items = [10, 20]
    config = Config(page_cls=None)

    result = run_sync_flow(create_page_flow(items, params, total=2, config=config))

    assert isinstance(result, Page)
    assert result.total == 2


def test_create_page_flow_with_custom_factory():
    params = Params(page=1, size=10)
    items = [1, 2, 3]
    factory_calls = []

    from fastapi_pagination.api import create_page

    def custom_factory(items, /, total=None, params=None, **kwargs):
        factory_calls.append((list(items), total))
        return create_page(items, total=total, params=params, **kwargs)

    result = run_sync_flow(create_page_flow(items, params, total=3, create_page_factory=custom_factory))

    assert isinstance(result, Page)
    assert len(factory_calls) == 1
    assert factory_calls[0] == ([1, 2, 3], 3)


def test_create_page_flow_with_transformer():
    params = Params(page=1, size=10)
    items = [1, 2, 3]

    def transformer(seq):
        return [x * 10 for x in seq]

    result = run_sync_flow(create_page_flow(items, params, total=3, transformer=transformer))

    assert isinstance(result, Page)
    assert list(result.items) == [10, 20, 30]


def test_generic_flow_raises_when_no_flow_provided():
    params = Params(page=1, size=10)

    with pytest.raises(ValueError, match="At least one flow must be provided"):
        run_sync_flow(generic_flow(params=params))


def test_generic_flow_raises_when_total_flow_missing_and_include_total():
    params = Params(page=1, size=10)
    lo_flow = _make_lo_flow([1, 2, 3])

    with pytest.raises(ValueError, match="total_flow is required when include_total is True"):
        run_sync_flow(generic_flow(limit_offset_flow=lo_flow, params=params))


def test_generic_flow_with_limit_offset():
    params = Params(page=1, size=10)
    items = [1, 2, 3]
    lo_flow = _make_lo_flow(items)
    total_flow = _make_total_flow(3)

    result = run_sync_flow(generic_flow(limit_offset_flow=lo_flow, total_flow=total_flow, params=params))

    assert isinstance(result, Page)
    assert list(result.items) == items
    assert result.total == 3


def test_generic_flow_with_cursor():
    params = CursorParams(cursor=None, size=10)
    items = [1, 2, 3]
    cursor_flow = _make_cursor_flow(items)
    total_flow = _make_total_flow(3)

    result = run_sync_flow(generic_flow(cursor_flow=cursor_flow, total_flow=total_flow, params=params))

    assert isinstance(result, CursorPage)
    assert list(result.items) == items
    assert result.total == 3


def test_generic_flow_with_cursor_and_extra_data():
    params = CursorParams(cursor=None, size=10)
    items = ["x", "y"]
    cursor_flow = _make_cursor_flow(items, extra_data={"next_cursor": "abc"})
    total_flow = _make_total_flow(2)

    result = run_sync_flow(generic_flow(cursor_flow=cursor_flow, total_flow=total_flow, params=params))

    assert isinstance(result, CursorPage)
    assert list(result.items) == items


def test_generic_flow_with_inner_transformer():
    params = Params(page=1, size=10)
    items = [1, 2, 3]
    lo_flow = _make_lo_flow(items)
    total_flow = _make_total_flow(3)

    def inner_transformer(seq):
        return [x * 2 for x in seq]

    result = run_sync_flow(
        generic_flow(
            limit_offset_flow=lo_flow,
            total_flow=total_flow,
            inner_transformer=inner_transformer,
            params=params,
        )
    )

    assert isinstance(result, Page)
    assert list(result.items) == [2, 4, 6]
    assert result.total == 3


def test_generic_flow_with_additional_data():
    params = Params(page=1, size=10)
    items = [1, 2]
    lo_flow = _make_lo_flow(items)
    total_flow = _make_total_flow(2)

    result = run_sync_flow(
        generic_flow(
            limit_offset_flow=lo_flow,
            total_flow=total_flow,
            additional_data={},
            params=params,
        )
    )

    assert isinstance(result, Page)
    assert list(result.items) == items


def test_generic_flow_with_config():
    params = Params(page=1, size=10)
    items = [1, 2, 3]
    lo_flow = _make_lo_flow(items)
    total_flow = _make_total_flow(3)
    config = Config(page_cls=Page)

    result = run_sync_flow(
        generic_flow(
            limit_offset_flow=lo_flow,
            total_flow=total_flow,
            config=config,
            params=params,
        )
    )

    assert isinstance(result, Page)
    assert list(result.items) == items


def test_generic_flow_cursor_raises_when_total_flow_missing():
    params = CursorParams(cursor=None, size=10)
    cursor_flow = _make_cursor_flow([1, 2, 3])

    with pytest.raises(ValueError, match="total_flow is required when include_total is True"):
        run_sync_flow(generic_flow(cursor_flow=cursor_flow, params=params))
