from __future__ import annotations

from dataclasses import dataclass

import pytest
from starlette.requests import Request
from starlette.responses import Response

from fastapi_pagination.api import _req_val, _rsp_val
from fastapi_pagination.links.bases import (
    BaseUseHeaderLinks,
    BaseUseLinks,
    Links,
    _resolve_path,
    _update_path,
    create_links,
)
from fastapi_pagination.pydantic.consts import IS_PYDANTIC_V2


def _make_request(path: str = "/api/v1/users", query: str = "page=1&size=10") -> Request:
    query_bytes = query.encode() if query else b""
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "query_string": query_bytes,
            "headers": [],
            "server": ("localhost", 8000),
            "scheme": "http",
        }
    )


@pytest.fixture
def req():
    return _make_request()


@pytest.fixture
def req_no_query():
    return _make_request(query="")


@pytest.fixture
def rsp():
    return Response()


@pytest.fixture
def with_request_ctx(req, rsp):
    token_req = _req_val.set(req)
    token_rsp = _rsp_val.set(rsp)
    yield req, rsp
    _req_val.reset(token_req)
    _rsp_val.reset(token_rsp)


# --- _resolve_path ---


def test_resolve_path_only_path_none_with_query(req):
    result = _resolve_path(req.url, only_path=None)
    assert result == "/api/v1/users?page=1&size=10"


def test_resolve_path_only_path_none_no_query(req_no_query):
    result = _resolve_path(req_no_query.url, only_path=None)
    assert result == "/api/v1/users"


def test_resolve_path_only_path_true_with_query(req):
    result = _resolve_path(req.url, only_path=True)
    assert result == "/api/v1/users?page=1&size=10"


def test_resolve_path_only_path_true_no_query(req_no_query):
    result = _resolve_path(req_no_query.url, only_path=True)
    assert result == "/api/v1/users"


def test_resolve_path_only_path_false(req):
    result = _resolve_path(req.url, only_path=False)
    assert result == "http://localhost:8000/api/v1/users?page=1&size=10"


def test_resolve_path_only_path_false_no_query(req_no_query):
    result = _resolve_path(req_no_query.url, only_path=False)
    assert result == "http://localhost:8000/api/v1/users"


# --- _update_path ---


def test_update_path_none_returns_none(req):
    result = _update_path(req.url, None)
    assert result is None


def test_update_path_with_params(req):
    result = _update_path(req.url, {"page": 2}, only_path=True)
    assert result is not None
    assert "page=2" in result
    assert result.startswith("/api/v1/users")


def test_update_path_full_url(req):
    result = _update_path(req.url, {"page": 3}, only_path=False)
    assert result is not None
    assert result.startswith("http://")
    assert "page=3" in result


# --- create_links ---


def test_create_links_basic(with_request_ctx):
    links = create_links(
        first={"page": 1},
        last={"page": 5},
        next={"page": 2},
        prev=None,
    )
    assert isinstance(links, Links)
    assert links.self is not None
    assert "page=1" in links.first
    assert "page=5" in links.last
    assert "page=2" in links.next
    assert links.prev is None


def test_create_links_no_next_no_prev(with_request_ctx):
    links = create_links(
        first={"page": 1},
        last={"page": 1},
        next=None,
        prev=None,
    )
    assert links.next is None
    assert links.prev is None
    assert links.first is not None
    assert links.last is not None


def test_create_links_with_only_path_false(with_request_ctx):
    req, _ = with_request_ctx
    links = create_links(
        first={"page": 1},
        last={"page": 3},
        next={"page": 2},
        prev=None,
        only_path=False,
    )
    assert links.self.startswith("http://")
    assert links.first.startswith("http://")


# --- BaseUseLinks.customize_page_ns (pydantic v2 path) ---


@dataclass
class ConcreteUseLinks(BaseUseLinks):
    def resolve_links(self, _page, /) -> Links:
        return Links(first="/first", last="/last", self="/self", next=None, prev=None)


def test_use_links_customize_page_ns_pydantic_v2():
    if not IS_PYDANTIC_V2:
        pytest.skip("pydantic v2 only")
    ns = {}
    customizer = ConcreteUseLinks()
    customizer.customize_page_ns(None, ns)
    assert "links" in ns


def test_use_links_customize_page_ns_custom_field():
    if not IS_PYDANTIC_V2:
        pytest.skip("pydantic v2 only")
    ns = {}
    customizer = ConcreteUseLinks(field="my_links")
    customizer.customize_page_ns(None, ns)
    assert "my_links" in ns


@pytest.mark.skip(reason="pydantic v1 path not exercised when IS_PYDANTIC_V2=True")
def test_use_links_customize_page_ns_pydantic_v1():
    pass


def test_use_links_customize_page_ns_pydantic_v1_adds_validator(mocker):
    mocker.patch("fastapi_pagination.links.bases.IS_PYDANTIC_V2", False)
    mocker.patch("fastapi_pagination.links.bases.root_validator", return_value=lambda f: f)
    mocker.patch("fastapi_pagination.links.bases.UseAdditionalFields")

    ns = {}
    customizer = ConcreteUseLinks()
    customizer.customize_page_ns(None, ns)

    assert "__links_root_validator__" in ns
    assert callable(ns["__links_root_validator__"])


