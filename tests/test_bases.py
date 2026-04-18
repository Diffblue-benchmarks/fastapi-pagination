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


# --- is_limit_offset ---

def test_is_limit_offset_returns_true_for_raw_params():
    params = RawParams(limit=10, offset=0)
    assert is_limit_offset(params) is True


def test_is_limit_offset_returns_false_for_cursor_params():
    params = CursorRawParams(cursor=None, size=10)
    assert is_limit_offset(params) is False


# --- is_cursor ---

def test_is_cursor_returns_true_for_cursor_params():
    params = CursorRawParams(cursor=None, size=10)
    assert is_cursor(params) is True


def test_is_cursor_returns_false_for_raw_params():
    params = RawParams(limit=10, offset=0)
    assert is_cursor(params) is False


# --- BaseRawParams.as_limit_offset ---

def test_as_limit_offset_returns_self_for_limit_offset():
    params = RawParams(limit=5, offset=10)
    result = params.as_limit_offset()
    assert result is params


def test_as_limit_offset_raises_for_cursor():
    params = CursorRawParams(cursor=None, size=10)
    with pytest.raises(ValueError, match="Not a 'limit-offset' params"):
        params.as_limit_offset()


# --- BaseRawParams.as_cursor ---

def test_as_cursor_returns_self_for_cursor():
    params = CursorRawParams(cursor=None, size=10)
    result = params.as_cursor()
    assert result is params


def test_as_cursor_raises_for_limit_offset():
    params = RawParams(limit=5, offset=0)
    with pytest.raises(ValueError, match="Not a 'cursor' params"):
        params.as_cursor()


# --- RawParams.as_slice ---

def test_raw_params_as_slice_with_limit_and_offset():
    params = RawParams(limit=10, offset=5)
    s = params.as_slice()
    assert s == slice(5, 15)


def test_raw_params_as_slice_with_none_offset():
    params = RawParams(limit=10, offset=None)
    s = params.as_slice()
    assert s == slice(None, 10)


def test_raw_params_as_slice_with_none_limit():
    params = RawParams(limit=None, offset=5)
    s = params.as_slice()
    assert s == slice(5, None)


def test_raw_params_as_slice_with_zero_offset():
    params = RawParams(limit=10, offset=0)
    s = params.as_slice()
    assert s == slice(0, 10)


# --- connect_page_and_params ---

def test_connect_page_and_params():
    class MyParams(AbstractParams):
        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    class MyPage(AbstractPage[Any]):
        __params_type__ = MyParams

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any):
            pass

    # Reset the page_type
    MyParams.__page_type__ = None

    connect_page_and_params(MyPage, MyParams)

    assert MyPage.__params_type__ is MyParams
    assert MyParams.__page_type__ is MyPage


# --- AbstractParams.set_page ---

def test_abstract_params_set_page():
    class SetPageParams(AbstractParams):
        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    class SetPagePage(AbstractPage[Any]):
        __params_type__ = SetPageParams

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any):
            pass

    SetPageParams.__page_type__ = None

    SetPageParams.set_page(SetPagePage)

    assert SetPageParams.__page_type__ is SetPagePage
    assert SetPagePage.__params_type__ is SetPageParams


# --- AbstractPage.__init_subclass__ ---

def test_abstract_page_init_subclass_connects_params_when_page_type_is_none():
    class InitSubParams(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    class InitSubPage(AbstractPage[Any]):
        __params_type__ = InitSubParams

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any):
            pass

    # __init_subclass__ runs on class creation; check the connection was made
    assert InitSubPage.__params_type__ is InitSubParams
    assert InitSubParams.__page_type__ is InitSubPage


# --- AbstractPage.set_params ---

def test_abstract_page_set_params():
    class SetParamsParams(AbstractParams):
        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    class SetParamsPage(AbstractPage[Any]):
        __params_type__ = SetParamsParams

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any):
            pass

    SetParamsParams.__page_type__ = None
    SetParamsPage.set_params(SetParamsParams)

    assert SetParamsPage.__params_type__ is SetParamsParams
    assert SetParamsParams.__page_type__ is SetParamsPage


# --- AbstractPage.__pydantic_init_subclass__ (pydantic v2 only) ---

@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="Pydantic v2 only")
def test_pydantic_init_subclass_with_exclude():
    from fastapi_pagination.bases import BasePage
    from fastapi_pagination.types import GreaterEqualZero

    class ExcludeParams(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    class ExcludePage(BasePage[Any]):
        __params_type__ = ExcludeParams
        __model_exclude__ = {"total"}

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any):
            pass

    # Check that 'total' field has exclude=True
    assert ExcludePage.model_fields["total"].exclude is True


@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="Pydantic v2 only")
def test_pydantic_init_subclass_with_aliases():
    from fastapi_pagination.bases import BasePage

    class AliasParams(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    class AliasPage(BasePage[Any]):
        __params_type__ = AliasParams
        __model_aliases__ = {"total": "totalCount"}

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any):
            pass

    assert AliasPage.model_fields["total"].serialization_alias == "totalCount"


@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="Pydantic v2 only")
def test_pydantic_init_subclass_no_customization():
    from fastapi_pagination.bases import BasePage

    class NoCustomParams(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    # No model_exclude or model_aliases - should not rebuild model
    class NoCustomPage(BasePage[Any]):
        __params_type__ = NoCustomParams

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any):
            pass

    # Just check the class was created without errors
    assert NoCustomPage.__model_exclude__ == set()
    assert NoCustomPage.__model_aliases__ == {}
