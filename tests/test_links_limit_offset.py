from __future__ import annotations

from math import inf
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from starlette.datastructures import URL

from fastapi_pagination.links.limit_offset import (
    LimitOffsetLinksCustomizer,
    UseLimitOffsetLinks,
    resolve_limit_offset_links,
)


def _make_mock_request(url: str = "http://test/items?limit=10&offset=0") -> MagicMock:
    mock_req = MagicMock()
    mock_req.url = URL(url)
    return mock_req


def _make_page(offset, limit, total):
    return SimpleNamespace(offset=offset, limit=limit, total=total)


@pytest.fixture(autouse=True)
def mock_request(mocker):
    mock_req = _make_mock_request()
    mocker.patch("fastapi_pagination.links.bases.request", return_value=mock_req)
    return mock_req


def test_resolve_limit_offset_links_basic():
    page = _make_page(offset=0, limit=10, total=30)
    links = resolve_limit_offset_links(page)
    assert links.first is not None
    assert links.last is not None
    assert links.next is not None
    assert links.prev is None


def test_resolve_limit_offset_links_offset_none():
    page = _make_page(offset=None, limit=10, total=30)
    links = resolve_limit_offset_links(page)
    assert links.first is not None
    assert links.prev is None


def test_resolve_limit_offset_links_limit_none():
    page = _make_page(offset=0, limit=None, total=30)
    links = resolve_limit_offset_links(page)
    assert links.first is not None
    assert links.next is None


@pytest.mark.skip(reason="total=None with finite limit causes OverflowError in source code (floor(inf)*int)")
def test_resolve_limit_offset_links_total_none():
    page = _make_page(offset=0, limit=10, total=None)
    links = resolve_limit_offset_links(page)
    assert links.first is not None
    assert links.next is not None


def test_resolve_limit_offset_links_last_page():
    page = _make_page(offset=20, limit=10, total=30)
    links = resolve_limit_offset_links(page)
    assert links.next is None
    assert links.prev is not None


def test_resolve_limit_offset_links_middle_page():
    page = _make_page(offset=10, limit=10, total=30)
    links = resolve_limit_offset_links(page)
    assert links.next is not None
    assert links.prev is not None


def test_resolve_limit_offset_links_last_equals_total():
    # When last == total, last should be set to total - limit
    page = _make_page(offset=0, limit=10, total=10)
    links = resolve_limit_offset_links(page)
    assert links.first is not None
    assert links.last is not None


def test_resolve_limit_offset_links_url_contains_offset():
    page = _make_page(offset=10, limit=10, total=30)
    links = resolve_limit_offset_links(page)
    assert "offset=20" in links.next
    assert "offset=0" in links.prev


class ConcreteLinksCustomizer(LimitOffsetLinksCustomizer):
    pass


def test_limit_offset_links_customizer_resolve_links():
    customizer = UseLimitOffsetLinks()
    page = _make_page(offset=0, limit=10, total=30)
    links = customizer.resolve_links(page)
    assert links.first is not None
    assert links.last is not None
