import pytest
from contextvars import ContextVar
from typing import Any
from collections.abc import Sequence

from fastapi import Depends, FastAPI
from fastapi.routing import APIRouter
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from fastapi_pagination.api import (
    _add_pagination,
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
    request as get_request,
    resolve_items_transformer,
    resolve_page,
    resolve_params,
    response as get_response,
    set_items_transformer,
    set_page,
    set_params,
)
from fastapi_pagination.bases import AbstractPage, AbstractParams
from fastapi_pagination.default import Page, Params
from fastapi_pagination.errors import UninitializedConfigurationError


# ---------------------------------------------------------------------------
# resolve_params
# ---------------------------------------------------------------------------


def test_resolve_params_raises_when_unset():
    with pytest.raises(UninitializedConfigurationError):
        resolve_params()


def test_resolve_params_returns_passed_params():
    params = Params(page=1, size=10)
    result = resolve_params(params)
    assert result is params


def test_resolve_params_from_context():
    params = Params(page=2, size=20)
    with set_params(params):
        result = resolve_params()
    assert result is params


# ---------------------------------------------------------------------------
# resolve_items_transformer
# ---------------------------------------------------------------------------


def test_resolve_items_transformer_returns_none_when_unset():
    result = resolve_items_transformer()
    assert result is None


def test_resolve_items_transformer_returns_passed_transformer():
    def my_transformer(items: Sequence[Any]) -> Sequence[Any]:
        return items

    result = resolve_items_transformer(my_transformer)
    assert result is my_transformer


def test_resolve_items_transformer_from_context():
    def my_transformer(items: Sequence[Any]) -> Sequence[Any]:
        return items

    with set_items_transformer(my_transformer):
        result = resolve_items_transformer()
    assert result is my_transformer


def test_resolve_items_transformer_context_cleared_after_exit():
    def my_transformer(items: Sequence[Any]) -> Sequence[Any]:
        return items

    with set_items_transformer(my_transformer):
        pass

    assert resolve_items_transformer() is None


# ---------------------------------------------------------------------------
# pagination_items
# ---------------------------------------------------------------------------


def test_pagination_items_raises_when_unset():
    with pytest.raises(UninitializedConfigurationError):
        pagination_items()


# ---------------------------------------------------------------------------
# create_page
# ---------------------------------------------------------------------------


def test_create_page_with_set_page():
    params = Params(page=1, size=3)
    items = [1, 2, 3]
    with set_page(Page):
        page = create_page(items, total=3, params=params)
    assert list(page.items) == items
    assert page.total == 3


def test_create_page_with_params_arg():
    params = Params(page=1, size=3)
    items = [10, 20, 30]
    with set_page(Page):
        page = create_page(items, total=3, params=params)
    assert list(page.items) == items
    assert page.total == 3


def test_create_page_sets_pagination_items_in_context():
    params = Params(page=1, size=5)
    items = [1, 2, 3]
    captured: list[Any] = []

    class CapturingPage(Page[Any]):
        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> "CapturingPage":
            captured.extend(pagination_items())
            return super().create(items, params, **kwargs)

    with set_page(CapturingPage):
        create_page(items, total=3, params=params)

    assert captured == items


# ---------------------------------------------------------------------------
# response / request
# ---------------------------------------------------------------------------


def test_response_raises_when_unset():
    with pytest.raises(RuntimeError, match="response context var must be set"):
        get_response()


def test_request_raises_when_unset():
    with pytest.raises(RuntimeError, match="request context var must be set"):
        get_request()


# ---------------------------------------------------------------------------
# _ctx_var_with_reset
# ---------------------------------------------------------------------------


def test_ctx_var_with_reset_sets_value():
    var: ContextVar[str] = ContextVar("_test_ctx_var_with_reset_sets")
    with _ctx_var_with_reset(var, "hello"):
        assert var.get() == "hello"


def test_ctx_var_with_reset_restores_after_exit():
    var: ContextVar[str] = ContextVar("_test_ctx_var_with_reset_restores")
    with _ctx_var_with_reset(var, "value"):
        pass
    with pytest.raises(LookupError):
        var.get()


