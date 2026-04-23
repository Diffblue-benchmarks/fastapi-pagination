from __future__ import annotations

import pytest

from fastapi_pagination.api import set_page
from fastapi_pagination.bases import AbstractParams, RawParams
from fastapi_pagination.config import Config
from fastapi_pagination.cursor import CursorPage, CursorParams
from fastapi_pagination.default import Page, Params
from fastapi_pagination.flow import run_sync_flow
from fastapi_pagination.flows import create_page_flow, generic_flow


# ============================================================
# Tests for create_page_flow
# ============================================================


def test_create_page_flow_basic_returns_page():
    params = Params(page=1, size=10)
    items = [1, 2, 3]
    page = run_sync_flow(create_page_flow(items, params, total=3))
    assert list(page.items) == [1, 2, 3]
    assert page.total == 3


def test_create_page_flow_with_zero_total():
    params = Params(page=1, size=10)
    items = ["a", "b"]
    page = run_sync_flow(create_page_flow(items, params, total=0))
    assert list(page.items) == ["a", "b"]
    assert page.total == 0


def test_create_page_flow_with_config_page_cls():
    params = Params(page=1, size=10)
    items = [10, 20]
    config = Config(page_cls=Page)
    page = run_sync_flow(create_page_flow(items, params, total=2, config=config))
    assert list(page.items) == [10, 20]
    assert page.total == 2


def test_create_page_flow_with_config_none_page_cls():
    params = Params(page=1, size=10)
    items = [1]
    config = Config(page_cls=None)
    page = run_sync_flow(create_page_flow(items, params, total=1, config=config))
    assert list(page.items) == [1]


def test_create_page_flow_with_transformer():
    params = Params(page=1, size=10)
    items = [1, 2, 3]
    transformer = lambda x: [i * 2 for i in x]  # noqa: E731
    page = run_sync_flow(create_page_flow(items, params, total=3, transformer=transformer))
    assert list(page.items) == [2, 4, 6]


def test_create_page_flow_with_custom_factory():
    from fastapi_pagination.api import create_page

    params = Params(page=1, size=10)
    items = [1, 2, 3]
    page = run_sync_flow(create_page_flow(items, params, total=3, create_page_factory=create_page))
    assert list(page.items) == [1, 2, 3]
    assert page.total == 3


def test_create_page_flow_multiple_items():
    params = Params(page=2, size=5)
    items = list(range(5))
    page = run_sync_flow(create_page_flow(items, params, total=10))
    assert list(page.items) == [0, 1, 2, 3, 4]
    assert page.total == 10


# ============================================================
# Tests for generic_flow
# ============================================================


def test_generic_flow_no_flows_raises():
    with pytest.raises(ValueError, match="At least one flow must be provided"):
        run_sync_flow(generic_flow())


def test_generic_flow_total_flow_required_when_include_total():
    params = Params(page=1, size=10)

    def lo_flow(raw_params):
        return [1, 2, 3]
        yield  # make it a generator

    with pytest.raises(ValueError, match="total_flow is required when include_total is True"):
        run_sync_flow(generic_flow(limit_offset_flow=lo_flow, params=params))


def test_generic_flow_limit_offset_with_total():
    params = Params(page=1, size=10)

    def lo_flow(raw_params):
        return [1, 2, 3]
        yield  # make it a generator

    def tf():
        return 3
        yield  # make it a generator

    page = run_sync_flow(generic_flow(limit_offset_flow=lo_flow, total_flow=tf, params=params))
    assert list(page.items) == [1, 2, 3]
    assert page.total == 3


def test_generic_flow_limit_offset_without_include_total():
    class NoTotalParams(Params):
        def to_raw_params(self) -> RawParams:
            return RawParams(limit=self.size, offset=self.size * (self.page - 1), include_total=False)

    params = NoTotalParams(page=1, size=10)
    factory_totals = []

    def lo_flow(raw_params):
        return [1, 2]
        yield  # make it a generator

    from fastapi_pagination.api import create_page

    def capturing_factory(items, /, total=None, params=None, **kwargs):
        factory_totals.append(total)
        return create_page(items, total=0, params=params)

    page = run_sync_flow(generic_flow(
        limit_offset_flow=lo_flow,
        params=params,
        create_page_factory=capturing_factory,
    ))
    assert list(page.items) == [1, 2]
    assert factory_totals == [None]  # total_flow was not called since include_total=False


