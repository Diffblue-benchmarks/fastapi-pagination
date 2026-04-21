import pytest
from starlette.requests import URL
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from fastapi_pagination.api import add_pagination, create_page, resolve_params
from fastapi_pagination.links.bases import (
    Links,
    _resolve_path,
    _update_path,
    create_links,
)


# ---------------------------------------------------------------------------
# _resolve_path
# ---------------------------------------------------------------------------


def test_resolve_path_with_query_defaults_to_path_only():
    url = URL("http://example.com/items?page=1&size=10")
    result = _resolve_path(url)
    assert result == "/items?page=1&size=10"


def test_resolve_path_without_query_defaults_to_path_only():
    url = URL("http://example.com/items")
    result = _resolve_path(url)
    assert result == "/items"


def test_resolve_path_only_path_none_with_query():
    url = URL("http://example.com/items?page=2")
    result = _resolve_path(url, only_path=None)
    assert result == "/items?page=2"


def test_resolve_path_only_path_none_without_query():
    url = URL("http://example.com/items")
    result = _resolve_path(url, only_path=None)
    assert result == "/items"


def test_resolve_path_only_path_false_returns_full_url():
    url = URL("http://example.com/items?page=1")
    result = _resolve_path(url, only_path=False)
    assert result == "http://example.com/items?page=1"


def test_resolve_path_only_path_true_with_query():
    url = URL("http://example.com/items?size=5")
    result = _resolve_path(url, only_path=True)
    assert result == "/items?size=5"


def test_resolve_path_only_path_true_without_query():
    url = URL("http://example.com/items")
    result = _resolve_path(url, only_path=True)
    assert result == "/items"


# ---------------------------------------------------------------------------
# _update_path
# ---------------------------------------------------------------------------


def test_update_path_returns_none_for_none_params():
    url = URL("http://example.com/items?page=1")
    result = _update_path(url, None)
    assert result is None


def test_update_path_with_mapping_returns_updated_path():
    url = URL("http://example.com/items?page=1&size=10")
    result = _update_path(url, {"page": 3})
    assert result is not None
    assert "page=3" in result
    assert result.startswith("/items")


def test_update_path_with_only_path_false():
    url = URL("http://example.com/items?page=1")
    result = _update_path(url, {"page": 2}, only_path=False)
    assert result is not None
    assert result.startswith("http://example.com")
    assert "page=2" in result


def test_update_path_adds_new_query_params():
    url = URL("http://example.com/items")
    result = _update_path(url, {"offset": 10, "limit": 5})
    assert result is not None
    assert "offset=10" in result
    assert "limit=5" in result


# ---------------------------------------------------------------------------
# create_links via FastAPI integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_links_returns_links_object():
    from fastapi_pagination.default import Page

    captured = {}
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    async def get_items():
        params = resolve_params()
        links = create_links(
            first={"page": 1},
            last={"page": 5},
            next={"page": 2},
            prev=None,
        )
        captured["links"] = links
        return create_page([1, 2, 3], total=15, params=params)

    add_pagination(app)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/items", params={"page": 1, "size": 3})

    assert resp.status_code == 200
    assert captured["links"] is not None
    assert captured["links"].first is not None
    assert captured["links"].last is not None
    assert captured["links"].next is not None
    assert captured["links"].prev is None


@pytest.mark.asyncio
async def test_create_links_with_only_path_false():
    from fastapi_pagination.default import Page

    captured = {}
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    async def get_items():
        params = resolve_params()
        links = create_links(
            first={"page": 1},
            last={"page": 3},
            next=None,
            prev=None,
            only_path=False,
        )
        captured["links"] = links
        return create_page([1, 2, 3], total=9, params=params)

    add_pagination(app)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/items", params={"page": 1, "size": 3})

    assert resp.status_code == 200
    assert captured["links"].self is not None
    assert captured["links"].self.startswith("http")


@pytest.mark.asyncio
async def test_create_links_self_points_to_request_url():
    from fastapi_pagination.default import Page

    captured = {}
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    async def get_items():
        params = resolve_params()
        links = create_links(
            first={"page": 1},
            last={"page": 1},
            next=None,
            prev=None,
        )
        captured["links"] = links
        return create_page([1, 2, 3], total=3, params=params)

    add_pagination(app)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/items", params={"page": 1, "size": 3})

    assert resp.status_code == 200
    assert captured["links"].self is not None
    assert "/items" in captured["links"].self


# ---------------------------------------------------------------------------
# BaseUseLinks.customize_page_ns + __links_root_validator__
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_use_links_page_includes_links_field():
    from fastapi_pagination.links.default import Page

    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    async def get_items():
        params = resolve_params()
        return create_page(list(range(3)), total=30, params=params)

    add_pagination(app)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/items", params={"page": 1, "size": 3})

    assert resp.status_code == 200
    data = resp.json()
    assert "links" in data
    assert data["links"]["first"] is not None
    assert data["links"]["self"] is not None