def test_ctx_var_with_reset_nested():
    var: ContextVar[str] = ContextVar("_test_ctx_var_with_reset_nested")
    with _ctx_var_with_reset(var, "outer"):
        assert var.get() == "outer"
        with _ctx_var_with_reset(var, "inner"):
            assert var.get() == "inner"
        assert var.get() == "outer"


# ---------------------------------------------------------------------------
# set_params / set_page / set_items_transformer
# ---------------------------------------------------------------------------


def test_set_params_makes_params_resolvable():
    params = Params(page=3, size=15)
    with set_params(params):
        assert resolve_params() is params


def test_set_page_makes_page_resolvable():
    with set_page(Page):
        assert resolve_page() is Page


def test_set_items_transformer_makes_transformer_resolvable():
    def tf(items: Sequence[Any]) -> Sequence[Any]:
        return list(reversed(items))

    with set_items_transformer(tf):
        assert resolve_items_transformer() is tf


# ---------------------------------------------------------------------------
# resolve_page
# ---------------------------------------------------------------------------


def test_resolve_page_raises_when_unset():
    with pytest.raises(UninitializedConfigurationError):
        resolve_page()


def test_resolve_page_from_context():
    with set_page(Page):
        result = resolve_page()
    assert result is Page


def test_resolve_page_from_params_page_type():
    params = Params(page=1, size=10)
    result = resolve_page(params)
    assert result is Page


# ---------------------------------------------------------------------------
# async_wrapped
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_wrapped_returns_value():
    assert await async_wrapped(42) == 42


@pytest.mark.asyncio
async def test_async_wrapped_returns_same_object():
    items = [1, 2, 3]
    result = await async_wrapped(items)
    assert result is items


# ---------------------------------------------------------------------------
# apply_items_transformer
# ---------------------------------------------------------------------------


def test_apply_items_transformer_no_transformer_returns_items():
    items = [1, 2, 3]
    result = apply_items_transformer(items)
    assert result is items


def test_apply_items_transformer_sync_transformer():
    items = [1, 2, 3]

    def doubler(x: Sequence[Any]) -> Sequence[Any]:
        return [i * 2 for i in x]

    result = apply_items_transformer(items, doubler)
    assert result == [2, 4, 6]


def test_apply_items_transformer_sync_transformer_from_context():
    items = [1, 2, 3]

    def adder(x: Sequence[Any]) -> Sequence[Any]:
        return [i + 10 for i in x]

    with set_items_transformer(adder):
        result = apply_items_transformer(items)
    assert result == [11, 12, 13]


def test_apply_items_transformer_async_transformer_sync_mode_raises():
    items = [1, 2, 3]

    async def async_tf(x: Sequence[Any]) -> Sequence[Any]:
        return x

    with pytest.raises(ValueError, match="apply_items_transformer called with async_=False but transformer is async"):
        apply_items_transformer(items, async_tf)


@pytest.mark.asyncio
async def test_apply_items_transformer_async_mode_no_transformer():
    items = [1, 2, 3]
    result = await apply_items_transformer(items, async_=True)
    assert result is items


@pytest.mark.asyncio
async def test_apply_items_transformer_async_mode_sync_transformer():
    items = [1, 2, 3]

    def doubler(x: Sequence[Any]) -> Sequence[Any]:
        return [i * 2 for i in x]

    result = await apply_items_transformer(items, doubler, async_=True)
    assert result == [2, 4, 6]


@pytest.mark.asyncio
async def test_apply_items_transformer_async_transformer():
    items = [1, 2, 3]

    async def async_tf(x: Sequence[Any]) -> Sequence[Any]:
        return [i * 3 for i in x]

    result = await apply_items_transformer(items, async_tf, async_=True)
    assert result == [3, 6, 9]


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
    dst = {"paths": {"/a": {"get": {}}}}
    src = {"paths": {"/b": {"post": {}}}}
    _patch_openapi(dst, src)
    assert "/a" in dst["paths"]
    assert "/b" in dst["paths"]


