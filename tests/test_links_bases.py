import pytest
from starlette.requests import Request as StarletteRequest
from starlette.requests import URL
from starlette.responses import Response as StarletteResponse

from fastapi_pagination.api import _req_val, _rsp_val
from fastapi_pagination.default import Page
from fastapi_pagination.links.bases import (
    BaseUseHeaderLinks,
    BaseUseLinks,
    Links,
    _resolve_path,
    _update_path,
    create_links,
)
from fastapi_pagination.links.default import UseHeaderLinks, UseLinks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(path: str = "/api/v1/users", query: str = "page=1&size=10") -> StarletteRequest:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": query.encode(),
        "headers": [],
        "server": ("localhost", 80),
    }
    return StarletteRequest(scope)


# ---------------------------------------------------------------------------
# _resolve_path
# ---------------------------------------------------------------------------


def test_resolve_path_defaults_to_only_path_with_query():
    url = URL("http://localhost/api/v1/users?page=1&size=10")
    assert _resolve_path(url) == "/api/v1/users?page=1&size=10"


def test_resolve_path_only_path_none_with_query():
    url = URL("http://localhost/api/v1/users?page=1&size=10")
    assert _resolve_path(url, only_path=None) == "/api/v1/users?page=1&size=10"


def test_resolve_path_only_path_false_returns_full_url():
    url = URL("http://localhost/api/v1/users?page=1&size=10")
    result = _resolve_path(url, only_path=False)
    assert result == "http://localhost/api/v1/users?page=1&size=10"


def test_resolve_path_only_path_true_no_query():
    url = URL("http://localhost/api/v1/users")
    assert _resolve_path(url, only_path=True) == "/api/v1/users"


def test_resolve_path_only_path_none_no_query():
    url = URL("http://localhost/api/v1/users")
    assert _resolve_path(url, only_path=None) == "/api/v1/users"


# ---------------------------------------------------------------------------
# _update_path
# ---------------------------------------------------------------------------


def test_update_path_none_returns_none():
    url = URL("http://localhost/api/v1/users?page=1&size=10")
    assert _update_path(url, None) is None


def test_update_path_with_params_returns_path():
    url = URL("http://localhost/api/v1/users?page=1&size=10")
    result = _update_path(url, {"page": 2})
    assert result is not None
    assert "page=2" in result
    assert result.startswith("/api/v1/users")


def test_update_path_full_url():
    url = URL("http://localhost/api/v1/users?page=1&size=10")
    result = _update_path(url, {"page": 2}, only_path=False)
    assert result is not None
    assert result.startswith("http://localhost/api/v1/users")
    assert "page=2" in result


# ---------------------------------------------------------------------------
# create_links
# ---------------------------------------------------------------------------


def test_create_links_with_next_only():
    req = _make_request()
    token = _req_val.set(req)
    try:
        links = create_links({"page": 1}, {"page": 5}, {"page": 2}, None)
        assert links.first is not None
        assert links.last is not None
        assert links.self is not None
        assert links.next is not None
        assert links.prev is None
    finally:
        _req_val.reset(token)


def test_create_links_with_prev_and_next():
    req = _make_request()
    token = _req_val.set(req)
    try:
        links = create_links({"page": 1}, {"page": 5}, {"page": 3}, {"page": 1})
        assert links.prev is not None
        assert links.next is not None
    finally:
        _req_val.reset(token)


def test_create_links_full_url():
    req = _make_request()
    token = _req_val.set(req)
    try:
        links = create_links({"page": 1}, {"page": 5}, None, None, only_path=False)
        assert links.self is not None
        assert links.self.startswith("http://")
    finally:
        _req_val.reset(token)


# ---------------------------------------------------------------------------
# BaseUseLinks.customize_page_ns (pydantic v2 branch)
# ---------------------------------------------------------------------------


def test_base_use_links_customize_page_ns_pydantic_v2():
    ns: dict = {}
    use_links = UseLinks()
    use_links.customize_page_ns(Page, ns)
    assert "links" in ns


# ---------------------------------------------------------------------------
# BaseUseLinks.customize_page_ns (pydantic v1 branch via monkeypatch)
# ---------------------------------------------------------------------------


def test_base_use_links_customize_page_ns_pydantic_v1(monkeypatch):
    import fastapi_pagination.links.bases as bases_module

    monkeypatch.setattr(bases_module, "IS_PYDANTIC_V2", False)

    ns: dict = {}
    use_links = UseLinks()
    use_links.customize_page_ns(Page, ns)

    assert "links" in ns
    assert "__links_root_validator__" in ns


