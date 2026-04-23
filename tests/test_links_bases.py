from __future__ import annotations

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from starlette.datastructures import URL

import fastapi_pagination.api as api_module
from fastapi_pagination.links.bases import (
    BaseUseHeaderLinks,
    BaseUseLinks,
    Links,
    _resolve_path,
    _update_path,
    create_links,
)
from fastapi_pagination.pydantic import IS_PYDANTIC_V2


# ---------------------------------------------------------------------------
# Concrete test subclasses (abstract methods implemented)
# ---------------------------------------------------------------------------


class _ConcreteUseLinks(BaseUseLinks):
    def resolve_links(self, _page, /):
        return Links(first="/first", last="/last")


class _ConcreteUseHeaderLinks(BaseUseHeaderLinks):
    def resolve_links(self, _page, /):
        return Links(first="/first", last="/last", next="/next", prev="/prev")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def req_ctx():
    mock_request = MagicMock()
    mock_request.url = URL("http://example.com/api/users?page=1")
    token = api_module._req_val.set(mock_request)
    yield mock_request
    api_module._req_val.reset(token)


@pytest.fixture
def rsp_ctx():
    mock_headers = {}
    mock_response = MagicMock()
    mock_response.headers = mock_headers
    token = api_module._rsp_val.set(mock_response)
    yield mock_response
    api_module._rsp_val.reset(token)


# ---------------------------------------------------------------------------
# Tests for _resolve_path
# ---------------------------------------------------------------------------


class TestResolvePath:
    def test_only_path_none_defaults_true_with_query(self):
        url = URL("http://example.com/api/users?page=1&size=10")
        result = _resolve_path(url)
        assert result == "/api/users?page=1&size=10"

    def test_only_path_none_defaults_true_without_query(self):
        url = URL("http://example.com/api/users")
        result = _resolve_path(url)
        assert result == "/api/users"

    def test_only_path_false_returns_full_url(self):
        url = URL("http://example.com/api/users?page=1")
        result = _resolve_path(url, only_path=False)
        assert result == "http://example.com/api/users?page=1"

    def test_only_path_true_with_query(self):
        url = URL("http://example.com/api/users?page=1")
        result = _resolve_path(url, only_path=True)
        assert result == "/api/users?page=1"

    def test_only_path_true_without_query(self):
        url = URL("http://example.com/api/users")
        result = _resolve_path(url, only_path=True)
        assert result == "/api/users"


# ---------------------------------------------------------------------------
# Tests for _update_path
# ---------------------------------------------------------------------------


class TestUpdatePath:
    def test_returns_none_when_to_update_is_none(self):
        url = URL("http://example.com/api/users?page=1")
        result = _update_path(url, None)
        assert result is None

    def test_updates_query_params_default_only_path(self):
        url = URL("http://example.com/api/users?page=1")
        result = _update_path(url, {"page": 2})
        assert result == "/api/users?page=2"

    def test_updates_query_params_only_path_false(self):
        url = URL("http://example.com/api/users?page=1")
        result = _update_path(url, {"page": 3}, only_path=False)
        assert result is not None
        assert "example.com" in result
        assert "page=3" in result


# ---------------------------------------------------------------------------
# Tests for create_links
# ---------------------------------------------------------------------------


class TestCreateLinks:
    def test_create_links_with_next(self, req_ctx):
        links = create_links(
            first={"page": 1},
            last={"page": 5},
            next={"page": 2},
            prev=None,
        )
        assert links.first is not None
        assert links.last is not None
        assert links.next is not None
        assert links.prev is None
        assert links.self is not None  # type: ignore[attr-defined]

    def test_create_links_no_next_no_prev(self, req_ctx):
        links = create_links(
            first={"page": 1},
            last={"page": 1},
            next=None,
            prev=None,
        )
        assert links.next is None
        assert links.prev is None
        assert links.first is not None

    def test_create_links_only_path_false(self, req_ctx):
        links = create_links(
            first={"page": 1},
            last={"page": 5},
            next=None,
            prev=None,
            only_path=False,
        )
        assert links.first is not None
        assert "http" in links.first
        assert links.self is not None  # type: ignore[attr-defined]
        assert "http" in links.self  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Tests for BaseUseLinks.customize_page_ns
# ---------------------------------------------------------------------------


class TestBaseUseLinksCustomizePageNs:
    def test_adds_field_to_namespace(self):
        customizer = _ConcreteUseLinks()
        ns: dict = {}
        page_cls = MagicMock()
        customizer.customize_page_ns(page_cls, ns)
        assert "links" in ns

    def test_custom_field_name(self):
        customizer = _ConcreteUseLinks(field="pagination_links")
        ns: dict = {}
        page_cls = MagicMock()
        customizer.customize_page_ns(page_cls, ns)
        assert "pagination_links" in ns

    @pytest.mark.skipif(IS_PYDANTIC_V2, reason="pydantic v1 code path")
    def test_v1_adds_root_validator_to_namespace(self):
        customizer = _ConcreteUseLinks()
        ns: dict = {}
        page_cls = MagicMock()
        customizer.customize_page_ns(page_cls, ns)
        assert "__links_root_validator__" in ns

    @pytest.mark.skipif(IS_PYDANTIC_V2, reason="pydantic v1 code path")
    def test_v1_root_validator_resolves_links(self):
        customizer = _ConcreteUseLinks()
        ns: dict = {}
        page_cls = MagicMock()
        customizer.customize_page_ns(page_cls, ns)

        validator = ns["__links_root_validator__"]
        raw_func = getattr(validator, "func", validator)
        values: dict = {}
        result = raw_func(MagicMock, values)
        assert result is not None
        assert "links" in result


