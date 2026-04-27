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
from fastapi_pagination.pydantic import IS_PYDANTIC_V2
from typing_extensions import Self, TypeVar

TAny = TypeVar("TAny", default=Any)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


class ConcreteParams(AbstractParams):
    """Minimal concrete AbstractParams implementation."""

    __page_type__ = None  # will be set by connect_page_and_params

    def to_raw_params(self) -> RawParams:
        return RawParams(limit=10, offset=0)


class ConcreteParams2(AbstractParams):
    """Second concrete params to avoid cross-test state pollution."""

    __page_type__ = None

    def to_raw_params(self) -> RawParams:
        return RawParams(limit=5, offset=5)


# ---------------------------------------------------------------------------
# is_limit_offset / is_cursor
# ---------------------------------------------------------------------------


def test_is_limit_offset_returns_true_for_raw_params():
    params = RawParams(limit=10, offset=0)
    assert is_limit_offset(params) is True


def test_is_limit_offset_returns_false_for_cursor_params():
    params = CursorRawParams(cursor=None, size=10)
    assert is_limit_offset(params) is False


def test_is_cursor_returns_true_for_cursor_params():
    params = CursorRawParams(cursor="abc", size=5)
    assert is_cursor(params) is True


def test_is_cursor_returns_false_for_raw_params():
    params = RawParams(limit=10, offset=0)
    assert is_cursor(params) is False


# ---------------------------------------------------------------------------
# BaseRawParams.as_limit_offset / as_cursor
# ---------------------------------------------------------------------------


def test_as_limit_offset_returns_self_when_limit_offset():
    params = RawParams(limit=10, offset=5)
    result = params.as_limit_offset()
    assert result is params


def test_as_limit_offset_raises_for_cursor_params():
    params = CursorRawParams(cursor=None, size=10)
    with pytest.raises(ValueError, match="Not a 'limit-offset' params"):
        params.as_limit_offset()


def test_as_cursor_returns_self_when_cursor():
    params = CursorRawParams(cursor="token", size=20)
    result = params.as_cursor()
    assert result is params


def test_as_cursor_raises_for_limit_offset_params():
    params = RawParams(limit=10, offset=0)
    with pytest.raises(ValueError, match="Not a 'cursor' params"):
        params.as_cursor()


# ---------------------------------------------------------------------------
# RawParams.as_slice
# ---------------------------------------------------------------------------


def test_raw_params_as_slice_with_limit_and_offset():
    params = RawParams(limit=10, offset=5)
    s = params.as_slice()
    assert s == slice(5, 15)


def test_raw_params_as_slice_with_none_limit():
    params = RawParams(limit=None, offset=3)
    s = params.as_slice()
    assert s == slice(3, None)


def test_raw_params_as_slice_offset_none_with_limit():
    params = RawParams(limit=10, offset=None)
    s = params.as_slice()
    assert s == slice(None, 10)


# ---------------------------------------------------------------------------
# connect_page_and_params
# ---------------------------------------------------------------------------


