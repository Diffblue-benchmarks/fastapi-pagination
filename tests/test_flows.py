from __future__ import annotations

import pytest

from fastapi_pagination.api import set_page
from fastapi_pagination.bases import AbstractParams, CursorRawParams, RawParams
from fastapi_pagination.config import Config
from fastapi_pagination.cursor import CursorPage, CursorParams
from fastapi_pagination.default import Page, Params
from fastapi_pagination.flow import run_sync_flow
from fastapi_pagination.flows import create_page_flow, generic_flow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class NoTotalParams(AbstractParams):
    """Params that return include_total=False so tests don't need total_flow."""

    def to_raw_params(self) -> RawParams:
        return RawParams(limit=10, offset=0, include_total=False)


class NoCursorTotalParams(AbstractParams):
    """Cursor params that return include_total=False."""

    def to_raw_params(self) -> CursorRawParams:
        return CursorRawParams(cursor=None, size=10, include_total=False)


def _lo_flow(items):
    """Build a simple limit-offset flow returning fixed items."""

    def _flow(raw_params):
        return items
        yield  # make it a generator

    return _flow


def _total_flow(total):
    """Build a simple total flow returning fixed total."""

    def _flow():
        return total
        yield  # make it a generator

    return _flow


def _cursor_flow(items, extra=None):
    """Build a simple cursor flow returning (items, extra)."""

    def _flow(raw_params):
        return (items, extra)
        yield  # make it a generator

    return _flow


# ---------------------------------------------------------------------------
# create_page_flow tests
# ---------------------------------------------------------------------------


def test_create_page_flow_basic():
    params = Params(page=1, size=10)
    items = [1, 2, 3]
    page = run_sync_flow(create_page_flow(items, params, total=3))
    assert list(page.items) == items
    assert page.total == 3


def test_create_page_flow_with_transformer():
    params = Params(page=1, size=10)
    items = [1, 2, 3]
    page = run_sync_flow(
        create_page_flow(
            items,
            params,
            total=3,
            transformer=lambda x: [i * 2 for i in x],
        )
    )
    assert list(page.items) == [2, 4, 6]


def test_create_page_flow_with_config_page_cls():
    params = Params(page=1, size=10)
    items = [10, 20]
    config = Config(page_cls=Page)
    page = run_sync_flow(create_page_flow(items, params, total=2, config=config))
    assert list(page.items) == items
    assert page.total == 2


def test_create_page_flow_with_config_no_page_cls():
    params = Params(page=1, size=10)
    items = [10, 20]
    config = Config(page_cls=None)
    page = run_sync_flow(create_page_flow(items, params, total=2, config=config))
    assert list(page.items) == items


def test_create_page_flow_with_custom_factory():
    params = Params(page=1, size=10)
    items = [1, 2, 3]

    def custom_factory(it, /, total=None, params=None, **kwargs):
        return {"items": list(it), "total": total}

    result = run_sync_flow(
        create_page_flow(items, params, total=3, create_page_factory=custom_factory)
    )
    assert result == {"items": items, "total": 3}


def test_create_page_flow_with_additional_data():
    params = Params(page=1, size=10)
    items = [1]

    def custom_factory(it, /, total=None, params=None, **kwargs):
        return {"items": list(it), "extra": kwargs.get("extra")}

    result = run_sync_flow(
        create_page_flow(
            items,
            params,
            create_page_factory=custom_factory,
            additional_data={"extra": "hello"},
        )
    )
    assert result["extra"] == "hello"


# ---------------------------------------------------------------------------
# generic_flow tests
# ---------------------------------------------------------------------------


def test_generic_flow_no_flows_raises():
    params = Params(page=1, size=10)
    with pytest.raises(ValueError, match="At least one flow must be provided"):
        run_sync_flow(generic_flow(params=params))


def test_generic_flow_include_total_requires_total_flow():
    params = Params(page=1, size=10)

    def lo(rp):
        return [1]
        yield

    with pytest.raises(ValueError, match="total_flow is required when include_total is True"):
        run_sync_flow(generic_flow(limit_offset_flow=lo, params=params))


def test_generic_flow_limit_offset_basic():
    items = [1, 2, 3]
    page = run_sync_flow(
        generic_flow(
            limit_offset_flow=_lo_flow(items),
            total_flow=_total_flow(3),
            params=Params(page=1, size=10),
        )
    )
    assert list(page.items) == items
    assert page.total == 3


def test_generic_flow_limit_offset_no_total():
    items = ["x", "y"]

    def custom_factory(it, /, total=None, params=None, **kwargs):
        return {"items": list(it), "total": total}

    result = run_sync_flow(
        generic_flow(
            limit_offset_flow=_lo_flow(items),
            params=NoTotalParams(),
            create_page_factory=custom_factory,
        )
    )
    assert result["items"] == items
    assert result["total"] is None


def test_generic_flow_limit_offset_with_inner_transformer():
    items = [1, 2, 3]
    page = run_sync_flow(
        generic_flow(
            limit_offset_flow=_lo_flow(items),
            total_flow=_total_flow(3),
            params=Params(page=1, size=10),
            inner_transformer=lambda x: [i * 10 for i in x],
        )
    )
    assert list(page.items) == [10, 20, 30]


@pytest.mark.skip(reason="limit_offset_flow=None with limit-offset params is unreachable: verify_params raises first")
def test_generic_flow_limit_offset_missing_raises():
    """limit_offset_flow is None but params is limit-offset — defensive branch, unreachable in practice."""
    pass


def test_generic_flow_cursor_basic():
    items = [10, 20]
    with set_page(CursorPage):
        page = run_sync_flow(
            generic_flow(
                cursor_flow=_cursor_flow(items),
                total_flow=_total_flow(2),
                params=CursorParams(),
            )
        )
    assert list(page.items) == items


def test_generic_flow_cursor_no_total():
    items = [10, 20]

    def custom_factory(it, /, total=None, params=None, **kwargs):
        return {"items": list(it), "total": total}

    result = run_sync_flow(
        generic_flow(
            cursor_flow=_cursor_flow(items, extra={"next": "tok"}),
            params=NoCursorTotalParams(),
            create_page_factory=custom_factory,
        )
    )
    assert result["items"] == items


@pytest.mark.skip(reason="cursor_flow=None with cursor params is unreachable: verify_params raises first")
def test_generic_flow_cursor_missing_raises():
    """cursor_flow is None but params is cursor — defensive branch, unreachable in practice."""
    pass


def test_generic_flow_with_config():
    items = [5, 6]
    config = Config(page_cls=Page)
    page = run_sync_flow(
        generic_flow(
            limit_offset_flow=_lo_flow(items),
            total_flow=_total_flow(2),
            params=Params(page=1, size=10),
            config=config,
        )
    )
    assert list(page.items) == items


def test_generic_flow_with_outer_transformer():
    items = [1, 2]
    page = run_sync_flow(
        generic_flow(
            limit_offset_flow=_lo_flow(items),
            total_flow=_total_flow(2),
            params=Params(page=1, size=10),
            transformer=lambda x: [str(i) for i in x],
        )
    )
    assert list(page.items) == ["1", "2"]


def test_generic_flow_with_additional_data():
    items = [1]

    def custom_factory(it, /, total=None, params=None, **kwargs):
        return {"items": list(it), "extra": kwargs.get("extra")}

    page = run_sync_flow(
        generic_flow(
            limit_offset_flow=_lo_flow(items),
            total_flow=_total_flow(1),
            params=Params(page=1, size=10),
            additional_data={"extra": "val"},
            create_page_factory=custom_factory,
        )
    )
    assert page["extra"] == "val"
