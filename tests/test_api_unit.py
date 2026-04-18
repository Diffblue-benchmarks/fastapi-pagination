"""Unit tests for fastapi_pagination/api.py"""
from __future__ import annotations

from contextvars import ContextVar
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from pydantic import BaseModel

import fastapi_pagination.api as _api_module
from fastapi_pagination.api import (
    _create_params_dependency,
    _ctx_var_with_reset,
    _model_validate_has_by_name_param,
    _noop_dep,
    _patch_openapi,
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
from fastapi_pagination.bases import AbstractParams, RawParams
from fastapi_pagination.default import Page, Params
from fastapi_pagination.errors import UninitializedConfigurationError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_context_vars():
    """Reset all pagination context vars before and after each test."""
    ctx_vars = [
        _api_module._params_val,
        _api_module._page_val,
        _api_module._rsp_val,
        _api_module._req_val,
        _api_module._items_val,
        _api_module._items_transformer_val,
    ]
    # Set all vars to sentinel values and capture reset tokens
    reset_tokens = [(var, var.set(None)) for var in ctx_vars]  # type: ignore[arg-type]
    # Immediately reset them back to their pre-test state (unset)
    for var, token in reset_tokens:
        var.reset(token)

    yield

    # After test: reset all vars to unset state
    for var in ctx_vars:
        try:
            var.get()
            # Var is set; reset it
            token = var.set(None)  # type: ignore[arg-type]
            var.reset(token)
        except LookupError:
            pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_params() -> Params:
    return Params(page=1, size=10)


# ---------------------------------------------------------------------------
# resolve_params
# ---------------------------------------------------------------------------

def test_resolve_params_returns_provided_params():
    params = _make_params()
    assert resolve_params(params) is params


def test_resolve_params_raises_when_not_set():
    with pytest.raises(UninitializedConfigurationError):
        resolve_params(None)


def test_resolve_params_from_context():
    params = _make_params()
    with set_params(params):
        result = resolve_params()
    assert result is params


# ---------------------------------------------------------------------------
# resolve_items_transformer
# ---------------------------------------------------------------------------

def test_resolve_items_transformer_returns_none_by_default():
    assert resolve_items_transformer(None) is None


def test_resolve_items_transformer_returns_provided():
    transformer = lambda items: items
    assert resolve_items_transformer(transformer) is transformer


def test_resolve_items_transformer_from_context():
    transformer = lambda items: list(reversed(items))
    with set_items_transformer(transformer):
        result = resolve_items_transformer(None)
    assert result is transformer


# ---------------------------------------------------------------------------
# pagination_items
# ---------------------------------------------------------------------------

def test_pagination_items_raises_when_not_in_create_page():
    with pytest.raises(UninitializedConfigurationError):
        pagination_items()


# ---------------------------------------------------------------------------
# create_page
# ---------------------------------------------------------------------------

def test_create_page_basic():
    params = _make_params()
    with set_page(Page):
        page = create_page([1, 2, 3], total=3, params=params)
    assert page.items == [1, 2, 3]
    assert page.total == 3


def test_create_page_with_params_kwarg():
    params = _make_params()
    with set_page(Page):
        page = create_page([1, 2], total=2, params=params)
    assert page.items == [1, 2]


def test_create_page_with_total_kwarg():
    params = _make_params()
    with set_page(Page):
        page = create_page([1], total=1, params=params)
    assert page.total == 1


# ---------------------------------------------------------------------------
# response / request context vars
# ---------------------------------------------------------------------------

def test_response_raises_when_not_set():
    with pytest.raises(RuntimeError, match="response context var must be set"):
        response()


def test_request_raises_when_not_set():
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


def test_ctx_var_with_reset_resets_to_previous():
    var: ContextVar[int] = ContextVar("test_var2")
    token = var.set(1)
    with _ctx_var_with_reset(var, 2):
        assert var.get() == 2
    assert var.get() == 1
    var.reset(token)


# ---------------------------------------------------------------------------
# set_params / set_page / set_items_transformer
# ---------------------------------------------------------------------------

def test_set_params_context_manager():
    params = _make_params()
    with set_params(params):
        assert resolve_params() is params
    with pytest.raises(UninitializedConfigurationError):
        resolve_params()


def test_set_page_context_manager():
    with set_page(Page):
        assert resolve_page() is Page
    with pytest.raises(UninitializedConfigurationError):
        resolve_page()


def test_set_items_transformer_context_manager():
    transformer = lambda x: x
    with set_items_transformer(transformer):
        assert resolve_items_transformer() is transformer
    assert resolve_items_transformer() is None


# ---------------------------------------------------------------------------
# resolve_page
# ---------------------------------------------------------------------------

def test_resolve_page_raises_when_not_set():
    with pytest.raises(UninitializedConfigurationError):
        resolve_page()


def test_resolve_page_from_context():
    with set_page(Page):
        assert resolve_page() is Page


def test_resolve_page_from_params():
    params = _make_params()
    # Params is connected to Page via __page_type__
    result = resolve_page(params)
    assert result is Page


# ---------------------------------------------------------------------------
# async_wrapped
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_async_wrapped_returns_obj():
    obj = [1, 2, 3]
    result = await async_wrapped(obj)
    assert result is obj


# ---------------------------------------------------------------------------
# apply_items_transformer
# ---------------------------------------------------------------------------

def test_apply_items_transformer_no_transformer_sync():
    items = [1, 2, 3]
    result = apply_items_transformer(items)
    assert result is items


@pytest.mark.asyncio
async def test_apply_items_transformer_no_transformer_async():
    items = [1, 2, 3]
    result = await apply_items_transformer(items, async_=True)
    assert result is items


def test_apply_items_transformer_sync_transformer():
    items = [1, 2, 3]
    transformer = lambda x: list(reversed(x))
    result = apply_items_transformer(items, transformer)
    assert result == [3, 2, 1]


@pytest.mark.asyncio
async def test_apply_items_transformer_sync_transformer_async_mode():
    items = [1, 2, 3]
    transformer = lambda x: list(reversed(x))
    result = await apply_items_transformer(items, transformer, async_=True)
    assert result == [3, 2, 1]


@pytest.mark.asyncio
async def test_apply_items_transformer_async_transformer():
    items = [1, 2, 3]

    async def async_transformer(x):
        return list(reversed(x))

    result = await apply_items_transformer(items, async_transformer, async_=True)
    assert result == [3, 2, 1]


def test_apply_items_transformer_async_transformer_raises_if_sync_mode():
    items = [1, 2, 3]

    async def async_transformer(x):
        return list(reversed(x))

    with pytest.raises(ValueError, match="async_=False"):
        apply_items_transformer(items, async_transformer)


def test_apply_items_transformer_from_context():
    items = [1, 2, 3]
    transformer = lambda x: [i * 2 for i in x]
    with set_items_transformer(transformer):
        result = apply_items_transformer(items)
    assert result == [2, 4, 6]


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
# _patch_openapi
# ---------------------------------------------------------------------------

def test_patch_openapi_merges_paths():
    dst = {"paths": {"/a": {}}, "components": {"schemas": {"A": {}}}}
    src = {"paths": {"/b": {}}, "components": {"schemas": {"B": {}}}}
    _patch_openapi(dst, src)
    assert "/b" in dst["paths"]
    assert "B" in dst["components"]["schemas"]
    assert "/a" in dst["paths"]


def test_patch_openapi_missing_keys():
    dst = {}
    src = {"paths": {"/b": {}}}
    _patch_openapi(dst, src)  # should not raise


# ---------------------------------------------------------------------------
# add_pagination / pagination_ctx via FastAPI app
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_pagination_adds_dependency():
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    async def get_items() -> Any:
        params = resolve_params()
        return create_page([1, 2, 3], total=3, params=params)

    add_pagination(app)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/items")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_pagination_ctx_sets_page_and_params():
    app = FastAPI()

    dep = pagination_ctx(Page)

    from fastapi import Depends

    @app.get("/items2", response_model=Page[int])
    async def get_items2(_params: Any = Depends(dep)) -> Any:
        params = resolve_params()
        return create_page([1, 2, 3], total=3, params=params)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/items2")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_add_pagination_lifespan():
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    async def get_items() -> Any:
        params = resolve_params()
        return create_page([1, 2, 3], total=3, params=params)

    add_pagination(app)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/items")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_full_pagination_flow():
    app = FastAPI()

    @app.get("/things", response_model=Page[int])
    async def get_things() -> Any:
        params = resolve_params()
        all_items = list(range(100))
        raw = params.to_raw_params()
        items = all_items[raw.offset : raw.offset + raw.limit] if raw.limit is not None else all_items
        return create_page(items, total=len(all_items), params=params)

    add_pagination(app)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/things?page=2&size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 2
    assert data["size"] == 10
    assert len(data["items"]) == 10


# ---------------------------------------------------------------------------
# _create_params_dependency - uncovered lines
# ---------------------------------------------------------------------------

class _SimpleParams(AbstractParams):
    """Non-pydantic params class to exercise line 241 (else branch)."""

    def __init__(self, page: int = 1, size: int = 10) -> None:
        self.page = page
        self.size = size

    def to_raw_params(self) -> RawParams:
        return RawParams(limit=self.size, offset=(self.page - 1) * self.size)


@pytest.mark.asyncio
async def test_create_params_dependency_non_pydantic_model():
    """Line 241: val = params(*args, **kwargs) when params is not a pydantic BaseModel."""
    dep = _create_params_dependency(_SimpleParams)
    collected = []
    async for val in dep(page=2, size=5):
        collected.append(val)
    assert len(collected) == 1
    assert isinstance(collected[0], _SimpleParams)
    assert collected[0].page == 2
    assert collected[0].size == 5


class _RequiredParams(BaseModel, AbstractParams):
    """Pydantic v2 model with required fields (no defaults) to exercise line 260."""

    page: int
    size: int

    def to_raw_params(self) -> RawParams:
        return RawParams(limit=self.size, offset=(self.page - 1) * self.size)


@pytest.mark.asyncio
async def test_create_params_dependency_pydantic_required_fields():
    """Line 260: param_default = inspect.Parameter.empty when field has no default."""
    dep = _create_params_dependency(_RequiredParams)
    collected = []
    async for val in dep(page=1, size=20):
        collected.append(val)
    assert len(collected) == 1
    assert isinstance(collected[0], _RequiredParams)
    assert collected[0].page == 1
    assert collected[0].size == 20


@pytest.mark.asyncio
async def test_create_params_dependency_old_pydantic_v2_path(mocker):
    """Lines 270-271: _get_param for older pydantic v2 (IS_PYDANTIC_V2_12_5_OR_HIGHER=False)."""
    mocker.patch("fastapi_pagination.api.IS_PYDANTIC_V2_12_5_OR_HIGHER", False)
    dep = _create_params_dependency(Params)
    collected = []
    async for val in dep(page=1, size=10):
        collected.append(val)
    assert len(collected) == 1
    assert isinstance(collected[0], Params)
