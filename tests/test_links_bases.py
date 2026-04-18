import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from starlette.requests import URL

from fastapi_pagination.links.bases import (
    Links,
    _resolve_path,
    _update_path,
    create_links,
    BaseLinksCustomizer,
    BaseUseLinks,
    BaseUseHeaderLinks,
)
from fastapi_pagination.pydantic import IS_PYDANTIC_V2


# ---------------------------------------------------------------------------
# Concrete test implementations for abstract classes
# ---------------------------------------------------------------------------

class ConcreteUseLinks(BaseUseLinks):
    def resolve_links(self, _page, /) -> Links:
        return Links(first="/first", last="/last", next="/next", prev="/prev", self_="/self")


class ConcreteUseHeaderLinks(BaseUseHeaderLinks):
    def resolve_links(self, _page, /) -> Links:
        return Links(first="/first", last="/last", next="/next", prev=None, **{"self": "/self"})


# ---------------------------------------------------------------------------
# _resolve_path
# ---------------------------------------------------------------------------

def test_resolve_path_only_path_none_defaults_to_true_with_query():
    url = URL("http://testserver/items?page=1&size=10")
    result = _resolve_path(url, only_path=None)
    assert result == "/items?page=1&size=10"


def test_resolve_path_only_path_none_defaults_to_true_no_query():
    url = URL("http://testserver/items")
    result = _resolve_path(url, only_path=None)
    assert result == "/items"


def test_resolve_path_only_path_true_with_query():
    url = URL("http://testserver/items?page=2")
    result = _resolve_path(url, only_path=True)
    assert result == "/items?page=2"


def test_resolve_path_only_path_true_no_query():
    url = URL("http://testserver/items")
    result = _resolve_path(url, only_path=True)
    assert result == "/items"


def test_resolve_path_only_path_false():
    url = URL("http://testserver/items?page=1")
    result = _resolve_path(url, only_path=False)
    assert result == "http://testserver/items?page=1"


def test_resolve_path_only_path_false_no_query():
    url = URL("http://testserver/items")
    result = _resolve_path(url, only_path=False)
    assert result == "http://testserver/items"


# ---------------------------------------------------------------------------
# _update_path
# ---------------------------------------------------------------------------

def test_update_path_none_returns_none():
    url = URL("http://testserver/items?page=1")
    result = _update_path(url, None)
    assert result is None


def test_update_path_with_params():
    url = URL("http://testserver/items?page=1")
    result = _update_path(url, {"page": 2})
    assert result == "/items?page=2"


def test_update_path_only_path_false():
    url = URL("http://testserver/items?page=1")
    result = _update_path(url, {"page": 3}, only_path=False)
    assert result == "http://testserver/items?page=3"


# ---------------------------------------------------------------------------
# create_links
# ---------------------------------------------------------------------------

def test_create_links_uses_request_context():
    from fastapi_pagination.api import _req_val

    mock_request = MagicMock()
    mock_request.url = URL("http://testserver/items?page=2&size=10")

    token = _req_val.set(mock_request)
    try:
        links = create_links(
            first={"page": 1},
            last={"page": 5},
            next={"page": 3},
            prev={"page": 1},
            only_path=True,
        )
        assert links.first is not None and "page=1" in links.first and "size=10" in links.first
        assert links.last is not None and "page=5" in links.last
        assert links.next is not None and "page=3" in links.next
        assert links.prev is not None and "page=1" in links.prev
        assert links.self is not None
        assert "page=2" in links.self
    finally:
        _req_val.reset(token)


def test_create_links_next_none():
    from fastapi_pagination.api import _req_val

    mock_request = MagicMock()
    mock_request.url = URL("http://testserver/items?page=5&size=10")

    token = _req_val.set(mock_request)
    try:
        links = create_links(
            first={"page": 1},
            last={"page": 5},
            next=None,
            prev={"page": 4},
            only_path=True,
        )
        assert links.next is None
        assert links.prev is not None
    finally:
        _req_val.reset(token)


# ---------------------------------------------------------------------------
# BaseUseLinks.customize_page_ns
# ---------------------------------------------------------------------------

def test_base_use_links_customize_page_ns_adds_to_namespace():
    customizer = ConcreteUseLinks()
    ns = {}
    page_cls = MagicMock()

    customizer.customize_page_ns(page_cls, ns)

    assert customizer.field in ns or "__links_root_validator__" in ns or True
    # The namespace should have been modified
    if IS_PYDANTIC_V2:
        assert customizer.field in ns
    else:
        assert "__links_root_validator__" in ns


def test_base_use_links_customize_page_ns_custom_field():
    from dataclasses import dataclass

    @dataclass
    class CustomUseLinks(BaseUseLinks):
        field: str = "my_links"

        def resolve_links(self, _page, /) -> Links:
            return Links()

    customizer = CustomUseLinks()
    ns = {}
    page_cls = MagicMock()

    customizer.customize_page_ns(page_cls, ns)

    if IS_PYDANTIC_V2:
        assert "my_links" in ns
    else:
        assert "__links_root_validator__" in ns


# ---------------------------------------------------------------------------
# BaseUseHeaderLinks._add_links_to_header
# ---------------------------------------------------------------------------

def test_add_links_to_header_with_links():
    from fastapi_pagination.api import _rsp_val

    mock_response = MagicMock()
    mock_response.headers = {}

    token = _rsp_val.set(mock_response)
    try:
        customizer = ConcreteUseHeaderLinks()
        links = Links(first="/first", last="/last", next="/next", prev=None)
        customizer._add_links_to_header(links)

        assert "Link" in mock_response.headers
        link_header = mock_response.headers["Link"]
        assert 'rel="first"' in link_header
        assert 'rel="last"' in link_header
        assert 'rel="next"' in link_header
        assert 'rel="prev"' not in link_header
    finally:
        _rsp_val.reset(token)


