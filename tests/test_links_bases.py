from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from starlette.requests import URL

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
# Concrete helpers
# ---------------------------------------------------------------------------


@dataclass
class ConcreteUseLinks(BaseUseLinks):
    def resolve_links(self, _page: Any, /) -> Links:
        return Links(first="/first", last="/last", next="/next", prev="/prev")


@dataclass
class ConcreteUseHeaderLinks(BaseUseHeaderLinks):
    def resolve_links(self, _page: Any, /) -> Links:
        return Links(first="/first", last="/last", next="/next", prev=None)


# ---------------------------------------------------------------------------
# _resolve_path
# ---------------------------------------------------------------------------


def test_resolve_path_only_path_none_defaults_to_true_no_query():
    url = URL("http://localhost/api/users")
    result = _resolve_path(url, only_path=None)
    assert result == "/api/users"


def test_resolve_path_only_path_none_defaults_to_true_with_query():
    url = URL("http://localhost/api/users?page=1&size=10")
    result = _resolve_path(url, only_path=None)
    assert result == "/api/users?page=1&size=10"


def test_resolve_path_only_path_false_returns_full_url():
    url = URL("http://localhost/api/users?page=2")
    result = _resolve_path(url, only_path=False)
    assert result == "http://localhost/api/users?page=2"


def test_resolve_path_only_path_true_with_query():
    url = URL("http://localhost/api/items?q=foo")
    result = _resolve_path(url, only_path=True)
    assert result == "/api/items?q=foo"


def test_resolve_path_only_path_true_no_query():
    url = URL("http://localhost/api/items")
    result = _resolve_path(url, only_path=True)
    assert result == "/api/items"


# ---------------------------------------------------------------------------
# _update_path
# ---------------------------------------------------------------------------


def test_update_path_returns_none_when_to_update_is_none():
    url = URL("http://localhost/api/users?page=1")
    result = _update_path(url, None)
    assert result is None


def test_update_path_updates_query_params():
    url = URL("http://localhost/api/users?page=1&size=10")
    result = _update_path(url, {"page": 2})
    assert result is not None
    assert "page=2" in result
    assert "size=10" in result


def test_update_path_with_only_path_false():
    url = URL("http://localhost/api/users?page=1")
    result = _update_path(url, {"page": 3}, only_path=False)
    assert result is not None
    assert result.startswith("http://localhost")


def test_update_path_adds_new_param():
    url = URL("http://localhost/api/users")
    result = _update_path(url, {"page": 5})
    assert result is not None
    assert "page=5" in result


# ---------------------------------------------------------------------------
# create_links
# ---------------------------------------------------------------------------


def test_create_links_with_only_path(mocker):
    mock_url = URL("http://localhost/api/users?page=1&size=10")
    mock_request = MagicMock()
    mock_request.url = mock_url
    mocker.patch("fastapi_pagination.links.bases.request", return_value=mock_request)

    links = create_links(
        first={"page": 1},
        last={"page": 5},
        next={"page": 2},
        prev=None,
        only_path=True,
    )

    assert links.self is not None
    assert "/api/users" in links.self
    assert links.first is not None
    assert links.last is not None
    assert links.next is not None
    assert links.prev is None


def test_create_links_full_url(mocker):
    mock_url = URL("http://localhost/api/users?page=1")
    mock_request = MagicMock()
    mock_request.url = mock_url
    mocker.patch("fastapi_pagination.links.bases.request", return_value=mock_request)

    links = create_links(
        first={"page": 1},
        last={"page": 3},
        next={"page": 2},
        prev=None,
        only_path=False,
    )

    assert links.self is not None
    assert links.self.startswith("http://localhost")


def test_create_links_no_next_no_prev(mocker):
    mock_url = URL("http://localhost/api/users?page=1&size=10")
    mock_request = MagicMock()
    mock_request.url = mock_url
    mocker.patch("fastapi_pagination.links.bases.request", return_value=mock_request)

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


# ---------------------------------------------------------------------------
# BaseUseHeaderLinks._add_links_to_header
# ---------------------------------------------------------------------------


def test_add_links_to_header_sets_link_header(mocker):
    mock_response = MagicMock()
    mock_response.headers = {}
    mocker.patch("fastapi_pagination.links.bases.response", return_value=mock_response)

    customizer = ConcreteUseHeaderLinks()
    links = Links(first="/first", last="/last", next="/next", prev=None)
    customizer._add_links_to_header(links)

    assert "Link" in mock_response.headers
    link_header = mock_response.headers["Link"]
    assert 'rel="first"' in link_header
    assert 'rel="last"' in link_header
    assert 'rel="next"' in link_header
    assert 'rel="prev"' not in link_header


