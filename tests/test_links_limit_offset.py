"""Tests for fastapi_pagination.links.limit_offset module."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from fastapi_pagination.links.bases import Links
from fastapi_pagination.links.limit_offset import (
    UseLimitOffsetLinks,
    resolve_limit_offset_links,
)


def _make_page(offset, limit, total):
    return SimpleNamespace(offset=offset, limit=limit, total=total)


@pytest.fixture
def mock_create_links(mocker):
    return mocker.patch(
        "fastapi_pagination.links.limit_offset.create_links",
        return_value=Links(),
    )


def test_resolve_limit_offset_links_first_page(mock_create_links):
    page = _make_page(offset=0, limit=10, total=30)
    result = resolve_limit_offset_links(page)
    mock_create_links.assert_called_once_with(
        first={"offset": 0},
        last={"offset": 20},
        next={"offset": 10},
        prev=None,
    )
    assert isinstance(result, Links)


def test_resolve_limit_offset_links_middle_page(mock_create_links):
    page = _make_page(offset=10, limit=10, total=30)
    resolve_limit_offset_links(page)
    mock_create_links.assert_called_once_with(
        first={"offset": 0},
        last={"offset": 20},
        next={"offset": 20},
        prev={"offset": 0},
    )


def test_resolve_limit_offset_links_last_page_adjusts_last(mock_create_links):
    # offset=20 triggers the `if last == total` branch (lines 38-39)
    page = _make_page(offset=20, limit=10, total=30)
    resolve_limit_offset_links(page)
    mock_create_links.assert_called_once_with(
        first={"offset": 0},
        last={"offset": 20},
        next=None,
        prev={"offset": 10},
    )


def test_resolve_limit_offset_links_single_page(mock_create_links):
    # Total fits within one page: no next, no prev
    page = _make_page(offset=0, limit=10, total=5)
    resolve_limit_offset_links(page)
    call_kwargs = mock_create_links.call_args.kwargs
    assert call_kwargs["next"] is None
    assert call_kwargs["prev"] is None


def test_resolve_limit_offset_links_none_offset(mock_create_links):
    # Lines 27-28: offset is None, defaults to 0
    page = _make_page(offset=None, limit=10, total=50)
    resolve_limit_offset_links(page)
    call_kwargs = mock_create_links.call_args.kwargs
    assert call_kwargs["first"] == {"offset": 0}
    assert call_kwargs["next"] == {"offset": 10}
    assert call_kwargs["prev"] is None


def test_resolve_limit_offset_links_none_limit(mock_create_links):
    # Lines 29-30: limit is None, defaults to inf
    # With limit=inf: offset + inf is not < total, so next=None; offset - inf < 0, so prev=None
    page = _make_page(offset=0, limit=None, total=30)
    resolve_limit_offset_links(page)
    call_kwargs = mock_create_links.call_args.kwargs
    assert call_kwargs["next"] is None
    assert call_kwargs["prev"] is None


def test_resolve_limit_offset_links_none_total_raises():
    # Lines 31-32: total is None, defaults to inf
    # This causes OverflowError because floor(inf) is evaluated on line 36
    page = _make_page(offset=0, limit=10, total=None)
    with pytest.raises(OverflowError):
        resolve_limit_offset_links(page)


def test_customizer_resolve_links_delegates(mock_create_links):
    # Tests LimitOffsetLinksCustomizer.resolve_links (lines 50-51)
    customizer = UseLimitOffsetLinks()
    page = _make_page(offset=5, limit=5, total=20)
    result = customizer.resolve_links(page)
    mock_create_links.assert_called_once()
    assert isinstance(result, Links)
