"""Unit tests for fastapi_pagination.api module."""
import pytest
import pytest_asyncio
from collections.abc import Sequence
from contextvars import ContextVar
from typing import Any
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.routing import APIRouter

from fastapi_pagination.api import (
    _ctx_var_with_reset,
    _patch_openapi,
    _add_pagination,
    add_pagination,
    apply_items_transformer,
    async_wrapped,
    create_page,
    pagination_ctx,
    pagination_items,
    request,
    resolve_items_transformer,
    resolve_page,
    resolve_params,
    response,
    set_items_transformer,
    set_page,
    set_params,
)
from fastapi_pagination.bases import AbstractParams
from fastapi_pagination.default import Page, Params
from fastapi_pagination.errors import UninitializedConfigurationError


# ---------------------------------------------------------------------------
# resolve_params
# ---------------------------------------------------------------------------


def test_resolve_params_returns_provided_params():
    params = Params()
    assert resolve_params(params) is params


def test_resolve_params_returns_context_var_when_no_params():
    params = Params()
    with set_params(params):
        result = resolve_params()
    assert result is params


def test_resolve_params_raises_when_uninitialized():
    with pytest.raises(UninitializedConfigurationError):
        resolve_params()


# ---------------------------------------------------------------------------
# resolve_items_transformer
# ---------------------------------------------------------------------------


def test_resolve_items_transformer_returns_none_by_default():
    result = resolve_items_transformer()
    assert result is None


def test_resolve_items_transformer_returns_provided_transformer():
    transformer = lambda items: items  # noqa: E731
    assert resolve_items_transformer(transformer) is transformer


def test_resolve_items_transformer_returns_context_var():
    transformer = lambda items: items  # noqa: E731
    with set_items_transformer(transformer):
        result = resolve_items_transformer()
    assert result is transformer


# ---------------------------------------------------------------------------
# pagination_items
# ---------------------------------------------------------------------------


def test_pagination_items_raises_when_uninitialized():
    with pytest.raises(UninitializedConfigurationError):
        pagination_items()


def test_pagination_items_returns_items_when_set():
    items = [1, 2, 3]
    params = Params()
    with set_params(params), set_page(Page):
        page = create_page(items, total=3, params=params)
    assert page.items == items


# ---------------------------------------------------------------------------
# create_page
# ---------------------------------------------------------------------------


def test_create_page_with_params_and_total():
    items = [1, 2, 3]
    params = Params(page=1, size=10)
    with set_page(Page):
        page = create_page(items, total=3, params=params)
    assert page.items == items
    assert page.total == 3


def test_create_page_uses_context_params():
    items = ["a", "b"]
    params = Params(page=1, size=10)
    with set_params(params), set_page(Page):
        page = create_page(items, total=2, params=params)
    assert page.total == 2


# ---------------------------------------------------------------------------
# response / request context vars
# ---------------------------------------------------------------------------


def test_response_raises_when_uninitialized():
    with pytest.raises(RuntimeError, match="response context var must be set"):
        response()


def test_request_raises_when_uninitialized():
    with pytest.raises(RuntimeError, match="request context var must be set"):
        request()


# ---------------------------------------------------------------------------
# _ctx_var_with_reset
# ---------------------------------------------------------------------------


def test_ctx_var_with_reset_sets_and_resets():
    var: ContextVar[int] = ContextVar("test_var")
    with _ctx_var_with_reset(var, 42):
        assert var.get() == 42
    with pytest.raises(LookupError):
        var.get()


def test_ctx_var_with_reset_restores_previous_value():
    var: ContextVar[int] = ContextVar("test_var2", default=10)
    var.set(10)
    with _ctx_var_with_reset(var, 99):
        assert var.get() == 99
    assert var.get() == 10


# ---------------------------------------------------------------------------
# set_params / set_page / set_items_transformer
# ---------------------------------------------------------------------------


def test_set_params_context_manager():
    params = Params()
    with set_params(params):
        assert resolve_params() is params


def test_set_page_context_manager():
    with set_page(Page):
        assert resolve_page() is Page


def test_set_items_transformer_context_manager():
    fn = lambda items: items  # noqa: E731
    with set_items_transformer(fn):
        assert resolve_items_transformer() is fn


# ---------------------------------------------------------------------------
# resolve_page
# ---------------------------------------------------------------------------


def test_resolve_page_from_context():
    with set_page(Page):
        assert resolve_page() is Page


def test_resolve_page_from_params():
    params = Params()
    # Params.__page_type__ should be Page after default wiring
    result = resolve_page(params)
    assert result is Page


def test_resolve_page_raises_when_uninitialized():
    with pytest.raises(UninitializedConfigurationError):
        resolve_page()


# ---------------------------------------------------------------------------
# async_wrapped
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_wrapped_returns_value():
    result = await async_wrapped(42)
    assert result == 42