def test_add_links_to_header_no_links_skips_header(mocker):
    mock_response = MagicMock()
    mock_response.headers = {}
    mocker.patch("fastapi_pagination.links.bases.response", return_value=mock_response)

    customizer = ConcreteUseHeaderLinks()
    links = Links(first=None, last=None, next=None, prev=None)
    customizer._add_links_to_header(links)

    assert "Link" not in mock_response.headers


def test_add_links_to_header_all_links(mocker):
    mock_response = MagicMock()
    mock_response.headers = {}
    mocker.patch("fastapi_pagination.links.bases.response", return_value=mock_response)

    customizer = ConcreteUseHeaderLinks()
    links = Links(first="/f", last="/l", next="/n", prev="/p")
    customizer._add_links_to_header(links)

    link_val = mock_response.headers["Link"]
    assert 'rel="first"' in link_val
    assert 'rel="last"' in link_val
    assert 'rel="next"' in link_val
    assert 'rel="prev"' in link_val


# ---------------------------------------------------------------------------
# BaseUseLinks.customize_page_ns
# ---------------------------------------------------------------------------


def test_use_links_customize_page_ns_adds_to_namespace():
    customizer = ConcreteUseLinks()
    ns: dict[str, Any] = {}
    page_cls = MagicMock()

    customizer.customize_page_ns(page_cls, ns)

    assert "links" in ns


@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="pydantic v2 only")
def test_use_links_customize_page_ns_pydantic_v2_computed_field():
    customizer = ConcreteUseLinks()
    ns: dict[str, Any] = {}
    page_cls = MagicMock()

    customizer.customize_page_ns(page_cls, ns)

    assert "links" in ns


@pytest.mark.skipif(IS_PYDANTIC_V2, reason="pydantic v1 only")
def test_use_links_customize_page_ns_pydantic_v1_adds_validator():
    customizer = ConcreteUseLinks()
    ns: dict[str, Any] = {}
    page_cls = MagicMock()

    customizer.customize_page_ns(page_cls, ns)

    assert "__links_root_validator__" in ns


@pytest.mark.skipif(IS_PYDANTIC_V2, reason="pydantic v1 only")
def test_use_links_root_validator_sets_links_field():
    customizer = ConcreteUseLinks()
    ns: dict[str, Any] = {}
    page_cls = MagicMock()

    customizer.customize_page_ns(page_cls, ns)

    validator = ns["__links_root_validator__"]
    values = {"items": [], "total": 0, "page": 1, "size": 10}
    result = validator.__wrapped__(None, values)
    assert "links" in result
    assert isinstance(result["links"], Links)


# ---------------------------------------------------------------------------
# BaseUseHeaderLinks.customize_page_ns
# ---------------------------------------------------------------------------


def test_use_header_links_customize_page_ns_dispatches():
    customizer = ConcreteUseHeaderLinks()
    ns: dict[str, Any] = {}
    page_cls = MagicMock()

    customizer.customize_page_ns(page_cls, ns)

    if IS_PYDANTIC_V2:
        assert "model_post_init" in ns
    else:
        assert "__add_links_to_header__" in ns


@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="pydantic v2 only")
def test_use_header_links_pydantic_v2_model_post_init(mocker):
    mock_response = MagicMock()
    mock_response.headers = {}
    mocker.patch("fastapi_pagination.links.bases.response", return_value=mock_response)

    customizer = ConcreteUseHeaderLinks()
    ns: dict[str, Any] = {}
    page_cls = MagicMock()

    customizer._customize_page_ns_pydantic_v2(page_cls, ns)

    assert "model_post_init" in ns
    post_init = ns["model_post_init"]
    page_self = SimpleNamespace(first="/f", last="/l", next="/n", prev=None)
    post_init(page_self, None)
    assert "Link" in mock_response.headers


@pytest.mark.skipif(IS_PYDANTIC_V2, reason="pydantic v1 only")
def test_use_header_links_pydantic_v1_adds_validator():
    customizer = ConcreteUseHeaderLinks()
    ns: dict[str, Any] = {}
    page_cls = MagicMock()

    customizer._customize_page_ns_pydantic_v1(page_cls, ns)

    assert "__add_links_to_header__" in ns


@pytest.mark.skipif(IS_PYDANTIC_V2, reason="pydantic v1 only")
def test_use_header_links_add_links_to_header_validator(mocker):
    mock_response = MagicMock()
    mock_response.headers = {}
    mocker.patch("fastapi_pagination.links.bases.response", return_value=mock_response)

    customizer = ConcreteUseHeaderLinks()
    ns: dict[str, Any] = {}
    page_cls = MagicMock()

    customizer._customize_page_ns_pydantic_v1(page_cls, ns)

    validator = ns["__add_links_to_header__"]
    values = {"items": [], "total": 0, "page": 1, "size": 10}
    result = validator.__wrapped__(None, values)
    assert result == values