def _make_fresh_page_class():
    """Return a brand new AbstractPage subclass with its own params type."""

    class FreshParams(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> RawParams:
            return RawParams()

    class FreshPage(AbstractPage[Any]):
        __params_type__ = FreshParams

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> Self:
            return cls(items=items, total=len(items), **kwargs)

    # Reset page_type so we can use connect_page_and_params freely
    FreshParams.__page_type__ = None
    return FreshPage, FreshParams


def test_connect_page_and_params():
    FreshPage, FreshParams = _make_fresh_page_class()
    FreshParams.__page_type__ = None  # ensure not set
    connect_page_and_params(FreshPage, FreshParams)
    assert FreshPage.__params_type__ is FreshParams
    assert FreshParams.__page_type__ is FreshPage


# ---------------------------------------------------------------------------
# AbstractParams.set_page
# ---------------------------------------------------------------------------


def test_abstract_params_set_page():
    class LocalParams(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> RawParams:
            return RawParams()

    class LocalPage(AbstractPage[Any]):
        __params_type__ = LocalParams

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> Self:
            return cls(items=items, total=len(items), **kwargs)

    LocalParams.__page_type__ = None
    LocalParams.set_page(LocalPage)
    assert LocalParams.__page_type__ is LocalPage
    assert LocalPage.__params_type__ is LocalParams


# ---------------------------------------------------------------------------
# AbstractPage.__init_subclass__
# ---------------------------------------------------------------------------


def test_init_subclass_connects_params_when_page_type_is_none():
    class SubParams(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> RawParams:
            return RawParams()

    class SubPage(AbstractPage[Any]):
        __params_type__ = SubParams

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> Self:
            return cls(items=items, total=len(items), **kwargs)

    # __init_subclass__ should have set SubParams.__page_type__ to SubPage
    assert SubParams.__page_type__ is SubPage


def test_init_subclass_does_not_overwrite_existing_page_type():
    class ParamsAlreadyConnected(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> RawParams:
            return RawParams()

    class FirstPage(AbstractPage[Any]):
        __params_type__ = ParamsAlreadyConnected

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> Self:
            return cls(items=items, total=len(items), **kwargs)

    # FirstPage.__init_subclass__ should have linked ParamsAlreadyConnected → FirstPage
    assert ParamsAlreadyConnected.__page_type__ is FirstPage

    class SecondPage(AbstractPage[Any]):
        __params_type__ = ParamsAlreadyConnected

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> Self:
            return cls(items=items, total=len(items), **kwargs)

    # Should NOT overwrite: params already had a page_type
    assert ParamsAlreadyConnected.__page_type__ is FirstPage


# ---------------------------------------------------------------------------
# AbstractPage.set_params
# ---------------------------------------------------------------------------


def test_abstract_page_set_params():
    class LocalParams2(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> RawParams:
            return RawParams()

    class LocalPage2(AbstractPage[Any]):
        __params_type__ = LocalParams2

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> Self:
            return cls(items=items, total=len(items), **kwargs)

    LocalParams2.__page_type__ = None  # reset
    LocalPage2.set_params(LocalParams2)
    assert LocalPage2.__params_type__ is LocalParams2
    assert LocalParams2.__page_type__ is LocalPage2


# ---------------------------------------------------------------------------
# AbstractPage.__pydantic_init_subclass__ (pydantic v2 only)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="pydantic v2 only")
def test_pydantic_init_subclass_with_model_exclude():
    class ParamsForExclude(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> RawParams:
            return RawParams()

    class PageWithExclude(AbstractPage[Any]):
        my_field: int = 0
        __params_type__ = ParamsForExclude
        __model_exclude__ = {"my_field"}

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> Self:
            return cls(my_field=0, **kwargs)

    # The field "my_field" should have been marked excluded
    assert PageWithExclude.model_fields["my_field"].exclude is True


@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="pydantic v2 only")
def test_pydantic_init_subclass_with_model_aliases():
    class ParamsForAlias(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> RawParams:
            return RawParams()

    class PageWithAlias(AbstractPage[Any]):
        my_field: int = 0
        __params_type__ = ParamsForAlias
        __model_aliases__ = {"my_field": "myField"}

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> Self:
            return cls(my_field=0, **kwargs)

    assert PageWithAlias.model_fields["my_field"].serialization_alias == "myField"


@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="pydantic v2 only")
def test_pydantic_init_subclass_without_customizations():
    class ParamsForPlain(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> RawParams:
            return RawParams()

    class PlainPage(AbstractPage[Any]):
        my_field: int = 0
        __params_type__ = ParamsForPlain

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> Self:
            return cls(my_field=0, **kwargs)

    # No exclude / aliases — field should remain unmodified (exclude not set to True)
    assert PlainPage.model_fields["my_field"].exclude is not True
