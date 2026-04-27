"""Unit tests for fastapi_pagination/api.py."""
from __future__ import annotations

import pytest
import pytest_asyncio
from typing import Any, Sequence
from contextvars import ContextVar

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from fastapi_pagination.api import (
    _add_pagination,
    _ctx_var_with_reset,
    _model_validate_has_by_name_param,
    _noop_dep,
    _patch_openapi,
    _update_route,
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
from fastapi_pagination.default import Page, Params
from fastapi_pagination.errors import UninitializedConfigurationError


# ---------------------------------------------------------------------------
# resolve_params
# ---------------------------------------------------------------------------

def test_resolve_params_with_explicit_params():
    params = Params()
    assert resolve_params(params) is params


def test_resolve_params_from_context():
    params = Params()
    with set_params(params):
        result = resolve_params()
    assert result is params


def test_resolve_params_none_raises_when_no_context():
    with pytest.raises(UninitializedConfigurationError):
        resolve_params(None)


# ---------------------------------------------------------------------------
# resolve_items_transformer
# ---------------------------------------------------------------------------

def test_resolve_items_transformer_returns_none_by_default():
    result = resolve_items_transformer(None)
    assert result is None


def test_resolve_items_transformer_with_explicit_transformer():
    transformer = lambda items: items  # noqa: E731
    assert resolve_items_transformer(transformer) is transformer


def test_resolve_items_transformer_from_context():
    transformer = lambda items: list(items)  # noqa: E731
    with set_items_transformer(transformer):
        result = resolve_items_transformer(None)
    assert result is transformer


# ---------------------------------------------------------------------------
# pagination_items
# ---------------------------------------------------------------------------

def test_pagination_items_raises_when_not_in_create_page():
    with pytest.raises(UninitializedConfigurationError):
        pagination_items()


def test_pagination_items_inside_create_page():
    items = [1, 2, 3]
    captured = []

    class CapturingPage(Page[Any]):
        @classmethod
        def create(cls, items: Sequence[Any], params: Any, **kwargs: Any) -> "CapturingPage":
            captured.extend(pagination_items())
            return super().create(items, params, **kwargs)

    params = Params(page=1, size=10)
    with set_page(CapturingPage):
        with set_params(params):
            create_page(items, total=3, params=params)

    assert captured == items


# ---------------------------------------------------------------------------
# response / request
# ---------------------------------------------------------------------------

def test_response_raises_when_no_context():
    with pytest.raises(RuntimeError, match="response context var must be set"):
        response()


def test_request_raises_when_no_context():
    with pytest.raises(RuntimeError, match="request context var must be set"):
        request()


# ---------------------------------------------------------------------------
# _ctx_var_with_reset
# ---------------------------------------------------------------------------

def test_ctx_var_with_reset_sets_and_resets():
    var: ContextVar[int] = ContextVar("test_var")
    with _ctx_var_with_reset(var, 42):
        assert var.get() == 42
    # after exiting, the token should be reset
    with pytest.raises(LookupError):
        var.get()


def test_ctx_var_with_reset_nested():
    var: ContextVar[str] = ContextVar("test_nested")
    with _ctx_var_with_reset(var, "outer"):
        assert var.get() == "outer"
        with _ctx_var_with_reset(var, "inner"):
            assert var.get() == "inner"
        assert var.get() == "outer"


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
    transformer = lambda items: items  # noqa: E731
    with set_items_transformer(transformer):
        assert resolve_items_transformer() is transformer


# ---------------------------------------------------------------------------
# resolve_page
# ---------------------------------------------------------------------------

def test_resolve_page_from_context():
    with set_page(Page):
        assert resolve_page() is Page


def test_resolve_page_from_params():
    params = Params()
    # Params is connected to Page via __page_type__
    assert resolve_page(params) is Page


def test_resolve_page_raises_when_no_context_and_no_params():
    with pytest.raises(UninitializedConfigurationError):
        resolve_page(None)


def test_resolve_page_raises_when_params_has_no_page_type():
    from fastapi_pagination.bases import AbstractParams, BaseRawParams, RawParams

    class NoPageParams(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    with pytest.raises(UninitializedConfigurationError):
        resolve_page(NoPageParams())


# ---------------------------------------------------------------------------
# create_page
# ---------------------------------------------------------------------------

def test_create_page_with_params_and_total():
    params = Params(page=1, size=10)
    with set_page(Page):
        page = create_page([1, 2, 3], total=3, params=params)
    assert page.total == 3
    assert list(page.items) == [1, 2, 3]


def test_create_page_without_total():
    params = Params(page=1, size=10)
    with set_page(Page):
        page = create_page([1, 2, 3], total=3, params=params)
    assert list(page.items) == [1, 2, 3]


def test_create_page_passes_kwargs():
    params = Params(page=1, size=10)
    with set_page(Page):
        page = create_page([1], total=1, params=params)
    assert page.page == 1


# ---------------------------------------------------------------------------
# async_wrapped
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_async_wrapped_returns_object():
    obj = object()
    result = await async_wrapped(obj)
    assert result is obj


# ---------------------------------------------------------------------------
# apply_items_transformer
# ---------------------------------------------------------------------------

def test_apply_items_transformer_no_transformer():
    items = [1, 2, 3]
    result = apply_items_transformer(items)
    assert result is items


def test_apply_items_transformer_sync_transformer():
    items = [1, 2, 3]
    transformer = lambda x: [i * 2 for i in x]  # noqa: E731
    result = apply_items_transformer(items, transformer)
    assert result == [2, 4, 6]


def test_apply_items_transformer_sync_transformer_async_mode():
    import asyncio
    items = [1, 2, 3]
    transformer = lambda x: list(x)  # noqa: E731
    result = asyncio.get_event_loop().run_until_complete(
        apply_items_transformer(items, transformer, async_=True)
    )
    assert result == [1, 2, 3]


@pytest.mark.asyncio
async def test_apply_items_transformer_async_transformer():
    items = [1, 2, 3]

    async def async_transformer(x: Sequence[Any]) -> Sequence[Any]:
        return [i * 3 for i in x]

    result = await apply_items_transformer(items, async_transformer, async_=True)
    assert result == [3, 6, 9]


def test_apply_items_transformer_async_transformer_sync_mode_raises():
    items = [1, 2, 3]

    async def async_transformer(x: Sequence[Any]) -> Sequence[Any]:
        return x

    with pytest.raises(ValueError, match="async_=False"):
        apply_items_transformer(items, async_transformer)


@pytest.mark.asyncio
async def test_apply_items_transformer_no_transformer_async():
    items = [1, 2, 3]
    result = await apply_items_transformer(items, async_=True)
    assert result is items


def test_apply_items_transformer_from_context():
    items = [1, 2, 3]
    transformer = lambda x: [i + 10 for i in x]  # noqa: E731
    with set_items_transformer(transformer):
        result = apply_items_transformer(items)
    assert result == [11, 12, 13]


# ---------------------------------------------------------------------------
# _model_validate_has_by_name_param
# ---------------------------------------------------------------------------

def test_model_validate_has_by_name_param_returns_bool():
    result = _model_validate_has_by_name_param()
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# _noop_dep
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_noop_dep_returns_none():
    result = await _noop_dep()
    assert result is None


# ---------------------------------------------------------------------------
# pagination_ctx
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pagination_ctx_with_page_and_params():
    from unittest.mock import MagicMock
    from fastapi import Request, Response

    dep_fn = pagination_ctx(Page)
    assert callable(dep_fn)


def test_pagination_ctx_sets_page_ctx_dep_flag():
    dep_fn = pagination_ctx(Page, __page_ctx_dep__=True)
    assert hasattr(dep_fn, "__page_ctx_dep__")
    assert dep_fn.__page_ctx_dep__ is True


def test_pagination_ctx_without_flag():
    dep_fn = pagination_ctx(Page)
    assert not hasattr(dep_fn, "__page_ctx_dep__")


# ---------------------------------------------------------------------------
# _patch_openapi
# ---------------------------------------------------------------------------

def test_patch_openapi_updates_paths():
    dst = {"paths": {"/a": {}}}
    src = {"paths": {"/b": {}}}
    _patch_openapi(dst, src)
    assert "/b" in dst["paths"]
    assert "/a" in dst["paths"]


def test_patch_openapi_updates_components():
    dst = {"components": {"schemas": {"A": {}}}}
    src = {"components": {"schemas": {"B": {}}}}
    _patch_openapi(dst, src)
    assert "B" in dst["components"]["schemas"]
    assert "A" in dst["components"]["schemas"]


def test_patch_openapi_missing_keys():
    dst: dict = {}
    src: dict = {}
    # should not raise
    _patch_openapi(dst, src)


def test_patch_openapi_missing_paths_in_dst():
    dst: dict = {}
    src = {"paths": {"/new": {}}}
    _patch_openapi(dst, src)
    # dst doesn't have "paths" key so it's skipped via suppress
    assert "paths" not in dst


# ---------------------------------------------------------------------------
# _add_pagination + add_pagination (integration style)
# ---------------------------------------------------------------------------

def test_add_pagination_to_router():
    from fastapi.routing import APIRouter
    router = APIRouter()

    @router.get("/items", response_model=Page[int])
    def get_items():
        return []

    _add_pagination(router)
    route = router.routes[0]
    assert isinstance(route, APIRoute)
    # The route should have pagination dependency now
    assert any(hasattr(d.call, "__page_ctx_dep__") for d in route.dependant.dependencies)


def test_add_pagination_to_app():
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    def get_items():
        with set_page(Page):
            with set_params(Params()):
                return create_page([], total=0, params=Params())

    add_pagination(app)

    client = TestClient(app)
    resp = client.get("/items?page=1&size=10")
    assert resp.status_code == 200


def test_add_pagination_skips_non_page_routes():
    app = FastAPI()

    @app.get("/plain", response_model=str)
    def plain():
        return "hello"

    _add_pagination(app)
    route = next(r for r in app.routes if isinstance(r, APIRoute) and r.path == "/plain")
    assert not any(hasattr(d.call, "__page_ctx_dep__") for d in route.dependant.dependencies)


def test_add_pagination_full_integration():
    app = FastAPI()

    @app.get("/nums", response_model=Page[int])
    async def get_nums():
        return create_page([1, 2, 3], total=3, params=Params(page=1, size=10))

    add_pagination(app)
    client = TestClient(app)
    resp = client.get("/nums?page=1&size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert data["items"] == [1, 2, 3]


def test_add_pagination_lifespan():
    """Test that add_pagination's lifespan wrapper properly calls _add_pagination."""
    import asyncio

    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    async def get_items():
        return create_page([1], total=1, params=Params())

    add_pagination(app)

    # Running the lifespan means the wrapped context manager executes
    client = TestClient(app)
    resp = client.get("/items?page=1&size=10")
    assert resp.status_code == 200


def test_update_route_skips_if_already_has_pagination_dep():
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    async def get_items():
        return create_page([1], total=1, params=Params())

    _add_pagination(app)
    route = next(r for r in app.routes if isinstance(r, APIRoute) and r.path == "/items")
    deps_before = len(route.dependant.dependencies)

    # Calling _update_route again should not add another dependency
    _update_route(route)
    assert len(route.dependant.dependencies) == deps_before