def test_base_use_links_root_validator_body(monkeypatch):
    import fastapi_pagination.links.bases as bases_module

    monkeypatch.setattr(bases_module, "IS_PYDANTIC_V2", False)

    ns: dict = {}
    use_links = UseLinks()
    use_links.customize_page_ns(Page, ns)

    validator = ns["__links_root_validator__"]
    inner_fn = validator.wrapped.__func__

    req = _make_request()
    token = _req_val.set(req)
    try:
        values = {"items": [], "total": 100, "page": 1, "size": 10, "pages": 10}
        result = inner_fn(Page, values)
        assert "links" in result
        assert isinstance(result["links"], Links)
    finally:
        _req_val.reset(token)


# ---------------------------------------------------------------------------
# BaseUseHeaderLinks._add_links_to_header
# ---------------------------------------------------------------------------


def test_add_links_to_header_sets_link_header():
    rsp = StarletteResponse()
    token = _rsp_val.set(rsp)
    try:
        links = Links(first="/path?page=1", last="/path?page=5", next="/path?page=2")
        use_header = UseHeaderLinks()
        use_header._add_links_to_header(links)
        link_header = rsp.headers.get("link")
        assert link_header is not None
        assert 'rel="first"' in link_header
        assert 'rel="last"' in link_header
        assert 'rel="next"' in link_header
    finally:
        _rsp_val.reset(token)


def test_add_links_to_header_no_links_skips_header():
    rsp = StarletteResponse()
    token = _rsp_val.set(rsp)
    try:
        links = Links()
        use_header = UseHeaderLinks()
        use_header._add_links_to_header(links)
        assert "link" not in rsp.headers
    finally:
        _rsp_val.reset(token)


def test_add_links_to_header_prev_included():
    rsp = StarletteResponse()
    token = _rsp_val.set(rsp)
    try:
        links = Links(prev="/path?page=1")
        use_header = UseHeaderLinks()
        use_header._add_links_to_header(links)
        link_header = rsp.headers.get("link")
        assert link_header is not None
        assert 'rel="prev"' in link_header
    finally:
        _rsp_val.reset(token)


# ---------------------------------------------------------------------------
# BaseUseHeaderLinks._customize_page_ns_pydantic_v1
# ---------------------------------------------------------------------------


def test_customize_page_ns_pydantic_v1_adds_validator():
    ns: dict = {}
    use_header = UseHeaderLinks()
    use_header._customize_page_ns_pydantic_v1(Page, ns)
    assert "__add_links_to_header__" in ns


def test_add_links_to_header_validator_body():
    ns: dict = {}
    use_header = UseHeaderLinks()
    use_header._customize_page_ns_pydantic_v1(Page, ns)

    validator = ns["__add_links_to_header__"]
    inner_fn = validator.wrapped.__func__

    req = _make_request()
    rsp = StarletteResponse()
    req_token = _req_val.set(req)
    rsp_token = _rsp_val.set(rsp)
    try:
        values = {"items": [], "total": 100, "page": 1, "size": 10, "pages": 10}
        result = inner_fn(Page, values)
        assert result == values
        assert rsp.headers.get("link") is not None
    finally:
        _req_val.reset(req_token)
        _rsp_val.reset(rsp_token)


# ---------------------------------------------------------------------------
# BaseUseHeaderLinks._customize_page_ns_pydantic_v2
# ---------------------------------------------------------------------------


def test_customize_page_ns_pydantic_v2_adds_model_post_init():
    ns: dict = {}
    use_header = UseHeaderLinks()
    use_header._customize_page_ns_pydantic_v2(Page, ns)
    assert "model_post_init" in ns


def test_model_post_init_body():
    from types import SimpleNamespace

    ns: dict = {}
    use_header = UseHeaderLinks()
    use_header._customize_page_ns_pydantic_v2(Page, ns)

    model_post_init = ns["model_post_init"]

    req = _make_request()
    rsp = StarletteResponse()
    req_token = _req_val.set(req)
    rsp_token = _rsp_val.set(rsp)
    try:
        page_self = SimpleNamespace(items=[], total=100, page=1, size=10, pages=10)
        model_post_init(page_self, None)
        assert rsp.headers.get("link") is not None
    finally:
        _req_val.reset(req_token)
        _rsp_val.reset(rsp_token)


# ---------------------------------------------------------------------------
# BaseUseHeaderLinks.customize_page_ns
# ---------------------------------------------------------------------------


def test_base_use_header_links_customize_page_ns_pydantic_v2():
    ns: dict = {}
    use_header = UseHeaderLinks()
    use_header.customize_page_ns(Page, ns)
    assert "model_post_init" in ns


def test_base_use_header_links_customize_page_ns_pydantic_v1(monkeypatch):
    import fastapi_pagination.links.bases as bases_module

    monkeypatch.setattr(bases_module, "IS_PYDANTIC_V2", False)

    ns: dict = {}
    use_header = UseHeaderLinks()
    use_header.customize_page_ns(Page, ns)
    assert "__add_links_to_header__" in ns