def test_generic_flow_cursor_with_total():
    params = CursorParams(cursor=None, size=10)

    def cursor_flow_fn(raw_params):
        return ([1, 2, 3], {})
        yield  # make it a generator

    def tf():
        return 3
        yield  # make it a generator

    page = run_sync_flow(generic_flow(cursor_flow=cursor_flow_fn, total_flow=tf, params=params))
    assert list(page.items) == [1, 2, 3]


def test_generic_flow_cursor_more_data_none():
    params = CursorParams(cursor=None, size=10)

    def cursor_flow_fn(raw_params):
        return ([5, 6], None)
        yield  # make it a generator

    def tf():
        return 2
        yield  # make it a generator

    page = run_sync_flow(generic_flow(cursor_flow=cursor_flow_fn, total_flow=tf, params=params))
    assert list(page.items) == [5, 6]


def test_generic_flow_with_inner_transformer():
    params = Params(page=1, size=10)

    def lo_flow(raw_params):
        return [1, 2, 3]
        yield  # make it a generator

    def tf():
        return 3
        yield  # make it a generator

    inner_transformer = lambda x: [i * 10 for i in x]  # noqa: E731

    page = run_sync_flow(
        generic_flow(
            limit_offset_flow=lo_flow,
            total_flow=tf,
            params=params,
            inner_transformer=inner_transformer,
        )
    )
    assert list(page.items) == [10, 20, 30]


def test_generic_flow_both_flows_limit_offset_params():
    params = Params(page=1, size=10)

    def lo_flow(raw_params):
        return [1, 2, 3]
        yield  # make it a generator

    def cursor_flow_fn(raw_params):
        return ([4, 5, 6], {})
        yield  # make it a generator

    def tf():
        return 3
        yield  # make it a generator

    page = run_sync_flow(
        generic_flow(
            limit_offset_flow=lo_flow,
            cursor_flow=cursor_flow_fn,
            total_flow=tf,
            params=params,
        )
    )
    assert list(page.items) == [1, 2, 3]


def test_generic_flow_both_flows_cursor_params():
    params = CursorParams(cursor=None, size=10)

    def lo_flow(raw_params):
        return [1, 2, 3]
        yield  # make it a generator

    def cursor_flow_fn(raw_params):
        return ([4, 5, 6], {})
        yield  # make it a generator

    def tf():
        return 3
        yield  # make it a generator

    page = run_sync_flow(
        generic_flow(
            limit_offset_flow=lo_flow,
            cursor_flow=cursor_flow_fn,
            total_flow=tf,
            params=params,
        )
    )
    assert list(page.items) == [4, 5, 6]


def test_generic_flow_with_config():
    params = Params(page=1, size=10)
    config = Config(page_cls=Page)

    def lo_flow(raw_params):
        return [7, 8, 9]
        yield  # make it a generator

    def tf():
        return 3
        yield  # make it a generator

    page = run_sync_flow(
        generic_flow(
            limit_offset_flow=lo_flow,
            total_flow=tf,
            params=params,
            config=config,
        )
    )
    assert list(page.items) == [7, 8, 9]


def test_generic_flow_with_additional_data_param():
    params = Params(page=1, size=10)

    def lo_flow(raw_params):
        return [1, 2]
        yield  # make it a generator

    def tf():
        return 2
        yield  # make it a generator

    page = run_sync_flow(
        generic_flow(
            limit_offset_flow=lo_flow,
            total_flow=tf,
            params=params,
            additional_data={},
        )
    )
    assert list(page.items) == [1, 2]


def test_generic_flow_total_zero_from_total_flow():
    params = Params(page=1, size=10)

    def lo_flow(raw_params):
        return []
        yield  # make it a generator

    def tf():
        return 0
        yield  # make it a generator

    page = run_sync_flow(generic_flow(limit_offset_flow=lo_flow, total_flow=tf, params=params))
    assert list(page.items) == []
    assert page.total == 0
