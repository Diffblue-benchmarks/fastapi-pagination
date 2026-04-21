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
from fastapi_pagination.types import GreaterEqualZero
from typing_extensions import Self, TypeVar

TAny = TypeVar("TAny", default=Any)


# --- Helpers ---

class ConcreteParams(AbstractParams):
    def to_raw_params(self) -> BaseRawParams:
        return RawParams(limit=10, offset=0)


class ConcretePage(AbstractPage[TAny]):
    items: list[TAny]
    total: GreaterEqualZero

    __params_type__ = ConcreteParams

    @classmethod
    def create(cls, items: Sequence[TAny], params: AbstractParams, **kwargs: Any) -> Self:
        from fastapi_pagination.pydantic import create_pydantic_model
        return create_pydantic_model(cls, items=list(items), total=len(items), **kwargs)


# --- Tests for is_limit_offset and is_cursor ---

def test_is_limit_offset_true():
    params = RawParams(limit=10, offset=0)
    assert is_limit_offset(params) is True


def test_is_limit_offset_false():
    params = CursorRawParams(cursor=None, size=10)
    assert is_limit_offset(params) is False


def test_is_cursor_true():
    params = CursorRawParams(cursor=None, size=10)
    assert is_cursor(params) is True


def test_is_cursor_false():
    params = RawParams(limit=10, offset=0)
    assert is_cursor(params) is False


# --- Tests for BaseRawParams.as_limit_offset ---

def test_as_limit_offset_returns_self():
    params = RawParams(limit=5, offset=2)
    result = params.as_limit_offset()
    assert result is params


def test_as_limit_offset_raises_for_cursor():
    params = CursorRawParams(cursor=None, size=10)
    with pytest.raises(ValueError, match="Not a 'limit-offset' params"):
        params.as_limit_offset()


# --- Tests for BaseRawParams.as_cursor ---

def test_as_cursor_returns_self():
    params = CursorRawParams(cursor=None, size=10)
    result = params.as_cursor()
    assert result is params


def test_as_cursor_raises_for_limit_offset():
    params = RawParams(limit=5, offset=2)
    with pytest.raises(ValueError, match="Not a 'cursor' params"):
        params.as_cursor()


# --- Tests for RawParams.as_slice ---

def test_as_slice_with_limit_and_offset():
    params = RawParams(limit=10, offset=5)
    s = params.as_slice()
    assert s == slice(5, 15)


def test_as_slice_with_none_offset():
    params = RawParams(limit=10, offset=None)
    s = params.as_slice()
    assert s == slice(None, 10)


def test_as_slice_with_none_limit():
    params = RawParams(limit=None, offset=5)
    s = params.as_slice()
    assert s == slice(5, None)


def test_as_slice_with_zero_offset():
    params = RawParams(limit=10, offset=0)
    s = params.as_slice()
    assert s == slice(0, 10)


# --- Tests for connect_page_and_params ---

def test_connect_page_and_params():
    class MyParams2(AbstractParams):
        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    class MyPage2(AbstractPage[TAny]):
        items: list[TAny]
        total: GreaterEqualZero

        @classmethod
        def create(cls, items: Sequence[TAny], params: AbstractParams, **kwargs: Any) -> Self:
            from fastapi_pagination.pydantic import create_pydantic_model
            return create_pydantic_model(cls, items=list(items), total=len(items), **kwargs)

    MyParams2.__page_type__ = None
    connect_page_and_params(MyPage2, MyParams2)
    assert MyPage2.__params_type__ is MyParams2
    assert MyParams2.__page_type__ is MyPage2


# --- Tests for AbstractParams.set_page ---

def test_abstract_params_set_page():
    class SetPageParams(AbstractParams):
        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    class SetPagePage(AbstractPage[TAny]):
        items: list[TAny]
        total: GreaterEqualZero

        @classmethod
        def create(cls, items: Sequence[TAny], params: AbstractParams, **kwargs: Any) -> Self:
            from fastapi_pagination.pydantic import create_pydantic_model
            return create_pydantic_model(cls, items=list(items), total=len(items), **kwargs)

    SetPageParams.__page_type__ = None
    SetPageParams.set_page(SetPagePage)
    assert SetPageParams.__page_type__ is SetPagePage
    assert SetPagePage.__params_type__ is SetPageParams


# --- Tests for AbstractPage.set_params ---