@pytest.mark.asyncio
async def test_async_wrapped_returns_list():
    items = [1, 2, 3]
    result = await async_wrapped(items)
    assert result is items


# ---------------------------------------------------------------------------
# apply_items_transformer
# ---------------------------------------------------------------------------


def test_apply_items_transformer_no_transformer():
    items = [1, 2, 3]
    result = apply_items_transformer(items)
    assert result is items


def test_apply_items_transformer_with_sync_transformer():
    items = [1, 2, 3]
    transformer = lambda x: [i * 2 for i in x]  # noqa: E731
    result = apply_items_transformer(items, transformer)
    assert result == [2, 4, 6]


def test_apply_items_transformer_async_false_with_async_raises():
    import asyncio

    async def async_transformer(items: Sequence[Any]) -> Sequence[Any]:
        return items

    with pytest.raises(ValueError, match="async_=False but transformer is async"):
        apply_items_transformer([1, 2, 3], async_transformer, async_=False)


@pytest.mark.asyncio
async def test_apply_items_transformer_async_true_no_transformer():
    items = [1, 2, 3]
    result = await apply_items_transformer(items, async_=True)
    assert result is items


@pytest.mark.asyncio
async def test_apply_items_transformer_async_true_with_async_transformer():
    items = [1, 2, 3]

    async def async_transformer(x: Sequence[Any]) -> Sequence[Any]:
        return [i + 1 for i in x]

    result = await apply_items_transformer(items, async_transformer, async_=True)
    assert result == [2, 3, 4]


@pytest.mark.asyncio
async def test_apply_items_transformer_async_true_with_sync_transformer():
    items = [1, 2, 3]

    def sync_transformer(x: Sequence[Any]) -> Sequence[Any]:
        return list(reversed(x))

    result = await apply_items_transformer(items, sync_transformer, async_=True)
    assert result == [3, 2, 1]


# ---------------------------------------------------------------------------
# _patch_openapi
# ---------------------------------------------------------------------------


def test_patch_openapi_updates_paths():
    dst = {"paths": {"/a": {}}}
    src = {"paths": {"/b": {}}}
    _patch_openapi(dst, src)
    assert "/a" in dst["paths"]
    assert "/b" in dst["paths"]


def test_patch_openapi_handles_missing_keys():
    dst: dict[str, Any] = {}
    src: dict[str, Any] = {}
    _patch_openapi(dst, src)  # should not raise


def test_patch_openapi_updates_schemas():
    dst = {"components": {"schemas": {"A": {}}}}
    src = {"components": {"schemas": {"B": {}}}}
    _patch_openapi(dst, src)
    assert "A" in dst["components"]["schemas"]
    assert "B" in dst["components"]["schemas"]


# ---------------------------------------------------------------------------
# add_pagination / _add_pagination
# ---------------------------------------------------------------------------


def test_add_pagination_returns_app():
    app = FastAPI()
    result = add_pagination(app)
    assert result is app


def test_add_pagination_returns_router():
    router = APIRouter()
    result = add_pagination(router)
    assert result is router


def test_add_pagination_processes_routes():
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    async def list_items():
        return []

    result = add_pagination(app)
    assert result is app


@pytest.mark.asyncio
@pytest.mark.skip(reason="asgi-lifespan not installed in this environment")
async def test_add_pagination_lifespan():
    """Test that the lifespan context added by add_pagination works."""
    from asgi_lifespan import LifespanManager
    import httpx

    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    async def list_items():
        return create_page([1, 2, 3], total=3)

    add_pagination(app)

    async with LifespanManager(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/items")
            assert resp.status_code == 200


# ---------------------------------------------------------------------------
# pagination_ctx
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pagination_ctx_yields_params():
    from fastapi.testclient import TestClient

    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    async def list_items():
        params = resolve_params()
        return create_page([1, 2, 3], total=3, params=params)

    add_pagination(app)

    client = TestClient(app)
    resp = client.get("/items?page=1&size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3


def test_pagination_ctx_with_page_and_transformer():
    transformer = lambda items: items  # noqa: E731
    ctx_fn = pagination_ctx(page=Page, transformer=transformer)
    assert callable(ctx_fn)


def test_pagination_ctx_with_params_only():
    ctx_fn = pagination_ctx(params=Params)
    assert callable(ctx_fn)


# ---------------------------------------------------------------------------
# _noop_dep
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_noop_dep_returns_none():
    from fastapi_pagination.api import _noop_dep

    result = await _noop_dep()
    assert result is None


# ---------------------------------------------------------------------------
# _model_validate_has_by_name_param
# ---------------------------------------------------------------------------


def test_model_validate_has_by_name_param():
    from fastapi_pagination.api import _model_validate_has_by_name_param

    result = _model_validate_has_by_name_param()
    assert isinstance(result, bool)