# ---------------------------------------------------------------------------
# Tests for BaseUseHeaderLinks._add_links_to_header
# ---------------------------------------------------------------------------


class TestAddLinksToHeader:
    def test_sets_link_header_when_links_present(self, rsp_ctx):
        customizer = _ConcreteUseHeaderLinks()
        links = Links(first="/first", last="/last", next="/next", prev="/prev")
        customizer._add_links_to_header(links)
        assert "Link" in rsp_ctx.headers
        link_header = rsp_ctx.headers["Link"]
        assert 'rel="first"' in link_header
        assert 'rel="last"' in link_header
        assert 'rel="next"' in link_header
        assert 'rel="prev"' in link_header

    def test_no_header_when_all_links_none(self):
        customizer = _ConcreteUseHeaderLinks()
        links = Links()
        # response() should not be called since parts will be empty
        customizer._add_links_to_header(links)

    def test_partial_links_only_non_none_in_header(self, rsp_ctx):
        customizer = _ConcreteUseHeaderLinks()
        links = Links(first="/first", next="/next")
        customizer._add_links_to_header(links)
        assert "Link" in rsp_ctx.headers
        link_header = rsp_ctx.headers["Link"]
        assert 'rel="first"' in link_header
        assert 'rel="next"' in link_header
        assert 'rel="last"' not in link_header
        assert 'rel="prev"' not in link_header


# ---------------------------------------------------------------------------
# Tests for BaseUseHeaderLinks._customize_page_ns_pydantic_v2
# ---------------------------------------------------------------------------


class TestCustomizePageNsPydanticV2:
    def test_adds_model_post_init_to_namespace(self):
        customizer = _ConcreteUseHeaderLinks()
        ns: dict = {}
        page_cls = MagicMock()
        customizer._customize_page_ns_pydantic_v2(page_cls, ns)
        assert "model_post_init" in ns
        assert callable(ns["model_post_init"])

    def test_model_post_init_calls_resolve_and_adds_header(self, rsp_ctx):
        customizer = _ConcreteUseHeaderLinks()
        ns: dict = {}
        page_cls = MagicMock()
        customizer._customize_page_ns_pydantic_v2(page_cls, ns)

        model_post_init = ns["model_post_init"]
        page_instance = MagicMock()
        model_post_init(page_instance, None)

        assert "Link" in rsp_ctx.headers
        link_header = rsp_ctx.headers["Link"]
        assert 'rel="first"' in link_header
        assert 'rel="next"' in link_header


# ---------------------------------------------------------------------------
# Tests for BaseUseHeaderLinks._customize_page_ns_pydantic_v1
# ---------------------------------------------------------------------------


class TestCustomizePageNsPydanticV1:
    def test_adds_validator_to_namespace(self):
        customizer = _ConcreteUseHeaderLinks()
        ns: dict = {}
        page_cls = MagicMock()
        customizer._customize_page_ns_pydantic_v1(page_cls, ns)
        assert "__add_links_to_header__" in ns

    def test_validator_function_resolves_links_and_adds_header(self, rsp_ctx):
        customizer = _ConcreteUseHeaderLinks()
        ns: dict = {}
        page_cls = MagicMock()
        customizer._customize_page_ns_pydantic_v1(page_cls, ns)

        validator = ns["__add_links_to_header__"]
        # In pydantic v2 compat, the validator is wrapped in PydanticDescriptorProxy
        # Access the underlying function via .wrapped attribute
        raw_func = getattr(validator, "wrapped", None) or getattr(validator, "func", validator)
        if not callable(raw_func):
            pytest.skip("Cannot extract raw function from pydantic validator wrapper")
        values: dict = {}
        result = raw_func(MagicMock, values)
        assert result == values
        assert "Link" in rsp_ctx.headers


# ---------------------------------------------------------------------------
# Tests for BaseUseHeaderLinks.customize_page_ns
# ---------------------------------------------------------------------------


class TestBaseUseHeaderLinksCustomizePageNs:
    def test_customize_page_ns_adds_correct_key_for_pydantic_version(self):
        customizer = _ConcreteUseHeaderLinks()
        ns: dict = {}
        page_cls = MagicMock()
        customizer.customize_page_ns(page_cls, ns)
        if IS_PYDANTIC_V2:
            assert "model_post_init" in ns
        else:
            assert "__add_links_to_header__" in ns

    def test_customize_page_ns_delegates_to_v2_method(self, mocker):
        customizer = _ConcreteUseHeaderLinks()
        spy_v2 = mocker.spy(customizer, "_customize_page_ns_pydantic_v2")
        spy_v1 = mocker.spy(customizer, "_customize_page_ns_pydantic_v1")
        ns: dict = {}
        page_cls = MagicMock()
        customizer.customize_page_ns(page_cls, ns)
        if IS_PYDANTIC_V2:
            spy_v2.assert_called_once()
            spy_v1.assert_not_called()
        else:
            spy_v1.assert_called_once()
            spy_v2.assert_not_called()
