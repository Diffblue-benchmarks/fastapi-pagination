"""Unit tests for fastapi_pagination.links.default module."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from starlette.datastructures import URL


def _make_mock_request(url_str: str = "http://localhost/api/items") -> MagicMock:
    mock_req = MagicMock()
    mock_req.url = URL(url_str)
    return mock_req


def _make_page(page: int | None, size: int | None, total: int | None) -> SimpleNamespace:
    return SimpleNamespace(page=page, size=size, total=total)


class TestResolveDefaultLinks:
    def test_returns_links_with_first_and_last(self):
        from fastapi_pagination.links.default import resolve_default_links

        mock_req = _make_mock_request()
        with patch("fastapi_pagination.links.bases.request", return_value=mock_req):
            _page = _make_page(page=1, size=10, total=30)
            links = resolve_default_links(_page)

        assert links.first is not None
        assert links.last is not None

    def test_next_link_when_more_pages(self):
        from fastapi_pagination.links.default import resolve_default_links

        mock_req = _make_mock_request()
        with patch("fastapi_pagination.links.bases.request", return_value=mock_req):
            _page = _make_page(page=1, size=10, total=30)
            links = resolve_default_links(_page)

        assert links.next is not None
        assert "page=2" in links.next

    def test_no_next_link_on_last_page(self):
        from fastapi_pagination.links.default import resolve_default_links

        mock_req = _make_mock_request()
        with patch("fastapi_pagination.links.bases.request", return_value=mock_req):
            _page = _make_page(page=3, size=10, total=30)
            links = resolve_default_links(_page)

        assert links.next is None

    def test_prev_link_when_not_first_page(self):
        from fastapi_pagination.links.default import resolve_default_links

        mock_req = _make_mock_request()
        with patch("fastapi_pagination.links.bases.request", return_value=mock_req):
            _page = _make_page(page=2, size=10, total=30)
            links = resolve_default_links(_page)

        assert links.prev is not None
        assert "page=1" in links.prev

    def test_no_prev_link_on_first_page(self):
        from fastapi_pagination.links.default import resolve_default_links

        mock_req = _make_mock_request()
        with patch("fastapi_pagination.links.bases.request", return_value=mock_req):
            _page = _make_page(page=1, size=10, total=30)
            links = resolve_default_links(_page)

        assert links.prev is None

    def test_last_page_calculated_correctly(self):
        from fastapi_pagination.links.default import resolve_default_links

        mock_req = _make_mock_request()
        with patch("fastapi_pagination.links.bases.request", return_value=mock_req):
            _page = _make_page(page=1, size=10, total=25)
            links = resolve_default_links(_page)

        assert links.last is not None
        assert "page=3" in links.last

    def test_last_page_is_one_when_total_is_zero(self):
        from fastapi_pagination.links.default import resolve_default_links

        mock_req = _make_mock_request()
        with patch("fastapi_pagination.links.bases.request", return_value=mock_req):
            _page = _make_page(page=1, size=10, total=0)
            links = resolve_default_links(_page)

        assert links.last is not None
        assert "page=1" in links.last

    def test_only_path_true_returns_path_only(self):
        from fastapi_pagination.links.default import resolve_default_links

        mock_req = _make_mock_request("http://localhost/api/items")
        with patch("fastapi_pagination.links.bases.request", return_value=mock_req):
            _page = _make_page(page=1, size=10, total=30)
            links = resolve_default_links(_page, only_path=True)

        assert links.first is not None
        assert links.first.startswith("/")

    def test_only_path_false_returns_full_url(self):
        from fastapi_pagination.links.default import resolve_default_links

        mock_req = _make_mock_request("http://localhost/api/items")
        with patch("fastapi_pagination.links.bases.request", return_value=mock_req):
            _page = _make_page(page=1, size=10, total=30)
            links = resolve_default_links(_page, only_path=False)

        assert links.first is not None
        assert links.first.startswith("http://")


class TestDefaultLinksCustomizer:
    def test_resolve_links_delegates_to_resolve_default_links(self):
        from fastapi_pagination.links.default import UseLinks

        mock_req = _make_mock_request()
        with patch("fastapi_pagination.links.bases.request", return_value=mock_req):
            customizer = UseLinks()
            _page = _make_page(page=1, size=10, total=30)
            links = customizer.resolve_links(_page)

        assert links.first is not None
        assert links.last is not None

    def test_resolve_links_uses_only_path_attribute(self):
        from fastapi_pagination.links.default import UseLinks

        mock_req = _make_mock_request("http://localhost/api/items")
        with patch("fastapi_pagination.links.bases.request", return_value=mock_req):
            customizer = UseLinks(only_path=False)
            _page = _make_page(page=1, size=10, total=30)
            links = customizer.resolve_links(_page)

        assert links.first is not None
        assert links.first.startswith("http://")

    def test_resolve_links_with_only_path_true(self):
        from fastapi_pagination.links.default import UseLinks

        mock_req = _make_mock_request("http://localhost/api/items")
        with patch("fastapi_pagination.links.bases.request", return_value=mock_req):
            customizer = UseLinks(only_path=True)
            _page = _make_page(page=2, size=5, total=20)
            links = customizer.resolve_links(_page)

        assert links.next is not None
        assert links.next.startswith("/")
