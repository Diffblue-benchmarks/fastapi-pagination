from __future__ import annotations

from math import ceil
from types import SimpleNamespace

import pytest
from starlette.requests import Request

import fastapi_pagination.api as _api
from fastapi_pagination.links.bases import Links
from fastapi_pagination.links.default import UseLinks, resolve_default_links


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(path: str = "/items", query: str = "page=1&size=10") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": query.encode(),
        "headers": [],
        "server": ("testserver", 80),
        "scheme": "http",
        "root_path": "",
    }
    return Request(scope)


@pytest.fixture
def fake_request():
    req = _make_request()
    token = _api._req_val.set(req)
    yield req
    _api._req_val.reset(token)


# ---------------------------------------------------------------------------
# resolve_default_links
# ---------------------------------------------------------------------------


def test_resolve_default_links_returns_links_instance(fake_request):
    page = SimpleNamespace(page=1, size=10, total=50)
    links = resolve_default_links(page)
    assert isinstance(links, Links)


def test_resolve_default_links_first_is_page_1(fake_request):
    page = SimpleNamespace(page=1, size=10, total=50)
    links = resolve_default_links(page)
    assert links.first is not None
    assert "page=1" in links.first


def test_resolve_default_links_last_matches_total_pages(fake_request):
    page = SimpleNamespace(page=1, size=10, total=50)
    links = resolve_default_links(page)
    expected_last = ceil(50 / 10)
    assert links.last is not None
    assert f"page={expected_last}" in links.last


def test_resolve_default_links_next_on_non_last_page(fake_request):
    page = SimpleNamespace(page=1, size=10, total=50)
    links = resolve_default_links(page)
    assert links.next is not None
    assert "page=2" in links.next


def test_resolve_default_links_no_next_on_last_page(fake_request):
    page = SimpleNamespace(page=5, size=10, total=50)
    links = resolve_default_links(page)
    assert links.next is None


def test_resolve_default_links_no_prev_on_first_page(fake_request):
    page = SimpleNamespace(page=1, size=10, total=50)
    links = resolve_default_links(page)
    assert links.prev is None


def test_resolve_default_links_prev_on_second_page(fake_request):
    page = SimpleNamespace(page=2, size=10, total=50)
    links = resolve_default_links(page)
    assert links.prev is not None
    assert "page=1" in links.prev


def test_resolve_default_links_zero_total_last_defaults_to_page_1(fake_request):
    page = SimpleNamespace(page=1, size=10, total=0)
    links = resolve_default_links(page)
    assert links.last is not None
    assert "page=1" in links.last
    assert links.next is None


def test_resolve_default_links_only_path_true_returns_path_only(fake_request):
    page = SimpleNamespace(page=1, size=10, total=50)
    links = resolve_default_links(page, only_path=True)
    assert links.first is not None
    assert links.first.startswith("/")


def test_resolve_default_links_only_path_false_returns_full_url(fake_request):
    page = SimpleNamespace(page=1, size=10, total=50)
    links = resolve_default_links(page, only_path=False)
    assert links.first is not None
    assert links.first.startswith("http://")


# ---------------------------------------------------------------------------
# DefaultLinksCustomizer.resolve_links  (via UseLinks)
# ---------------------------------------------------------------------------


def test_default_links_customizer_resolve_links_returns_links(fake_request):
    customizer = UseLinks()
    page = SimpleNamespace(page=1, size=10, total=50)
    links = customizer.resolve_links(page)
    assert isinstance(links, Links)


def test_default_links_customizer_resolve_links_delegates_only_path(fake_request):
    customizer = UseLinks(only_path=True)
    page = SimpleNamespace(page=2, size=10, total=50)
    links = customizer.resolve_links(page)
    assert links.prev is not None
    assert links.prev.startswith("/")
    assert "page=1" in links.prev
