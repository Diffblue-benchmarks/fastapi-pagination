import pytest
import pytest_asyncio
from collections.abc import AsyncIterator
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from httpx import AsyncClient

from fastapi_pagination.api import (
    resolve_params,
    resolve_items_transformer,
    pagination_items,
    create_page,
    response,
    request,
    set_params,
    set_page,
    resolve_page,
    set_items_transformer,
    async_wrapped,
    apply_items_transformer,
    add_pagination,
    pagination_ctx,
    _ctx_var_with_reset,
    _model_validate_has_by_name_param,
    _patch_openapi,
)
from fastapi_pagination.bases import AbstractParams, RawParams
from fastapi_pagination.default import Page, Params
from fastapi_pagination.errors import UninitializedConfigurationError


# ---- resolve_params ----

def test_resolve_params_with_explicit_params():
    params = Params(page=1, size=10)
    result = resolve_params(params)
    assert result is params


def test_resolve_params_from_context():
    params = Params(page=2, size=5)
    with set_params(params):
        result = resolve_params()
    assert result is params


def test_resolve_params_raises_when_not_set():
    with pytest.raises(UninitializedConfigurationError):
        resolve_params()


# ---- resolve_items_transformer ----

def test_resolve_items_transformer_none_returns_default():
    result = resolve_items_transformer(None)
    assert result is None


def test_resolve_items_transformer_explicit():
    transformer = lambda items: items
    result = resolve_items_transformer(transformer)
    assert result is transformer


def test_resolve_items_transformer_from_context():
    transformer = lambda items: [x * 2 for x in items]
    with set_items_transformer(transformer):
        result = resolve_items_transformer()
    assert result is transformer


# ---- pagination_items ----

def test_pagination_items_raises_when_not_set():
    with pytest.raises(UninitializedConfigurationError):
        pagination_items()


# ---- create_page ----

def test_create_page_with_params_and_total():
    params = Params(page=1, size=10)
    with set_page(Page):
        with set_params(params):
            result = create_page([1, 2, 3], total=10, params=params)
    assert result.items == [1, 2, 3]
    assert result.total == 10


def test_create_page_items_accessible_during_creation():
    params = Params(page=1, size=10)
    captured = []

    class CaptureItemsPage(Page[Any]):
        @classmethod
        def create(cls, items, params, **kwargs):
            captured.extend(pagination_items())
            return super().create(items, params, **kwargs)

    with set_page(CaptureItemsPage):
        create_page([10, 20], total=2, params=params)

    assert captured == [10, 20]


# ---- response / request ----

def test_response_raises_when_not_set():
    with pytest.raises(RuntimeError, match="response context var must be set"):
        response()


def test_request_raises_when_not_set():
    with pytest.raises(RuntimeError, match="request context var must be set"):
        request()


# ---- _ctx_var_with_reset ----

def test_ctx_var_with_reset_resets_after_exit():
    from contextvars import ContextVar
    var: ContextVar[int] = ContextVar("test_var")
    with _ctx_var_with_reset(var, 42):
        assert var.get() == 42
    with pytest.raises(LookupError):
        var.get()


def test_ctx_var_with_reset_restores_previous_value():
    from contextvars import ContextVar
    var: ContextVar[int] = ContextVar("test_var2")
    var.set(1)
    with _ctx_var_with_reset(var, 2):
        assert var.get() == 2
    assert var.get() == 1


# ---- set_params ----

def test_set_params():
    params = Params(page=1, size=20)
    with set_params(params):
        assert resolve_params() is params


# ---- set_page ----

def test_set_page():
    with set_page(Page):
        assert resolve_page() is Page


# ---- resolve_page ----

def test_resolve_page_from_context():
    with set_page(Page):
        result = resolve_page()
    assert result is Page


def test_resolve_page_from_params():
    params = Params(page=1, size=10)
    result = resolve_page(params)
    assert result is Page


def test_resolve_page_raises_when_not_set():
    with pytest.raises(UninitializedConfigurationError):
        resolve_page()


# ---- set_items_transformer ----

def test_set_items_transformer():
    transformer = lambda items: items
    with set_items_transformer(transformer):
        result = resolve_items_transformer()
    assert result is transformer


# ---- async_wrapped ----

@pytest.mark.asyncio
async def test_async_wrapped():
    result = await async_wrapped([1, 2, 3])
    assert result == [1, 2, 3]


# ---- apply_items_transformer ----

def test_apply_items_transformer_no_transformer():
    items = [1, 2, 3]
    result = apply_items_transformer(items)
    assert result == items


def test_apply_items_transformer_with_sync_transformer():
    transformer = lambda items: [x * 2 for x in items]
    result = apply_items_transformer([1, 2, 3], transformer)
    assert result == [2, 4, 6]


