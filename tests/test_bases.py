from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Generic

import pytest
from typing_extensions import TypeVar

from fastapi_pagination.bases import (
    AbstractPage,
    AbstractParams,
    BasePage,
    CursorRawParams,
    RawParams,
    connect_page_and_params,
    is_cursor,
    is_limit_offset,
)
from fastapi_pagination.pydantic import create_pydantic_model
from fastapi_pagination.pydantic.consts import IS_PYDANTIC_V2

TAny = TypeVar("TAny", default=Any)


# ============================================================
# Tests for is_limit_offset
# ============================================================


def test_is_limit_offset_returns_true_for_raw_params():
    params = RawParams(limit=10, offset=0)
    assert is_limit_offset(params) is True


def test_is_limit_offset_returns_false_for_cursor_params():
    params = CursorRawParams(cursor=None, size=10)
    assert is_limit_offset(params) is False


# ============================================================
# Tests for is_cursor
# ============================================================


def test_is_cursor_returns_true_for_cursor_params():
    params = CursorRawParams(cursor=None, size=10)
    assert is_cursor(params) is True


def test_is_cursor_returns_false_for_raw_params():
    params = RawParams(limit=10, offset=0)
    assert is_cursor(params) is False


# ============================================================
# Tests for BaseRawParams.as_limit_offset
# ============================================================


def test_as_limit_offset_returns_self_for_raw_params():
    params = RawParams(limit=10, offset=5)
    result = params.as_limit_offset()
    assert result is params


def test_as_limit_offset_raises_for_cursor_params():
    params = CursorRawParams(cursor=None, size=10)
    with pytest.raises(ValueError, match="Not a 'limit-offset' params"):
        params.as_limit_offset()


# ============================================================
# Tests for BaseRawParams.as_cursor
# ============================================================


def test_as_cursor_returns_self_for_cursor_params():
    params = CursorRawParams(cursor=None, size=10)
    result = params.as_cursor()
    assert result is params


def test_as_cursor_raises_for_raw_params():
    params = RawParams(limit=10, offset=0)
    with pytest.raises(ValueError, match="Not a 'cursor' params"):
        params.as_cursor()


# ============================================================
# Tests for RawParams.as_slice
# ============================================================


def test_raw_params_as_slice_with_limit_and_offset():
    params = RawParams(limit=10, offset=5)
    result = params.as_slice()
    assert result == slice(5, 15)


def test_raw_params_as_slice_with_none_limit():
    params = RawParams(limit=None, offset=5)
    result = params.as_slice()
    assert result == slice(5, None)


def test_raw_params_as_slice_with_none_offset():
    params = RawParams(limit=10, offset=None)
    result = params.as_slice()
    assert result == slice(None, 10)


def test_raw_params_as_slice_with_zero_offset():
    params = RawParams(limit=10, offset=0)
    result = params.as_slice()
    assert result == slice(0, 10)


# ============================================================
# Tests for connect_page_and_params
# ============================================================