def test_abstract_page_set_params():
    class SetParamsParams(AbstractParams):
        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    class SetParamsPage(AbstractPage[TAny]):
        items: list[TAny]
        total: GreaterEqualZero

        @classmethod
        def create(cls, items: Sequence[TAny], params: AbstractParams, **kwargs: Any) -> Self:
            from fastapi_pagination.pydantic import create_pydantic_model
            return create_pydantic_model(cls, items=list(items), total=len(items), **kwargs)

    SetParamsParams.__page_type__ = None
    SetParamsPage.set_params(SetParamsParams)
    assert SetParamsPage.__params_type__ is SetParamsParams
    assert SetParamsParams.__page_type__ is SetParamsPage


# --- Tests for AbstractPage.__init_subclass__ ---

def test_init_subclass_connects_params_when_page_type_is_none():
    class SubclassParams(AbstractParams):
        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    SubclassParams.__page_type__ = None

    class SubclassPage(AbstractPage[TAny]):
        items: list[TAny]
        total: GreaterEqualZero
        __params_type__ = SubclassParams

        @classmethod
        def create(cls, items: Sequence[TAny], params: AbstractParams, **kwargs: Any) -> Self:
            from fastapi_pagination.pydantic import create_pydantic_model
            return create_pydantic_model(cls, items=list(items), total=len(items), **kwargs)

    assert SubclassParams.__page_type__ is SubclassPage


def test_init_subclass_does_not_override_existing_page_type():
    class OriginalPage(AbstractPage[TAny]):
        items: list[TAny]
        total: GreaterEqualZero

        @classmethod
        def create(cls, items: Sequence[TAny], params: AbstractParams, **kwargs: Any) -> Self:
            from fastapi_pagination.pydantic import create_pydantic_model
            return create_pydantic_model(cls, items=list(items), total=len(items), **kwargs)

    class AlreadyConnectedParams(AbstractParams):
        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    AlreadyConnectedParams.__page_type__ = OriginalPage

    class AnotherPage(AbstractPage[TAny]):
        items: list[TAny]
        total: GreaterEqualZero
        __params_type__ = AlreadyConnectedParams

        @classmethod
        def create(cls, items: Sequence[TAny], params: AbstractParams, **kwargs: Any) -> Self:
            from fastapi_pagination.pydantic import create_pydantic_model
            return create_pydantic_model(cls, items=list(items), total=len(items), **kwargs)

    # Should still be OriginalPage, not AnotherPage
    assert AlreadyConnectedParams.__page_type__ is OriginalPage


# --- Tests for AbstractPage.__pydantic_init_subclass__ ---

@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="Pydantic v2 only")
def test_pydantic_init_subclass_with_model_exclude():
    class ExcludeParams(AbstractParams):
        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    class ExcludePage(AbstractPage[TAny]):
        items: list[TAny]
        total: GreaterEqualZero
        extra_field: str = "default"
        __params_type__ = ExcludeParams
        __model_exclude__ = {"extra_field"}

        @classmethod
        def create(cls, items: Sequence[TAny], params: AbstractParams, **kwargs: Any) -> Self:
            from fastapi_pagination.pydantic import create_pydantic_model
            return create_pydantic_model(cls, items=list(items), total=len(items), extra_field="val", **kwargs)

    assert ExcludePage.model_fields["extra_field"].exclude is True


@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="Pydantic v2 only")
def test_pydantic_init_subclass_with_model_aliases():
    class AliasParams(AbstractParams):
        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    class AliasPage(AbstractPage[TAny]):
        items: list[TAny]
        total: GreaterEqualZero
        my_field: str = "default"
        __params_type__ = AliasParams
        __model_aliases__ = {"my_field": "myField"}

        @classmethod
        def create(cls, items: Sequence[TAny], params: AbstractParams, **kwargs: Any) -> Self:
            from fastapi_pagination.pydantic import create_pydantic_model
            return create_pydantic_model(cls, items=list(items), total=len(items), my_field="val", **kwargs)

    assert AliasPage.model_fields["my_field"].serialization_alias == "myField"


@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="Pydantic v2 only")
def test_pydantic_init_subclass_no_customization():
    class NoCustParams(AbstractParams):
        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    class NoCustPage(AbstractPage[TAny]):
        items: list[TAny]
        total: GreaterEqualZero
        __params_type__ = NoCustParams

        @classmethod
        def create(cls, items: Sequence[TAny], params: AbstractParams, **kwargs: Any) -> Self:
            from fastapi_pagination.pydantic import create_pydantic_model
            return create_pydantic_model(cls, items=list(items), total=len(items), **kwargs)

    # No customizations, model_fields should be accessible normally
    assert "items" in NoCustPage.model_fields
    assert "total" in NoCustPage.model_fields