def test_apply_items_transformer_async_false_with_no_transformer():
    items = [1, 2, 3]
    result = apply_items_transformer(items, async_=False)
    assert result == items


@pytest.mark.asyncio
async def test_apply_items_transformer_async_true_no_transformer():
    items = [1, 2, 3]
    result = await apply_items_transformer(items, async_=True)
    assert result == items


@pytest.mark.asyncio
async def test_apply_items_transformer_async_true_with_sync_transformer():
    transformer = lambda items: [x + 1 for x in items]
    result = await apply_items_transformer([1, 2, 3], transformer, async_=True)
    assert result == [2, 3, 4]


@pytest.mark.asyncio
async def test_apply_items_transformer_async_true_with_async_transformer():
    async def transformer(items):
        return [x * 3 for x in items]

    result = await apply_items_transformer([1, 2, 3], transformer, async_=True)
    assert result == [3, 6, 9]


def test_apply_items_transformer_async_transformer_sync_raises():
    async def transformer(items):
        return items

    with pytest.raises(ValueError, match="async_=False"):
        apply_items_transformer([1, 2, 3], transformer, async_=False)


def test_apply_items_transformer_from_context():
    transformer = lambda items: list(reversed(items))
    with set_items_transformer(transformer):
        result = apply_items_transformer([1, 2, 3])
    assert result == [3, 2, 1]


# ---- _model_validate_has_by_name_param ----

def test_model_validate_has_by_name_param_returns_bool():
    result = _model_validate_has_by_name_param()
    assert isinstance(result, bool)


# ---- pagination_ctx ----

def test_pagination_ctx_returns_callable():
    ctx = pagination_ctx(Page)
    assert callable(ctx)


def test_pagination_ctx_with_page_ctx_dep_flag():
    ctx = pagination_ctx(Page, __page_ctx_dep__=True)
    assert hasattr(ctx, "__page_ctx_dep__")
    assert ctx.__page_ctx_dep__ is True


# ---- add_pagination / integration ----

def test_add_pagination_returns_parent():
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    def get_items():
        return create_page([1, 2, 3], total=3)

    result = add_pagination(app)
    assert result is app


def test_add_pagination_with_client():
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    def get_items():
        params = resolve_params()
        return create_page([1, 2, 3], total=3, params=params)

    add_pagination(app)
    client = TestClient(app)
    resp = client.get("/items")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["items"] == [1, 2, 3]


def test_add_pagination_idempotent():
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    def get_items():
        params = resolve_params()
        return create_page([1, 2, 3], total=3, params=params)

    add_pagination(app)
    add_pagination(app)
    client = TestClient(app)
    resp = client.get("/items")
    assert resp.status_code == 200


def test_add_pagination_router():
    from fastapi.routing import APIRouter
    router = APIRouter()

    @router.get("/items", response_model=Page[int])
    def get_items():
        params = resolve_params()
        return create_page([1, 2, 3], total=3, params=params)

    add_pagination(router)
    app = FastAPI()
    app.include_router(router)
    add_pagination(app)
    client = TestClient(app)
    resp = client.get("/items")
    assert resp.status_code == 200


# ---- _patch_openapi ----

def test_patch_openapi_updates_paths():
    dst = {"paths": {"/a": {"get": {}}}}
    src = {"paths": {"/b": {"post": {}}}}
    _patch_openapi(dst, src)
    assert "/a" in dst["paths"]
    assert "/b" in dst["paths"]


def test_patch_openapi_updates_components_schemas():
    dst = {"components": {"schemas": {"Foo": {"type": "object"}}}}
    src = {"components": {"schemas": {"Bar": {"type": "string"}}}}
    _patch_openapi(dst, src)
    assert "Foo" in dst["components"]["schemas"]
    assert "Bar" in dst["components"]["schemas"]


def test_patch_openapi_missing_paths_key_suppressed():
    dst = {}
    src = {"paths": {"/b": {"post": {}}}}
    _patch_openapi(dst, src)
    assert "paths" not in dst


def test_patch_openapi_missing_components_schemas_suppressed():
    dst = {"paths": {"/a": {}}}
    src = {"components": {"schemas": {"Bar": {}}}}
    _patch_openapi(dst, src)
    assert "components" not in dst


def test_patch_openapi_both_paths_and_schemas():
    dst = {"paths": {"/a": {}}, "components": {"schemas": {"Foo": {}}}}
    src = {"paths": {"/b": {}}, "components": {"schemas": {"Bar": {}}}}
    _patch_openapi(dst, src)
    assert dst["paths"] == {"/a": {}, "/b": {}}
    assert dst["components"]["schemas"] == {"Foo": {}, "Bar": {}}
