from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest

from fastapi_pagination.bases import (
    AbstractPage,
    AbstractParams,
    BaseRawParams,
    CursorRawParams,
    RawParams,
    connect_page_and_params,
    is_cursor,
    is_limit_offset,
)
from fastapi_pagination.pydantic.consts import IS_PYDANTIC_V2


# --- Concrete helpers ---

class ConcreteParams(AbstractParams):
    def to_raw_params(self) -> BaseRawParams:
        return RawParams(limit=10, offset=0)


class ConcreteParams2(AbstractParams):
    def to_raw_params(self) -> BaseRawParams:
        return RawParams(limit=5, offset=0)


def _make_page_cls(params_cls=None):
    """Create a fresh concrete AbstractPage subclass, optionally pre-connected to params_cls."""

    class _Page(AbstractPage[Any]):
        items: list[Any] = []

        if params_cls is not None:
            __params_type__ = params_cls

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> "_Page":
            return cls(items=list(items))

    return _Page


# --- Tests for is_limit_offset ---

def test_is_limit_offset_returns_true_for_raw_params():
    params = RawParams(limit=10, offset=0)
    assert is_limit_offset(params) is True


def test_is_limit_offset_returns_false_for_cursor_params():
    params = CursorRawParams(cursor=None, size=10)
    assert is_limit_offset(params) is False


# --- Tests for is_cursor ---

def test_is_cursor_returns_true_for_cursor_raw_params():
    params = CursorRawParams(cursor="abc", size=5)
    assert is_cursor(params) is True


def test_is_cursor_returns_false_for_raw_params():
    params = RawParams(limit=10, offset=0)
    assert is_cursor(params) is False


# --- Tests for BaseRawParams.as_limit_offset ---

def test_as_limit_offset_returns_self_for_raw_params():
    params = RawParams(limit=10, offset=5)
    result = params.as_limit_offset()
    assert result is params


def test_as_limit_offset_raises_for_cursor_params():
    params = CursorRawParams(cursor=None, size=10)
    with pytest.raises(ValueError, match="Not a 'limit-offset' params"):
        params.as_limit_offset()


# --- Tests for BaseRawParams.as_cursor ---

def test_as_cursor_returns_self_for_cursor_params():
    params = CursorRawParams(cursor="xyz", size=20)
    result = params.as_cursor()
    assert result is params


def test_as_cursor_raises_for_raw_params():
    params = RawParams(limit=10, offset=0)
    with pytest.raises(ValueError, match="Not a 'cursor' params"):
        params.as_cursor()


# --- Tests for RawParams.as_slice ---

def test_as_slice_with_limit_and_offset():
    params = RawParams(limit=10, offset=5)
    s = params.as_slice()
    assert s == slice(5, 15)


def test_as_slice_with_none_limit():
    params = RawParams(limit=None, offset=3)
    s = params.as_slice()
    assert s == slice(3, None)


def test_as_slice_with_none_offset():
    params = RawParams(limit=10, offset=None)
    s = params.as_slice()
    assert s == slice(None, 10)


# --- Tests for connect_page_and_params ---

def test_connect_page_and_params_sets_attributes():
    class _LocalParams(AbstractParams):
        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    class _LocalPage(AbstractPage[Any]):
        items: list[Any] = []

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> "_LocalPage":
            return cls(items=list(items))

    _LocalParams.__page_type__ = None

    connect_page_and_params(_LocalPage, _LocalParams)

    assert _LocalPage.__params_type__ is _LocalParams
    assert _LocalParams.__page_type__ is _LocalPage


# --- Tests for AbstractParams.set_page ---

def test_abstract_params_set_page():
    class _LocalParams(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    class _LocalPage(AbstractPage[Any]):
        items: list[Any] = []

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> "_LocalPage":
            return cls(items=list(items))

    _LocalParams.set_page(_LocalPage)

    assert _LocalParams.__page_type__ is _LocalPage
    assert _LocalPage.__params_type__ is _LocalParams


# --- Tests for AbstractPage.__init_subclass__ ---

def test_init_subclass_connects_params_when_page_type_is_none():
    class _LocalParams(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    class _LocalPage(AbstractPage[Any]):
        __params_type__ = _LocalParams
        items: list[Any] = []

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> "_LocalPage":
            return cls(items=list(items))

    assert _LocalParams.__page_type__ is _LocalPage


def test_init_subclass_does_not_overwrite_existing_page_type():
    class _LocalParams(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    class _FirstPage(AbstractPage[Any]):
        __params_type__ = _LocalParams
        items: list[Any] = []

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> "_FirstPage":
            return cls(items=list(items))

    # _LocalParams.__page_type__ is now _FirstPage, so a second subclass should not overwrite it
    class _SecondPage(AbstractPage[Any]):
        __params_type__ = _LocalParams
        items: list[Any] = []

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> "_SecondPage":
            return cls(items=list(items))

    assert _LocalParams.__page_type__ is _FirstPage


# --- Tests for AbstractPage.set_params ---

def test_set_params_connects_page_and_params():
    class _LocalParams(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    class _LocalPage(AbstractPage[Any]):
        items: list[Any] = []

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> "_LocalPage":
            return cls(items=list(items))

    _LocalPage.set_params(_LocalParams)

    assert _LocalPage.__params_type__ is _LocalParams
    assert _LocalParams.__page_type__ is _LocalPage


# --- Tests for AbstractPage.__pydantic_init_subclass__ (pydantic v2 only) ---

@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="Pydantic v2 only")
def test_pydantic_init_subclass_applies_exclude():
    class _LocalParams(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    class _LocalPage(AbstractPage[Any]):
        __params_type__ = _LocalParams
        __model_exclude__ = {"items"}
        items: list[Any] = []
        extra_field: str = "hello"

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> "_LocalPage":
            return cls(items=list(items))

    assert _LocalPage.model_fields["items"].exclude is True


@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="Pydantic v2 only")
def test_pydantic_init_subclass_applies_alias():
    class _LocalParams(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    class _LocalPage(AbstractPage[Any]):
        __params_type__ = _LocalParams
        __model_aliases__ = {"items": "data"}
        items: list[Any] = []

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> "_LocalPage":
            return cls(items=list(items))

    assert _LocalPage.model_fields["items"].serialization_alias == "data"


@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="Pydantic v2 only")
def test_pydantic_init_subclass_no_rebuild_when_no_customizations():
    class _LocalParams(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    class _LocalPage(AbstractPage[Any]):
        __params_type__ = _LocalParams
        items: list[Any] = []

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> "_LocalPage":
            return cls(items=list(items))

    # Should not raise; no model_rebuild triggered since no excludes or aliases
    assert _LocalPage.model_fields is not None
