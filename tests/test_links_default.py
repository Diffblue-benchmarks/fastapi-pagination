from __future__ import annotations

from typing import List

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_pagination import add_pagination
from fastapi_pagination.links.default import DefaultLinksCustomizer, Page, UseLinks, resolve_default_links
from fastapi_pagination.default import Page as BasePage, Params
from fastapi_pagination.api import _req_val, _rsp_val
from fastapi import Request, Response


def _make_app_with_data(items: list, total: int, page: int = 1, size: int = 10):
    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    def list_items(params: Params = pytest.importorskip("fastapi").Depends(Params)):
        return Page.create(items, params, total=total)

    add_pagination(app)
    return app


def _make_simple_app():
    app = FastAPI()
    items = list(range(1, 101))

    @app.get("/items", response_model=Page[int])
    def list_items(params: Params = pytest.importorskip("fastapi").Depends(Params)):
        return Page.create(items, params, total=100)

    add_pagination(app)
    return app


def _call_resolve_default_links(page: int, size: int, total: int):
    """Helper to invoke resolve_default_links within a real request context."""
    app = FastAPI()
    items = list(range(1, total + 1))
    captured = {}

    @app.get("/items", response_model=Page[int])
    def list_items(params: Params = pytest.importorskip("fastapi").Depends(Params)):
        pg = BasePage.create(items[: params.size], params, total=total)
        captured["links"] = resolve_default_links(pg)
        return Page.create(items[: params.size], params, total=total)

    add_pagination(app)

    client = TestClient(app)
    client.get(f"/items?page={page}&size={size}")
    return captured.get("links")


class TestResolveDefaultLinks:
    def test_first_page_links(self):
        links = _call_resolve_default_links(page=1, size=10, total=100)
        assert links is not None
        assert "page=1" in links.first
        assert links.prev is None
        assert links.next is not None
        assert "page=2" in links.next

    def test_last_page_links(self):
        links = _call_resolve_default_links(page=10, size=10, total=100)
        assert links is not None
        assert "page=10" in links.last
        assert links.next is None
        assert links.prev is not None
        assert "page=9" in links.prev

    def test_middle_page_has_both_next_and_prev(self):
        links = _call_resolve_default_links(page=5, size=10, total=100)
        assert links is not None
        assert links.next is not None
        assert links.prev is not None
        assert "page=6" in links.next
        assert "page=4" in links.prev

    def test_single_page_no_next_no_prev(self):
        links = _call_resolve_default_links(page=1, size=10, total=5)
        assert links is not None
        assert links.next is None
        assert links.prev is None

    def test_last_page_computed_correctly(self):
        links = _call_resolve_default_links(page=1, size=10, total=25)
        assert links is not None
        assert "page=3" in links.last


class TestDefaultLinksCustomizerResolveLinks:
    def test_resolve_links_delegates_to_resolve_default_links(self):
        """UseLinks subclass of DefaultLinksCustomizer resolves links correctly."""
        app = FastAPI()
        items = list(range(1, 101))
        captured = {}

        @app.get("/items", response_model=Page[int])
        def list_items(params: Params = pytest.importorskip("fastapi").Depends(Params)):
            pg = BasePage.create(items[: params.size], params, total=100)
            customizer = UseLinks()
            captured["links"] = customizer.resolve_links(pg)
            return Page.create(items[: params.size], params, total=100)

        add_pagination(app)
        client = TestClient(app)
        client.get("/items?page=2&size=10")

        links = captured.get("links")
        assert links is not None
        assert "page=1" in links.first
        assert "page=3" in links.next
        assert "page=1" in links.prev

    def test_resolve_links_only_path_default(self):
        """UseLinks uses only_path=True by default, so links are relative paths."""
        app = FastAPI()
        items = list(range(1, 21))
        captured = {}

        @app.get("/items", response_model=Page[int])
        def list_items(params: Params = pytest.importorskip("fastapi").Depends(Params)):
            pg = BasePage.create(items[: params.size], params, total=20)
            customizer = UseLinks()
            captured["links"] = customizer.resolve_links(pg)
            return Page.create(items[: params.size], params, total=20)

        add_pagination(app)
        client = TestClient(app)
        client.get("/items?page=1&size=10")

        links = captured.get("links")
        assert links is not None
        # With only_path=True (default), links should not start with 'http'
        assert links.first is not None
        assert not links.first.startswith("http")
