import pytest

from fastapi_pagination import Page, Params
from fastapi_pagination.api import set_page, set_params
from fastapi_pagination.bases import CursorRawParams, RawParams
from fastapi_pagination.config import Config
from fastapi_pagination.cursor import CursorPage, CursorParams
from fastapi_pagination.flow import run_sync_flow
from fastapi_pagination.flows import create_page_flow, generic_flow


# --- Helpers ---

def _params(page=1, size=10):
    return Params(page=page, size=size)


def _simple_total_flow(total):
    def _flow():
        if False:
            yield
        return total

    return _flow


def _simple_limit_offset_flow(items):
    def _flow(raw_params: RawParams):
        if False:
            yield
        return items

    return _flow


def _simple_cursor_flow(items, more_data=None):
    def _flow(raw_params: CursorRawParams):
        if False:
            yield
        return (items, more_data)

    return _flow


# --- create_page_flow ---


def test_create_page_flow_basic():
    params = _params()
    items = [1, 2, 3]

    with set_page(Page), set_params(params):
        page = run_sync_flow(create_page_flow(items, params, total=3))

    assert list(page.items) == items
    assert page.total == 3


def test_create_page_flow_with_config_page_cls():
    params = _params()
    items = ["a", "b"]
    config = Config(page_cls=Page)

    with set_params(params):
        page = run_sync_flow(create_page_flow(items, params, total=2, config=config))

    assert list(page.items) == items
    assert page.total == 2


def test_create_page_flow_with_transformer():
    params = _params()
    items = [1, 2, 3]

    def transformer(xs):
        return [x * 10 for x in xs]

    with set_page(Page), set_params(params):
        page = run_sync_flow(create_page_flow(items, params, total=3, transformer=transformer))

    assert list(page.items) == [10, 20, 30]


def test_create_page_flow_with_custom_factory():
    params = _params()
    items = [5, 6]
    calls = []

    def my_factory(items_arg, /, total=None, params=None, **kwargs):
        result = Page.create(items_arg, params, total=total, **kwargs)
        calls.append(result)
        return result

    with set_page(Page), set_params(params):
        page = run_sync_flow(create_page_flow(items, params, total=2, create_page_factory=my_factory))

    assert len(calls) == 1
    assert list(page.items) == items


def test_create_page_flow_with_additional_data():
    params = _params()
    items = [7, 8]

    with set_page(Page), set_params(params):
        page = run_sync_flow(create_page_flow(items, params, total=2, additional_data={}))

    assert list(page.items) == items


# --- generic_flow ---


def test_generic_flow_no_flows_raises():
    params = _params()

    with set_page(Page), set_params(params):
        with pytest.raises(ValueError, match="At least one flow must be provided"):
            run_sync_flow(generic_flow())


def test_generic_flow_total_flow_required_when_include_total():
    params = _params()

    with set_page(Page), set_params(params):
        with pytest.raises(ValueError, match="total_flow is required"):
            run_sync_flow(generic_flow(
                limit_offset_flow=_simple_limit_offset_flow([]),
                total_flow=None,
            ))


def test_generic_flow_limit_offset_basic():
    params = _params()
    items = ["x", "y", "z"]

    with set_page(Page), set_params(params):
        page = run_sync_flow(generic_flow(
            limit_offset_flow=_simple_limit_offset_flow(items),
            total_flow=_simple_total_flow(3),
        ))

    assert list(page.items) == items
    assert page.total == 3


def test_generic_flow_limit_offset_with_inner_transformer():
    params = _params()
    items = [1, 2, 3]

    def double(xs):
        return [x * 2 for x in xs]

    with set_page(Page), set_params(params):
        page = run_sync_flow(generic_flow(
            limit_offset_flow=_simple_limit_offset_flow(items),
            total_flow=_simple_total_flow(3),
            inner_transformer=double,
        ))

    assert list(page.items) == [2, 4, 6]


def test_generic_flow_cursor_basic():
    cursor_params = CursorParams(size=10)
    items = ["a", "b"]

    with set_page(CursorPage), set_params(cursor_params):
        page = run_sync_flow(generic_flow(
            cursor_flow=_simple_cursor_flow(items, None),
            total_flow=_simple_total_flow(2),
        ))

    assert list(page.items) == items
    assert page.total == 2


def test_generic_flow_cursor_with_more_data():
    cursor_params = CursorParams(size=5)
    items = ["p", "q"]
    more_data = {"next_": "cursor_token"}

    with set_page(CursorPage), set_params(cursor_params):
        page = run_sync_flow(generic_flow(
            cursor_flow=_simple_cursor_flow(items, more_data),
            total_flow=_simple_total_flow(2),
        ))

    assert list(page.items) == items
    assert page.next_page is not None


def test_generic_flow_cursor_no_more_data():
    cursor_params = CursorParams(size=5)
    items = ["r"]

    with set_page(CursorPage), set_params(cursor_params):
        page = run_sync_flow(generic_flow(
            cursor_flow=_simple_cursor_flow(items, None),
            total_flow=_simple_total_flow(1),
        ))

    assert list(page.items) == items


def test_generic_flow_wrong_params_type_raises():
    cursor_params = CursorParams(size=5)

    with set_page(CursorPage), set_params(cursor_params):
        with pytest.raises(ValueError):
            run_sync_flow(generic_flow(
                limit_offset_flow=_simple_limit_offset_flow([]),
                total_flow=_simple_total_flow(0),
            ))


def test_generic_flow_with_additional_data():
    params = _params()
    items = [10, 20]

    with set_page(Page), set_params(params):
        page = run_sync_flow(generic_flow(
            limit_offset_flow=_simple_limit_offset_flow(items),
            total_flow=_simple_total_flow(2),
            additional_data={},
        ))

    assert list(page.items) == items


def test_generic_flow_with_config():
    params = _params()
    items = [100]
    config = Config(page_cls=Page)

    with set_params(params):
        page = run_sync_flow(generic_flow(
            limit_offset_flow=_simple_limit_offset_flow(items),
            total_flow=_simple_total_flow(1),
            config=config,
        ))

    assert list(page.items) == items