def test_patch_openapi_merges_schemas():
    dst = {"components": {"schemas": {"ModelA": {}}}}
    src = {"components": {"schemas": {"ModelB": {}}}}
    _patch_openapi(dst, src)
    assert "ModelA" in dst["components"]["schemas"]
    assert "ModelB" in dst["components"]["schemas"]


def test_patch_openapi_missing_paths_in_dst():
    dst: dict[str, Any] = {}
    src = {"paths": {"/a": {}}}
    _patch_openapi(dst, src)
    assert "paths" not in dst


def test_patch_openapi_missing_paths_in_src():
    dst = {"paths": {"/a": {}}}
    src: dict[str, Any] = {}
    _patch_openapi(dst, src)
    assert "/a" in dst["paths"]


def test_patch_openapi_missing_components():
    dst: dict[str, Any] = {}
    src = {"components": {"schemas": {"X": {}}}}
    _patch_openapi(dst, src)
    assert "components" not in dst


# ---------------------------------------------------------------------------
# add_pagination / _add_pagination
# ---------------------------------------------------------------------------


def test_add_pagination_returns_same_app():
    app = FastAPI()
    result = add_pagination(app)
    assert result is app


def test_add_pagination_returns_same_router():
    router = APIRouter()
    result = add_pagination(router)
    assert result is router


def test_add_pagination_fastapi_app_with_route():
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    def get_items() -> Any:
        params = resolve_params()
        items = list(range(params.size))
        return create_page(items, total=100, params=params)

    add_pagination(app)

    with TestClient(app) as client:
        response = client.get("/items?page=1&size=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 5


def test_add_pagination_is_idempotent():
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    def get_items() -> Any:
        params = resolve_params()
        return create_page(list(range(params.size)), total=10, params=params)

    add_pagination(app)
    add_pagination(app)

    with TestClient(app) as client:
        response = client.get("/items?page=1&size=3")
    assert response.status_code == 200


def test_add_pagination_patches_prebuilt_openapi():
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    def get_items() -> Any:
        pass

    schema_before = app.openapi()
    assert schema_before is not None

    add_pagination(app)


def test_add_pagination_lifespan_wraps_context():
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    def get_items() -> Any:
        params = resolve_params()
        return create_page(list(range(params.size)), total=params.size, params=params)

    add_pagination(app)

    with TestClient(app) as client:
        response = client.get("/items?page=1&size=4")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# pagination_ctx (integration via TestClient)
# ---------------------------------------------------------------------------


def test_pagination_ctx_no_args():
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    async def get_items(_: Any = Depends(pagination_ctx(Page))) -> Any:
        params = resolve_params()
        return create_page(list(range(params.size)), total=params.size, params=params)

    add_pagination(app)

    with TestClient(app) as client:
        response = client.get("/items?page=1&size=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3


def test_pagination_ctx_with_transformer():
    app = FastAPI()

    def double(items: Sequence[Any]) -> Sequence[Any]:
        return [i * 2 for i in items]

    @app.get("/items", response_model=Page[int])
    async def get_items(_: Any = Depends(pagination_ctx(Page, transformer=double))) -> Any:
        params = resolve_params()
        raw_items = list(range(params.size))
        return create_page(apply_items_transformer(raw_items), total=params.size, params=params)

    add_pagination(app)

    with TestClient(app) as client:
        response = client.get("/items?page=1&size=3")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == [0, 2, 4]


@pytest.mark.asyncio
async def test_pagination_ctx_async_client():
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    async def get_items(_: Any = Depends(pagination_ctx(Page))) -> Any:
        params = resolve_params()
        items = list(range(params.size))
        return create_page(items, total=100, params=params)

    add_pagination(app)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/items?page=1&size=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 5


# ---------------------------------------------------------------------------
# pagination_ctx with params only (no page)
# ---------------------------------------------------------------------------


def test_pagination_ctx_with_params_only():
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    async def get_items(_: Any = Depends(pagination_ctx(params=Params))) -> Any:
        params = resolve_params()
        return create_page(list(range(params.size)), total=params.size, params=params)

    add_pagination(app)

    with TestClient(app) as client:
        response = client.get("/items?page=1&size=4")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 4