def test_connect_page_and_params_sets_page_attr_on_params():
    class CpTestParams(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> RawParams:
            return RawParams(limit=10, offset=0)

    class CpTestPage(BasePage[TAny], Generic[TAny]):
        __params_type__ = CpTestParams

        @classmethod
        def create(cls, items: Sequence[TAny], params: AbstractParams, **kwargs: Any) -> "CpTestPage[TAny]":
            return create_pydantic_model(cls, items=list(items), total=len(items), **kwargs)

    class AnotherCpParams(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> RawParams:
            return RawParams(limit=20, offset=0)

    connect_page_and_params(CpTestPage, AnotherCpParams)

    assert CpTestPage.__params_type__ is AnotherCpParams
    assert AnotherCpParams.__page_type__ is CpTestPage


# ============================================================
# Tests for AbstractParams.set_page
# ============================================================


def test_abstract_params_set_page():
    class SpTestParams(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> RawParams:
            return RawParams(limit=10, offset=0)

    class SpTestPage(BasePage[TAny], Generic[TAny]):
        __params_type__ = SpTestParams

        @classmethod
        def create(cls, items: Sequence[TAny], params: AbstractParams, **kwargs: Any) -> "SpTestPage[TAny]":
            return create_pydantic_model(cls, items=list(items), total=len(items), **kwargs)

    SpTestParams.__page_type__ = None
    SpTestParams.set_page(SpTestPage)

    assert SpTestParams.__page_type__ is SpTestPage
    assert SpTestPage.__params_type__ is SpTestParams


# ============================================================
# Tests for AbstractPage.__init_subclass__
# ============================================================


def test_init_subclass_auto_connects_params_when_page_type_is_none():
    class IscTestParams(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> RawParams:
            return RawParams(limit=10, offset=0)

    class IscTestPage(BasePage[TAny], Generic[TAny]):
        __params_type__ = IscTestParams

        @classmethod
        def create(cls, items: Sequence[TAny], params: AbstractParams, **kwargs: Any) -> "IscTestPage[TAny]":
            return create_pydantic_model(cls, items=list(items), total=len(items), **kwargs)

    assert IscTestParams.__page_type__ is IscTestPage


def test_init_subclass_does_not_override_existing_page_type():
    class IscTestParams2(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> RawParams:
            return RawParams(limit=10, offset=0)

    class IscFirstTestPage(BasePage[TAny], Generic[TAny]):
        __params_type__ = IscTestParams2

        @classmethod
        def create(cls, items: Sequence[TAny], params: AbstractParams, **kwargs: Any) -> "IscFirstTestPage[TAny]":
            return create_pydantic_model(cls, items=list(items), total=len(items), **kwargs)

    assert IscTestParams2.__page_type__ is IscFirstTestPage

    class IscSecondTestPage(BasePage[TAny], Generic[TAny]):
        __params_type__ = IscTestParams2

        @classmethod
        def create(
            cls, items: Sequence[TAny], params: AbstractParams, **kwargs: Any
        ) -> "IscSecondTestPage[TAny]":
            return create_pydantic_model(cls, items=list(items), total=len(items), **kwargs)

    assert IscTestParams2.__page_type__ is IscFirstTestPage


# ============================================================
# Tests for AbstractPage.set_params
# ============================================================


def test_abstract_page_set_params():
    class SetpTestParams(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> RawParams:
            return RawParams(limit=10, offset=0)

    class SetpTestPage(BasePage[TAny], Generic[TAny]):
        __params_type__ = SetpTestParams

        @classmethod
        def create(cls, items: Sequence[TAny], params: AbstractParams, **kwargs: Any) -> "SetpTestPage[TAny]":
            return create_pydantic_model(cls, items=list(items), total=len(items), **kwargs)

    class NewSetpTestParams(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> RawParams:
            return RawParams(limit=20, offset=0)

    SetpTestPage.set_params(NewSetpTestParams)

    assert SetpTestPage.__params_type__ is NewSetpTestParams
    assert NewSetpTestParams.__page_type__ is SetpTestPage


# ============================================================
# Tests for AbstractPage.__pydantic_init_subclass__ (pydantic v2 only)
# ============================================================


@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="Pydantic v2 only")
def test_pydantic_init_subclass_with_model_exclude():
    class ExcludeTestParams(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> RawParams:
            return RawParams(limit=10, offset=0)

    class ExcludeTestPage(BasePage[TAny], Generic[TAny]):
        __params_type__ = ExcludeTestParams
        __model_exclude__ = {"total"}

        @classmethod
        def create(
            cls, items: Sequence[TAny], params: AbstractParams, **kwargs: Any
        ) -> "ExcludeTestPage[TAny]":
            return create_pydantic_model(cls, items=list(items), total=len(items), **kwargs)

    assert ExcludeTestPage.model_fields["total"].exclude is True


@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="Pydantic v2 only")
def test_pydantic_init_subclass_with_model_aliases():
    class AliasTestParams(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> RawParams:
            return RawParams(limit=10, offset=0)

    class AliasTestPage(BasePage[TAny], Generic[TAny]):
        __params_type__ = AliasTestParams
        __model_aliases__ = {"total": "count"}

        @classmethod
        def create(
            cls, items: Sequence[TAny], params: AbstractParams, **kwargs: Any
        ) -> "AliasTestPage[TAny]":
            return create_pydantic_model(cls, items=list(items), total=len(items), **kwargs)

    assert AliasTestPage.model_fields["total"].serialization_alias == "count"