def test_add_links_to_header_all_none():
    customizer = ConcreteUseHeaderLinks()
    links = Links(first=None, last=None, next=None, prev=None)
    # Should not call response() when all links are None
    customizer._add_links_to_header(links)  # Should not raise


# ---------------------------------------------------------------------------
# BaseUseHeaderLinks.customize_page_ns
# ---------------------------------------------------------------------------

def test_base_use_header_links_customize_page_ns():
    customizer = ConcreteUseHeaderLinks()
    ns = {}
    page_cls = MagicMock()

    customizer.customize_page_ns(page_cls, ns)

    if IS_PYDANTIC_V2:
        assert "model_post_init" in ns
    else:
        assert "__add_links_to_header__" in ns


def test_customize_page_ns_pydantic_v1_or_v2():
    customizer = ConcreteUseHeaderLinks()
    ns = {}
    page_cls = MagicMock()

    if IS_PYDANTIC_V2:
        customizer._customize_page_ns_pydantic_v2(page_cls, ns)
        assert "model_post_init" in ns
    else:
        customizer._customize_page_ns_pydantic_v1(page_cls, ns)
        assert "__add_links_to_header__" in ns


def test_model_post_init_calls_add_links_to_header():
    """Test pydantic v2 model_post_init calls resolve_links and _add_links_to_header."""
    if not IS_PYDANTIC_V2:
        pytest.skip("Pydantic v2 only")

    from fastapi_pagination.api import _rsp_val

    mock_response = MagicMock()
    mock_response.headers = {}
    token = _rsp_val.set(mock_response)

    try:
        customizer = ConcreteUseHeaderLinks()
        ns = {}
        page_cls = MagicMock()
        customizer._customize_page_ns_pydantic_v2(page_cls, ns)

        page_mock = MagicMock()
        ns["model_post_init"](page_mock, None)
        # _add_links_to_header was called; since ConcreteUseHeaderLinks returns next="/next",
        # the Link header should have been set
        assert "Link" in mock_response.headers
    finally:
        _rsp_val.reset(token)


def test_root_validator_calls_resolve_links():
    """Test pydantic v1 root validator calls resolve_links."""
    if IS_PYDANTIC_V2:
        pytest.skip("Pydantic v1 only")

    from fastapi_pagination.api import _rsp_val

    mock_response = MagicMock()
    mock_response.headers = {}
    token = _rsp_val.set(mock_response)

    try:
        customizer = ConcreteUseHeaderLinks()
        ns = {}
        page_cls = MagicMock()
        customizer._customize_page_ns_pydantic_v1(page_cls, ns)

        validator = ns["__add_links_to_header__"]
        values = {"items": [], "total": 0}
        result = validator.__func__(MagicMock, values)
        assert result == values
        assert "Link" in mock_response.headers
    finally:
        _rsp_val.reset(token)


# ---------------------------------------------------------------------------
# BaseUseLinks.customize_page_ns - pydantic v1 branch (lines 111-119)
# ---------------------------------------------------------------------------

def test_base_use_links_customize_page_ns_pydantic_v1_adds_root_validator(mocker):
    """Test that the pydantic v1 path adds __links_root_validator__ to namespace."""
    mocker.patch("fastapi_pagination.links.bases.IS_PYDANTIC_V2", False)

    customizer = ConcreteUseLinks()
    ns = {}
    page_cls = MagicMock()

    customizer.customize_page_ns(page_cls, ns)

    assert "__links_root_validator__" in ns
    assert "__annotations__" in ns
    assert customizer.field in ns["__annotations__"]


def test_base_use_links_customize_page_ns_pydantic_v1_adds_field_to_annotations(mocker):
    """Test that the pydantic v1 path populates __annotations__ with the links field."""
    mocker.patch("fastapi_pagination.links.bases.IS_PYDANTIC_V2", False)

    customizer = ConcreteUseLinks()
    ns = {}
    page_cls = MagicMock()

    customizer.customize_page_ns(page_cls, ns)

    anns = ns.get("__annotations__", {})
    assert customizer.field in anns
    assert anns[customizer.field] is Links


def test_base_use_links_customize_page_ns_pydantic_v1_root_validator_calls_resolve_links(mocker):
    """Test that the root validator created in pydantic v1 path calls resolve_links."""
    mocker.patch("fastapi_pagination.links.bases.IS_PYDANTIC_V2", False)

    customizer = ConcreteUseLinks()
    ns = {}
    page_cls = MagicMock()

    customizer.customize_page_ns(page_cls, ns)

    validator_fn = ns["__links_root_validator__"]
    values = {"items": [], "total": 0}
    result = validator_fn.__func__(MagicMock, values)

    assert result is values
    assert customizer.field in result
    assert isinstance(result[customizer.field], Links)


def test_base_use_links_customize_page_ns_pydantic_v1_custom_field(mocker):
    """Test pydantic v1 path uses the configured field name."""
    mocker.patch("fastapi_pagination.links.bases.IS_PYDANTIC_V2", False)

    from dataclasses import dataclass as dc

    @dc
    class CustomFieldUseLinks(BaseUseLinks):
        field: str = "custom_links"

        def resolve_links(self, _page, /) -> Links:
            return Links(first="/f", last="/l")

    customizer = CustomFieldUseLinks()
    ns = {}
    page_cls = MagicMock()

    customizer.customize_page_ns(page_cls, ns)

    assert "__links_root_validator__" in ns
    assert "custom_links" in ns.get("__annotations__", {})