@pytest.mark.asyncio
async def test_use_links_page_last_link_present():
    from fastapi_pagination.links.default import Page

    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    async def get_items():
        params = resolve_params()
        return create_page(list(range(5)), total=50, params=params)

    add_pagination(app)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/items", params={"page": 1, "size": 5})

    assert resp.status_code == 200
    data = resp.json()
    assert "links" in data
    assert data["links"]["last"] is not None


@pytest.mark.asyncio
async def test_use_links_page_next_prev_on_middle_page():
    from fastapi_pagination.links.default import Page

    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    async def get_items():
        params = resolve_params()
        return create_page(list(range(3)), total=30, params=params)

    add_pagination(app)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/items", params={"page": 2, "size": 3})

    assert resp.status_code == 200
    data = resp.json()
    assert "links" in data
    assert data["links"]["next"] is not None
    assert data["links"]["prev"] is not None


# ---------------------------------------------------------------------------
# BaseUseHeaderLinks._add_links_to_header (unit tests)
# ---------------------------------------------------------------------------


def test_add_links_to_header_with_some_links(mocker):
    from fastapi_pagination.links.default import UseHeaderLinks

    customizer = UseHeaderLinks()

    class MockHeaders(dict):
        pass

    class MockResponse:
        def __init__(self):
            self.headers = MockHeaders()

    mock_rsp = MockResponse()
    mocker.patch("fastapi_pagination.links.bases.response", return_value=mock_rsp)

    links = Links(first="/first", last="/last", next=None, prev=None)
    customizer._add_links_to_header(links)

    assert "Link" in mock_rsp.headers
    link_val = mock_rsp.headers["Link"]
    assert "first" in link_val
    assert "last" in link_val
    assert "next" not in link_val
    assert "prev" not in link_val


def test_add_links_to_header_with_all_none_links(mocker):
    from fastapi_pagination.links.default import UseHeaderLinks

    customizer = UseHeaderLinks()

    mock_response_fn = mocker.patch("fastapi_pagination.links.bases.response")

    links = Links(first=None, last=None, next=None, prev=None)
    customizer._add_links_to_header(links)

    mock_response_fn.assert_not_called()


def test_add_links_to_header_with_all_links(mocker):
    from fastapi_pagination.links.default import UseHeaderLinks

    customizer = UseHeaderLinks()

    class MockHeaders(dict):
        pass

    class MockResponse:
        def __init__(self):
            self.headers = MockHeaders()

    mock_rsp = MockResponse()
    mocker.patch("fastapi_pagination.links.bases.response", return_value=mock_rsp)

    links = Links(first="/first", last="/last", next="/next", prev="/prev")
    customizer._add_links_to_header(links)

    assert "Link" in mock_rsp.headers
    link_val = mock_rsp.headers["Link"]
    assert "first" in link_val
    assert "last" in link_val
    assert "next" in link_val
    assert "prev" in link_val


# ---------------------------------------------------------------------------
# BaseUseHeaderLinks.customize_page_ns + __add_links_to_header__ / __model_post_init__
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_use_header_links_adds_link_header():
    from fastapi_pagination.links.default import UseHeaderLinks
    from fastapi_pagination.customization import CustomizedPage
    from fastapi_pagination.default import Page as BasePage

    HeaderPage = CustomizedPage[BasePage[int], UseHeaderLinks()]

    app = FastAPI()

    @app.get("/items", response_model=HeaderPage)
    async def get_items():
        params = resolve_params()
        return create_page(list(range(3)), total=30, params=params)

    add_pagination(app)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/items", params={"page": 1, "size": 3})

    assert resp.status_code == 200
    assert "Link" in resp.headers
    assert "first" in resp.headers["Link"]
    assert "last" in resp.headers["Link"]


@pytest.mark.asyncio
async def test_use_header_links_next_prev_on_middle_page():
    from fastapi_pagination.links.default import UseHeaderLinks
    from fastapi_pagination.customization import CustomizedPage
    from fastapi_pagination.default import Page as BasePage

    HeaderPage = CustomizedPage[BasePage[int], UseHeaderLinks()]

    app = FastAPI()

    @app.get("/items", response_model=HeaderPage)
    async def get_items():
        params = resolve_params()
        return create_page(list(range(3)), total=30, params=params)

    add_pagination(app)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/items", params={"page": 2, "size": 3})

    assert resp.status_code == 200
    assert "Link" in resp.headers
    link_header = resp.headers["Link"]
    assert "next" in link_header
    assert "prev" in link_header


