"""
Tests for fastapi_pagination.links.default
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from fastapi_pagination.links.bases import Links
from fastapi_pagination.links.default import DefaultLinksCustomizer, UseLinks, resolve_default_links


def make_page(page=1, size=10, total=100):
    return SimpleNamespace(page=page, size=size, total=total)


def make_mock_request(url="http://test.example.com/api/users?page=1&size=10"):
    from starlette.datastructures import URL

    mock_req = MagicMock()
    mock_req.url = URL(url)
    return mock_req


@pytest.fixture
def mock_request():
    mock_req = make_mock_request()
    with patch("fastapi_pagination.links.bases.request", return_value=mock_req):
        yield mock_req


class TestResolveDefaultLinks:
    def test_middle_page_has_next_and_prev(self, mock_request):
        page = make_page(page=2, size=10, total=100)
        links = resolve_default_links(page)

        assert isinstance(links, Links)
        assert links.first is not None
        assert links.last is not None
        assert links.next is not None
        assert links.prev is not None

    def test_first_page_has_no_prev(self, mock_request):
        page = make_page(page=1, size=10, total=100)
        links = resolve_default_links(page)

        assert links.prev is None
        assert links.next is not None

    def test_last_page_has_no_next(self, mock_request):
        page = make_page(page=10, size=10, total=100)
        links = resolve_default_links(page)

        assert links.next is None
        assert links.prev is not None

    def test_only_path_none_default(self, mock_request):
        page = make_page(page=1, size=10, total=50)
        links = resolve_default_links(page, only_path=None)

        assert links.first is not None
        assert links.last is not None

    def test_only_path_true(self, mock_request):
        page = make_page(page=1, size=10, total=50)
        links = resolve_default_links(page, only_path=True)

        assert links.first is not None

    def test_only_path_false(self, mock_request):
        page = make_page(page=1, size=10, total=50)
        links = resolve_default_links(page, only_path=False)

        assert links.first is not None

    def test_zero_total_uses_last_page_1(self, mock_request):
        page = make_page(page=1, size=10, total=0)
        links = resolve_default_links(page)

        assert links.last is not None
        assert "page=1" in links.last

    def test_single_page_no_next_no_prev(self, mock_request):
        page = make_page(page=1, size=10, total=5)
        links = resolve_default_links(page)

        assert links.prev is None
        assert links.next is None

    def test_returns_links_instance(self, mock_request):
        page = make_page(page=1, size=10, total=100)
        result = resolve_default_links(page)

        assert isinstance(result, Links)


class TestDefaultLinksCustomizer:
    def test_resolve_links_returns_links_instance(self, mock_request):
        page = make_page(page=1, size=10, total=50)
        customizer = UseLinks()

        links = customizer.resolve_links(page)

        assert isinstance(links, Links)

    def test_resolve_links_uses_only_path_attribute(self, mock_request):
        page = make_page(page=2, size=10, total=50)
        customizer = UseLinks(only_path=True)

        links = customizer.resolve_links(page)

        assert links.first is not None
        assert links.prev is not None
        assert links.next is not None

    def test_resolve_links_delegates_to_resolve_default_links(self, mock_request):
        page = make_page(page=1, size=5, total=20)

        with patch("fastapi_pagination.links.default.resolve_default_links") as mock_resolve:
            mock_resolve.return_value = Links()
            customizer = UseLinks(only_path=False)
            customizer.resolve_links(page)

            mock_resolve.assert_called_once_with(page, only_path=False)

    def test_resolve_links_with_only_path_false(self, mock_request):
        page = make_page(page=1, size=10, total=30)
        customizer = UseLinks(only_path=False)

        links = customizer.resolve_links(page)

        assert isinstance(links, Links)
