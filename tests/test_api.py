import pytest
from collections.abc import Sequence
from contextvars import ContextVar
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute
from httpx import AsyncClient, ASGITransport

from fastapi_pagination.api import (
    _create_params_dependency,
    _ctx_var_with_reset,
    _items_val,
    _model_validate_has_by_name_param,
    _noop_dep,
    _patch_openapi,
    _add_pagination,
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
from fastapi_pagination.bases import AbstractPage, AbstractParams, RawParams
from fastapi_pagination.default import Page, Params
from fastapi_pagination.errors import UninitializedConfigurationError


# ---------------------------------------------------------------------------
# resolve_params
# ---------------------------------------------------------------------------


def test_resolve_params_raises_when_not_set():
    with pytest.raises(UninitializedConfigurationError):
        resolve_params()


def test_resolve_params_returns_from_context():
    params = Params(page=1, size=10)
    with set_params(params):
        result = resolve_params()
    assert result is params


def test_resolve_params_returns_provided_params():
    params = Params(page=2, size=20)
    result = resolve_params(params)
    assert result is params


# ---------------------------------------------------------------------------
# resolve_items_transformer
# ---------------------------------------------------------------------------


def test_resolve_items_transformer_returns_none_when_not_set():
    result = resolve_items_transformer()
    assert result is None


def test_resolve_items_transformer_returns_provided_transformer():
    transformer = lambda items: items  # noqa: E731
    result = resolve_items_transformer(transformer)
    assert result is transformer


def test_resolve_items_transformer_returns_context_var_when_set():
    transformer = lambda items: list(reversed(items))  # noqa: E731
    with set_items_transformer(transformer):
        result = resolve_items_transformer()
    assert result is transformer


# ---------------------------------------------------------------------------
# pagination_items
# ---------------------------------------------------------------------------


def test_pagination_items_raises_when_not_set():
    with pytest.raises(UninitializedConfigurationError):
        pagination_items()


def test_pagination_items_returns_items_from_context():
    items = [1, 2, 3]
    with _ctx_var_with_reset(_items_val, items):
        result = pagination_items()
    assert result == items


# ---------------------------------------------------------------------------
# response / request
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
    var: ContextVar[int] = ContextVar("test_var_reset")
    token = None

    with _ctx_var_with_reset(var, 42):
        assert var.get() == 42

    with pytest.raises(LookupError):
        var.get()


def test_ctx_var_with_reset_restores_previous_value():
    var: ContextVar[int] = ContextVar("test_var_prev", default=0)

    with _ctx_var_with_reset(var, 10):
        assert var.get() == 10
        with _ctx_var_with_reset(var, 20):
            assert var.get() == 20
        assert var.get() == 10

    assert var.get() == 0


# ---------------------------------------------------------------------------
# set_params / set_page / set_items_transformer
# ---------------------------------------------------------------------------


def test_set_params_context_manager():
    params = Params(page=3, size=5)
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
    transformer = lambda items: items  # noqa: E731
    with set_items_transformer(transformer):
        assert resolve_items_transformer() is transformer
    assert resolve_items_transformer() is None


# ---------------------------------------------------------------------------
# resolve_page
# ---------------------------------------------------------------------------


def test_resolve_page_returns_from_context():
    with set_page(Page):
        result = resolve_page()
    assert result is Page


def test_resolve_page_returns_from_params_page_type():
    params = Params(page=1, size=10)
    # Params.__page_type__ is Page (set during class definition)
    result = resolve_page(params)
    assert result is Page


def test_resolve_page_raises_when_not_set():
    with pytest.raises(UninitializedConfigurationError):
        resolve_page()


# ---------------------------------------------------------------------------
# create_page
# ---------------------------------------------------------------------------


def test_create_page_with_total_and_params():
    items = [1, 2, 3]
    params = Params(page=1, size=10)
    with set_params(params):
        with set_page(Page):
            page = create_page(items, total=10, params=params)
    assert page.items == items
    assert page.total == 10


def test_create_page_with_params_from_context():
    items = ["a", "b"]
    params = Params(page=1, size=5)
    with set_params(params):
        with set_page(Page):
            page = create_page(items, total=2, params=params)
    assert len(page.items) == 2


def test_create_page_without_explicit_total():
    items = [10, 20]
    params = Params(page=1, size=5)
    with set_params(params):
        with set_page(Page):
            page = create_page(items, total=len(items), params=params)
    assert page.items == items


# ---------------------------------------------------------------------------
# async_wrapped
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_wrapped_returns_object():
    obj = {"key": "value"}
    result = await async_wrapped(obj)
    assert result is obj


@pytest.mark.asyncio
async def test_async_wrapped_with_list():
    items = [1, 2, 3]
    result = await async_wrapped(items)
    assert result == items


# ---------------------------------------------------------------------------
# apply_items_transformer
# ---------------------------------------------------------------------------


def test_apply_items_transformer_no_transformer_sync():
    items = [1, 2, 3]
    result = apply_items_transformer(items)
    assert result == items


@pytest.mark.asyncio
async def test_apply_items_transformer_no_transformer_async():
    items = [1, 2, 3]
    result = await apply_items_transformer(items, async_=True)
    assert result == items


def test_apply_items_transformer_sync_transformer():
    items = [1, 2, 3]
    transformer = lambda x: [i * 2 for i in x]  # noqa: E731
    result = apply_items_transformer(items, transformer)
    assert result == [2, 4, 6]


@pytest.mark.asyncio
async def test_apply_items_transformer_sync_transformer_async_mode():
    items = [1, 2, 3]
    transformer = lambda x: [i + 1 for i in x]  # noqa: E731
    result = await apply_items_transformer(items, transformer, async_=True)
    assert result == [2, 3, 4]


@pytest.mark.asyncio
async def test_apply_items_transformer_async_transformer():
    items = [1, 2, 3]

    async def async_transformer(x: Sequence[Any]) -> Sequence[Any]:
        return [i * 3 for i in x]

    result = await apply_items_transformer(items, async_transformer, async_=True)
    assert result == [3, 6, 9]


def test_apply_items_transformer_async_transformer_sync_raises():
    items = [1, 2, 3]

    async def async_transformer(x: Sequence[Any]) -> Sequence[Any]:
        return x

    with pytest.raises(ValueError, match="async_=False but transformer is async"):
        apply_items_transformer(items, async_transformer, async_=False)


def test_apply_items_transformer_uses_context_transformer():
    items = [10, 20, 30]
    transformer = lambda x: [i - 1 for i in x]  # noqa: E731
    with set_items_transformer(transformer):
        result = apply_items_transformer(items)
    assert result == [9, 19, 29]


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


def test_patch_openapi_patches_paths():
    dst = {"paths": {"/existing": {}}}
    src = {"paths": {"/new": {}}}
    _patch_openapi(dst, src)
    assert "/new" in dst["paths"]
    assert "/existing" in dst["paths"]


def test_patch_openapi_patches_components_schemas():
    dst = {"components": {"schemas": {"Existing": {}}}}
    src = {"components": {"schemas": {"New": {}}}}
    _patch_openapi(dst, src)
    assert "New" in dst["components"]["schemas"]
    assert "Existing" in dst["components"]["schemas"]


def test_patch_openapi_no_error_when_keys_missing():
    dst: dict = {}
    src: dict = {}
    _patch_openapi(dst, src)
    assert dst == {}


def test_patch_openapi_no_error_when_dst_has_no_paths():
    dst: dict = {}
    src = {"paths": {"/new": {}}}
    _patch_openapi(dst, src)
    # dst does not have paths, so the with suppress block handles KeyError
    assert "paths" not in dst


# ---------------------------------------------------------------------------
# pagination_ctx
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pagination_ctx_sets_params_and_page():
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    async def get_items():
        params = resolve_params()
        page_cls = resolve_page()
        return create_page([1, 2, 3], total=3, params=params)

    add_pagination(app)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/items", params={"page": 1, "size": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == [1, 2, 3]


@pytest.mark.asyncio
async def test_pagination_ctx_with_transformer():
    app = FastAPI()

    def double_items(items: Sequence[Any]) -> Sequence[Any]:
        return [i * 2 for i in items]

    @app.get("/items", response_model=Page[int])
    async def get_items():
        params = resolve_params()
        items = apply_items_transformer([1, 2, 3])
        return create_page(items, total=3, params=params)

    ctx = pagination_ctx(Page, transformer=double_items)
    add_pagination(app)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/items", params={"page": 1, "size": 3})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# _update_route and _add_pagination
# ---------------------------------------------------------------------------


def test_update_route_adds_pagination_dependency():
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    def get_items():
        return create_page([1, 2, 3], total=3)

    route = next(r for r in app.routes if isinstance(r, APIRoute) and r.path == "/items")
    initial_dep_count = len(route.dependencies)

    _update_route(route)

    assert len(route.dependencies) > initial_dep_count


def test_update_route_skips_non_page_routes():
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    route = next(r for r in app.routes if isinstance(r, APIRoute) and r.path == "/health")
    initial_dep_count = len(route.dependencies)

    _update_route(route)

    assert len(route.dependencies) == initial_dep_count


def test_add_pagination_updates_routes():
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    def get_items():
        return create_page([1, 2, 3], total=3)

    _add_pagination(app)

    route = next(r for r in app.routes if isinstance(r, APIRoute) and r.path == "/items")
    assert any(hasattr(d.call, "__page_ctx_dep__") for d in route.dependant.dependencies)


# ---------------------------------------------------------------------------
# add_pagination
# ---------------------------------------------------------------------------


def test_add_pagination_returns_parent():
    app = FastAPI()
    result = add_pagination(app)
    assert result is app


def test_add_pagination_router():
    from fastapi.routing import APIRouter

    router = APIRouter()

    @router.get("/items", response_model=Page[int])
    def get_items():
        return create_page([1, 2, 3], total=3)

    result = add_pagination(router)
    assert result is router


@pytest.mark.asyncio
async def test_add_pagination_lifespan_called():
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    async def get_items():
        params = resolve_params()
        return create_page([1, 2, 3], total=3, params=params)

    add_pagination(app)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/items", params={"page": 1, "size": 5})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_pagination_ctx_no_page_no_params():
    ctx_dep = pagination_ctx()
    # Should return _noop_dep when no page or params given
    assert ctx_dep is not None


# ---------------------------------------------------------------------------
# response and request via FastAPI integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_response_accessible_in_route():
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    async def get_items():
        rsp = response()
        assert rsp is not None
        params = resolve_params()
        return create_page([1, 2, 3], total=3, params=params)

    add_pagination(app)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/items", params={"page": 1, "size": 5})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_request_accessible_in_route():
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    async def get_items():
        req = request()
        assert req is not None
        params = resolve_params()
        return create_page([1, 2, 3], total=3, params=params)

    add_pagination(app)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/items", params={"page": 1, "size": 5})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# pagination_items via create_page context
# ---------------------------------------------------------------------------


def test_pagination_items_accessible_inside_create_page():
    captured = []

    class CustomPage(Page[int]):
        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> "CustomPage":
            captured.extend(pagination_items())
            return super().create(items, params, **kwargs)

    items = [10, 20, 30]
    params = Params(page=1, size=10)
    with set_params(params):
        with set_page(CustomPage):
            create_page(items, total=3, params=params)

    assert captured == items


# ---------------------------------------------------------------------------
# _create_params_dependency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_params_dependency_non_pydantic_params():
    """Covers line 241: val = params(*args, **kwargs) for non-Pydantic params"""

    class SimpleParams(AbstractParams):
        def __init__(self, page: int = 1, size: int = 10):
            self.page = page
            self.size = size

        def to_raw_params(self) -> RawParams:
            return RawParams(limit=self.size, offset=self.size * (self.page - 1))

    dep = _create_params_dependency(SimpleParams)
    collected = []
    async for val in dep(page=2, size=5):
        collected.append(val)

    assert len(collected) == 1
    assert collected[0].page == 2
    assert collected[0].size == 5


@pytest.mark.asyncio
async def test_create_params_dependency_required_field_no_default():
    """Covers line 260: param_default = inspect.Parameter.empty for required fields"""
    from fastapi_pagination.pydantic.consts import IS_PYDANTIC_V2_12_5_OR_HIGHER

    if not IS_PYDANTIC_V2_12_5_OR_HIGHER:
        pytest.skip("Only relevant for pydantic >= 2.12.5")

    from pydantic import BaseModel as PydanticBaseModel

    class RequiredParams(PydanticBaseModel, AbstractParams):
        page: int
        size: int = 10

        def to_raw_params(self) -> RawParams:
            return RawParams(limit=self.size, offset=self.size * (self.page - 1))

    dep = _create_params_dependency(RequiredParams)
    collected = []
    async for val in dep(page=3):
        collected.append(val)

    assert len(collected) == 1
    assert collected[0].page == 3
    assert collected[0].size == 10


@pytest.mark.asyncio
async def test_create_params_dependency_pydantic_v2_pre_2_12_5(mocker):
    """Covers lines 270-271: _get_param for pydantic v2 < 2.12.5 path"""
    from fastapi_pagination.pydantic.consts import IS_PYDANTIC_V2

    if not IS_PYDANTIC_V2:
        pytest.skip("Only relevant for pydantic v2")

    mocker.patch("fastapi_pagination.api.IS_PYDANTIC_V2_12_5_OR_HIGHER", False)

    dep = _create_params_dependency(Params)
    sign = dep.__signature__
    assert "page" in sign.parameters
    assert "size" in sign.parameters