def test_customize_page_ns_pydantic_v1_validator_body_returns_values(mocker):
    mock_response = MagicMock()
    mock_response.headers = {}
    mocker.patch("fastapi_pagination.links.bases.response", return_value=mock_response)

    customizer = ConcreteUseHeaderLinks()
    ns: dict[str, Any] = {}
    page_cls = MagicMock()

    customizer._customize_page_ns_pydantic_v1(page_cls, ns)

    assert "__add_links_to_header__" in ns
    validator = ns["__add_links_to_header__"]
    values = {"items": [], "total": 0, "page": 1, "size": 10}
    result = validator.__wrapped__(None, values)

    assert result == values
    assert "Link" in mock_response.headers
    assert 'rel="first"' in mock_response.headers["Link"]


def test_customize_page_ns_pydantic_v1_validator_calls_resolve_links(mocker):
    mock_response = MagicMock()
    mock_response.headers = {}
    mocker.patch("fastapi_pagination.links.bases.response", return_value=mock_response)

    customizer = ConcreteUseHeaderLinks()
    ns: dict[str, Any] = {}
    page_cls = MagicMock()

    customizer._customize_page_ns_pydantic_v1(page_cls, ns)

    validator = ns["__add_links_to_header__"]
    values = {"items": [1, 2, 3], "total": 3, "page": 2, "size": 10}
    result = validator.__wrapped__(None, values)

    assert result is values
    link_header = mock_response.headers["Link"]
    assert 'rel="next"' in link_header
    assert 'rel="last"' in link_header


# ---------------------------------------------------------------------------
# BaseUseLinks.customize_page_ns - pydantic v1 path (mocked IS_PYDANTIC_V2=False)
# ---------------------------------------------------------------------------


def test_use_links_customize_page_ns_mocked_v1_adds_root_validator(mocker):
    mocker.patch("fastapi_pagination.links.bases.IS_PYDANTIC_V2", False)

    customizer = ConcreteUseLinks()
    ns: dict[str, Any] = {}
    page_cls = MagicMock()

    customizer.customize_page_ns(page_cls, ns)

    assert "__links_root_validator__" in ns


def test_use_links_customize_page_ns_mocked_v1_adds_field_annotation(mocker):
    mocker.patch("fastapi_pagination.links.bases.IS_PYDANTIC_V2", False)

    customizer = ConcreteUseLinks()
    ns: dict[str, Any] = {}
    page_cls = MagicMock()

    customizer.customize_page_ns(page_cls, ns)

    assert "__annotations__" in ns
    assert "links" in ns["__annotations__"]


def test_use_links_customize_page_ns_mocked_v1_root_validator_sets_links(mocker):
    mocker.patch("fastapi_pagination.links.bases.IS_PYDANTIC_V2", False)

    customizer = ConcreteUseLinks()
    ns: dict[str, Any] = {}
    page_cls = MagicMock()

    customizer.customize_page_ns(page_cls, ns)

    validator = ns["__links_root_validator__"]
    values: dict[str, Any] = {"items": [], "total": 0, "page": 1, "size": 10}
    result = validator.__wrapped__(None, values)

    assert "links" in result
    assert isinstance(result["links"], Links)


def test_use_links_customize_page_ns_mocked_v1_root_validator_returns_values(mocker):
    mocker.patch("fastapi_pagination.links.bases.IS_PYDANTIC_V2", False)

    customizer = ConcreteUseLinks()
    ns: dict[str, Any] = {}
    page_cls = MagicMock()

    customizer.customize_page_ns(page_cls, ns)

    validator = ns["__links_root_validator__"]
    values: dict[str, Any] = {"items": [1, 2], "total": 2}
    result = validator.__wrapped__(None, values)

    assert result is values


def test_use_links_customize_page_ns_mocked_v1_custom_field_name(mocker):
    mocker.patch("fastapi_pagination.links.bases.IS_PYDANTIC_V2", False)

    @dataclass
    class CustomFieldLinks(BaseUseLinks):
        field: str = "my_links"

        def resolve_links(self, _page: Any, /) -> Links:
            return Links(first="/first", last="/last")

    customizer = CustomFieldLinks()
    ns: dict[str, Any] = {}
    page_cls = MagicMock()

    customizer.customize_page_ns(page_cls, ns)

    assert "__links_root_validator__" in ns
    assert "my_links" in ns["__annotations__"]
    validator = ns["__links_root_validator__"]
    values: dict[str, Any] = {"items": []}
    result = validator.__wrapped__(None, values)
    assert "my_links" in result
    assert isinstance(result["my_links"], Links)