@pytest.mark.asyncio
async def test_use_header_links_no_next_on_last_page():
    from fastapi_pagination.links.default import UseHeaderLinks
    from fastapi_pagination.customization import CustomizedPage
    from fastapi_pagination.default import Page as BasePage

    HeaderPage = CustomizedPage[BasePage[int], UseHeaderLinks()]

    app = FastAPI()

    @app.get("/items", response_model=HeaderPage)
    async def get_items():
        params = resolve_params()
        return create_page([1, 2, 3], total=3, params=params)

    add_pagination(app)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/items", params={"page": 1, "size": 10})

    assert resp.status_code == 200
    assert "Link" in resp.headers
    link_header = resp.headers["Link"]
    assert "next" not in link_header
    assert "prev" not in link_header


# ---------------------------------------------------------------------------
# BaseUseHeaderLinks._customize_page_ns_pydantic_v1 / __add_links_to_header__
# ---------------------------------------------------------------------------


def test_customize_page_ns_pydantic_v1_adds_validator_to_namespace():
    from fastapi_pagination.links.default import UseHeaderLinks

    customizer = UseHeaderLinks()
    ns = {}
    customizer._customize_page_ns_pydantic_v1(object, ns)

    assert "__add_links_to_header__" in ns


# ---------------------------------------------------------------------------
# BaseUseLinks.customize_page_ns - pydantic v1 path (lines 111-119)
# ---------------------------------------------------------------------------


def test_customize_page_ns_pydantic_v1_adds_annotations_and_validator(mocker):
    from fastapi_pagination.links.default import UseLinks

    mocker.patch("fastapi_pagination.links.bases.IS_PYDANTIC_V2", False)
    customizer = UseLinks()
    ns = {}
    customizer.customize_page_ns(object, ns)

    assert "__annotations__" in ns
    assert "links" in ns["__annotations__"]
    assert "links" in ns
    assert "__links_root_validator__" in ns


def test_customize_page_ns_pydantic_v1_validator_sets_links_field(mocker):
    from fastapi_pagination.links.bases import Links
    from fastapi_pagination.links.default import UseLinks

    mocker.patch("fastapi_pagination.links.bases.IS_PYDANTIC_V2", False)
    customizer = UseLinks()
    mock_links = Links(first="/first", last="/last", next=None, prev=None)
    mocker.patch.object(customizer, "resolve_links", return_value=mock_links)

    ns = {}
    customizer.customize_page_ns(object, ns)

    validator = ns["__links_root_validator__"]

    inner_fn = getattr(validator, "func", None)
    if inner_fn is None:
        inner_fn = getattr(validator, "__func__", None)
    if inner_fn is None:
        inner_fn = getattr(validator, "__wrapped__", None)

    if inner_fn is None:
        pytest.skip("Cannot extract inner validator function from pydantic root_validator wrapper")

    values = {"total": 10, "items": []}
    result = inner_fn(None, values)

    assert result is values
    assert result["links"] is mock_links


def test_customize_page_ns_pydantic_v1_custom_field_name(mocker):
    from fastapi_pagination.links.default import UseLinks

    mocker.patch("fastapi_pagination.links.bases.IS_PYDANTIC_V2", False)
    customizer = UseLinks(field="pagination_links")
    ns = {}
    customizer.customize_page_ns(object, ns)

    assert "__annotations__" in ns
    assert "pagination_links" in ns["__annotations__"]
    assert "__links_root_validator__" in ns


def test_customize_page_ns_pydantic_v1_validator_body_executes(mocker):
    from fastapi_pagination.links.bases import Links
    from fastapi_pagination.links.default import UseHeaderLinks

    customizer = UseHeaderLinks()
    mock_links = Links(first="/first", last="/last", next=None, prev=None)
    mocker.patch.object(customizer, "resolve_links", return_value=mock_links)
    mock_add = mocker.patch.object(customizer, "_add_links_to_header")

    ns = {}
    customizer._customize_page_ns_pydantic_v1(object, ns)

    validator = ns["__add_links_to_header__"]

    # In pydantic v2, root_validator wraps the function in a Decorator with a 'func' attribute
    inner_fn = getattr(validator, "func", None)
    if inner_fn is None:
        inner_fn = getattr(validator, "__func__", None)
    if inner_fn is None:
        inner_fn = getattr(validator, "__wrapped__", None)

    if inner_fn is None:
        pytest.skip("Cannot extract inner validator function from pydantic root_validator wrapper")

    values = {"total": 10, "items": []}
    result = inner_fn(None, values)

    assert result == values
    mock_add.assert_called_once_with(mock_links)