def test_use_links_customize_page_ns_pydantic_v1_validator_updates_values(mocker):
    mocker.patch("fastapi_pagination.links.bases.IS_PYDANTIC_V2", False)
    mocker.patch("fastapi_pagination.links.bases.root_validator", return_value=lambda f: f)
    mocker.patch("fastapi_pagination.links.bases.UseAdditionalFields")

    ns = {}
    customizer = ConcreteUseLinks()
    customizer.customize_page_ns(None, ns)

    validator_fn = ns["__links_root_validator__"]
    values = {}
    result = validator_fn(None, values)
    assert result is values
    assert result["links"] == Links(first="/first", last="/last", self="/self", next=None, prev=None)


def test_use_links_customize_page_ns_pydantic_v1_uses_add_field(mocker):
    mocker.patch("fastapi_pagination.links.bases.IS_PYDANTIC_V2", False)
    mocker.patch("fastapi_pagination.links.bases.root_validator", return_value=lambda f: f)
    mock_cls = mocker.patch("fastapi_pagination.links.bases.UseAdditionalFields")

    ns = {}
    customizer = ConcreteUseLinks(field="custom_links")
    customizer.customize_page_ns(None, ns)

    mock_cls.assert_called_once()
    mock_cls.return_value.customize_page_ns.assert_called_once_with(None, ns)


# --- BaseUseHeaderLinks._add_links_to_header ---


@dataclass
class ConcreteUseHeaderLinks(BaseUseHeaderLinks):
    def resolve_links(self, _page, /) -> Links:
        return Links(first="/first", last="/last", self="/self", next="/next", prev="/prev")


def test_add_links_to_header_all_links(rsp):
    token = _rsp_val.set(rsp)
    try:
        customizer = ConcreteUseHeaderLinks()
        links = Links(first="/first", last="/last", self="/self", next="/next", prev="/prev")
        customizer._add_links_to_header(links)
        link_header = rsp.headers.get("Link", "")
        assert 'rel="first"' in link_header
        assert 'rel="last"' in link_header
        assert 'rel="next"' in link_header
        assert 'rel="prev"' in link_header
    finally:
        _rsp_val.reset(token)


def test_add_links_to_header_partial_links(rsp):
    token = _rsp_val.set(rsp)
    try:
        customizer = ConcreteUseHeaderLinks()
        links = Links(first="/first", last="/last", self=None, next=None, prev=None)
        customizer._add_links_to_header(links)
        link_header = rsp.headers.get("Link", "")
        assert 'rel="first"' in link_header
        assert 'rel="last"' in link_header
        assert "next" not in link_header
        assert "prev" not in link_header
    finally:
        _rsp_val.reset(token)


def test_add_links_to_header_no_links(rsp):
    token = _rsp_val.set(rsp)
    try:
        customizer = ConcreteUseHeaderLinks()
        links = Links(first=None, last=None, self=None, next=None, prev=None)
        customizer._add_links_to_header(links)
        assert "Link" not in rsp.headers
    finally:
        _rsp_val.reset(token)


# --- BaseUseHeaderLinks._customize_page_ns_pydantic_v2 ---


def test_customize_page_ns_pydantic_v2_adds_model_post_init():
    if not IS_PYDANTIC_V2:
        pytest.skip("pydantic v2 only")
    ns = {}
    customizer = ConcreteUseHeaderLinks()
    customizer._customize_page_ns_pydantic_v2(None, ns)
    assert "model_post_init" in ns
    assert callable(ns["model_post_init"])


# --- BaseUseHeaderLinks.customize_page_ns ---


def test_use_header_links_customize_page_ns_pydantic_v2(mocker):
    if not IS_PYDANTIC_V2:
        pytest.skip("pydantic v2 only")
    customizer = ConcreteUseHeaderLinks()
    mock_v2 = mocker.patch.object(customizer, "_customize_page_ns_pydantic_v2")
    ns = {}
    customizer.customize_page_ns(None, ns)
    mock_v2.assert_called_once_with(None, ns)


def test_use_header_links_customize_page_ns_pydantic_v1(mocker):
    if IS_PYDANTIC_V2:
        pytest.skip("pydantic v1 only")
    customizer = ConcreteUseHeaderLinks()
    mock_v1 = mocker.patch.object(customizer, "_customize_page_ns_pydantic_v1")
    ns = {}
    customizer.customize_page_ns(None, ns)
    mock_v1.assert_called_once_with(None, ns)


def test_customize_page_ns_pydantic_v1_adds_validator(mocker):
    mocker.patch("fastapi_pagination.links.bases.root_validator", return_value=lambda f: f)
    customizer = ConcreteUseHeaderLinks()
    ns = {}
    customizer._customize_page_ns_pydantic_v1(None, ns)
    assert "__add_links_to_header__" in ns
    assert callable(ns["__add_links_to_header__"])


def test_add_links_to_header_pydantic_v1_validator(rsp, mocker):
    mocker.patch("fastapi_pagination.links.bases.root_validator", return_value=lambda f: f)
    token = _rsp_val.set(rsp)
    try:
        customizer = ConcreteUseHeaderLinks()
        ns = {}
        customizer._customize_page_ns_pydantic_v1(None, ns)
        validator_fn = ns["__add_links_to_header__"]
        values = {}
        result = validator_fn(None, values)
        assert result is values
        assert "Link" in rsp.headers
    finally:
        _rsp_val.reset(token)
