from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi import Response
from starlette.requests import Request

from fastapi_pagination.api import _req_val, _rsp_val
from fastapi_pagination.links.default import UseLinks, resolve_default_links


def _make_request(path: str = "/items", query: str = "page=1&size=10") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": query.encode(),
        "headers": [],
    }
    return Request(scope)


@contextmanager
def _pagination_ctx(path: str = "/items", query: str = "page=1&size=10"):
    req = _make_request(path, query)
    rsp = Response()
    tok_req = _req_val.set(req)
    tok_rsp = _rsp_val.set(rsp)
    try:
        yield rsp
    finally:
        _req_val.reset(tok_req)
        _rsp_val.reset(tok_rsp)


def test_resolve_default_links_basic():
    with _pagination_ctx():
        page = SimpleNamespace(page=1, size=10, total=100)
        links = resolve_default_links(page)

    assert links.first is not None
    assert links.last is not None
    assert links.self is not None
    assert links.next is not None
    assert links.prev is None


def test_resolve_default_links_last_page():
    with _pagination_ctx():
        page = SimpleNamespace(page=10, size=10, total=100)
        links = resolve_default_links(page)

    assert links.next is None
    assert links.prev is not None


def test_resolve_default_links_first_and_only_page():
    with _pagination_ctx():
        page = SimpleNamespace(page=1, size=10, total=5)
        links = resolve_default_links(page)

    assert links.next is None
    assert links.prev is None


def test_resolve_default_links_middle_page():
    with _pagination_ctx():
        page = SimpleNamespace(page=3, size=10, total=100)
        links = resolve_default_links(page)

    assert links.next is not None
    assert links.prev is not None


def test_resolve_default_links_total_zero():
    with _pagination_ctx():
        page = SimpleNamespace(page=1, size=10, total=0)
        links = resolve_default_links(page)

    assert links.first is not None
    assert links.last is not None
    assert links.next is None


def test_resolve_default_links_only_path_false():
    with _pagination_ctx(path="/items", query="page=1&size=10"):
        page = SimpleNamespace(page=1, size=10, total=30)
        links = resolve_default_links(page, only_path=False)

    assert links.self is not None
    assert "http" not in links.self or links.self.startswith("http")


def test_resolve_default_links_page_param_in_links():
    with _pagination_ctx():
        page = SimpleNamespace(page=2, size=5, total=20)
        links = resolve_default_links(page)

    assert "page=3" in links.next
    assert "page=1" in links.prev
    assert "page=1" in links.first
    assert "page=4" in links.last


def test_use_links_resolve_links():
    customizer = UseLinks()
    with _pagination_ctx():
        page = SimpleNamespace(page=1, size=10, total=50)
        links = customizer.resolve_links(page)

    assert links.first is not None
    assert links.last is not None
    assert links.next is not None
    assert links.prev is None


def test_use_links_resolve_links_uses_only_path():
    customizer = UseLinks(only_path=True)
    with _pagination_ctx(path="/api/users", query="page=2&size=5"):
        page = SimpleNamespace(page=2, size=5, total=15)
        links = customizer.resolve_links(page)

    assert links.first is not None
    assert links.self.startswith("/api/users")
