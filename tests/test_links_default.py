from __future__ import annotations

from types import SimpleNamespace

import pytest
from starlette.requests import Request

from fastapi_pagination.api import _req_val
from fastapi_pagination.links.default import UseLinks, resolve_default_links


def _make_request(path="/items", query_string=b"page=1&size=10"):
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": query_string,
        "headers": [],
    }
    return Request(scope)


def _make_page(page, size, total):
    return SimpleNamespace(page=page, size=size, total=total)


@pytest.fixture
def req_ctx():
    req = _make_request()
    token = _req_val.set(req)
    yield req
    _req_val.reset(token)


def test_resolve_default_links_first_page_has_next_no_prev(req_ctx):
    page = _make_page(page=1, size=10, total=100)
    links = resolve_default_links(page)
    assert links.first is not None
    assert links.last is not None
    assert links.next is not None
    assert links.prev is None


def test_resolve_default_links_last_page_no_next_has_prev(req_ctx):
    page = _make_page(page=10, size=10, total=100)
    links = resolve_default_links(page)
    assert links.next is None
    assert links.prev is not None


def test_resolve_default_links_middle_page_has_next_and_prev(req_ctx):
    page = _make_page(page=3, size=10, total=100)
    links = resolve_default_links(page)
    assert links.next is not None
    assert links.prev is not None


def test_resolve_default_links_only_path_true(req_ctx):
    page = _make_page(page=1, size=10, total=50)
    links = resolve_default_links(page, only_path=True)
    assert links.first is not None
    assert links.first.startswith("/")


def test_resolve_default_links_empty_total(req_ctx):
    page = _make_page(page=1, size=10, total=0)
    links = resolve_default_links(page)
    assert links.next is None
    assert links.last is not None


def test_default_links_customizer_resolve_links(req_ctx):
    page = _make_page(page=2, size=5, total=30)
    customizer = UseLinks()
    links = customizer.resolve_links(page)
    assert links.first is not None
    assert links.last is not None
    assert links.next is not None
    assert links.prev is not None


def test_default_links_customizer_resolve_links_only_path(req_ctx):
    page = _make_page(page=1, size=10, total=20)
    customizer = UseLinks(only_path=True)
    links = customizer.resolve_links(page)
    assert links.first is not None
    assert links.first.startswith("/")
