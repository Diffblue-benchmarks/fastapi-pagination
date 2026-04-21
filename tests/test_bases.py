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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _SimpleParams(AbstractParams):
    """Minimal concrete AbstractParams for testing."""

    __page_type__ = None

    def to_raw_params(self) -> BaseRawParams:
        return RawParams(limit=10, offset=0)


# ---------------------------------------------------------------------------
# is_limit_offset
# ---------------------------------------------------------------------------


def test_is_limit_offset_returns_true_for_raw_params():
    params = RawParams(limit=10, offset=0)
    assert is_limit_offset(params) is True


def test_is_limit_offset_returns_false_for_cursor_params():
    params = CursorRawParams(cursor=None, size=10)
    assert is_limit_offset(params) is False


# ---------------------------------------------------------------------------
# is_cursor
# ---------------------------------------------------------------------------


def test_is_cursor_returns_true_for_cursor_params():
    params = CursorRawParams(cursor=None, size=10)
    assert is_cursor(params) is True


def test_is_cursor_returns_false_for_raw_params():
    params = RawParams(limit=10, offset=0)
    assert is_cursor(params) is False


# ---------------------------------------------------------------------------
# BaseRawParams.as_limit_offset
# ---------------------------------------------------------------------------


def test_as_limit_offset_returns_self_for_raw_params():
    params = RawParams(limit=5, offset=2)
    result = params.as_limit_offset()
    assert result is params


def test_as_limit_offset_raises_value_error_for_cursor_params():
    params = CursorRawParams(cursor=None, size=10)
    with pytest.raises(ValueError, match="Not a 'limit-offset' params"):
        params.as_limit_offset()


# ---------------------------------------------------------------------------
# BaseRawParams.as_cursor
# ---------------------------------------------------------------------------


def test_as_cursor_returns_self_for_cursor_params():
    params = CursorRawParams(cursor="abc", size=10)
    result = params.as_cursor()
    assert result is params


def test_as_cursor_raises_value_error_for_raw_params():
    params = RawParams(limit=5, offset=2)
    with pytest.raises(ValueError, match="Not a 'cursor' params"):
        params.as_cursor()


# ---------------------------------------------------------------------------
# RawParams.as_slice
# ---------------------------------------------------------------------------


def test_raw_params_as_slice_with_limit_and_offset():
    params = RawParams(limit=10, offset=5)
    assert params.as_slice() == slice(5, 15)


def test_raw_params_as_slice_with_none_limit():
    params = RawParams(limit=None, offset=5)
    assert params.as_slice() == slice(5, None)


def test_raw_params_as_slice_with_none_offset():
    params = RawParams(limit=10, offset=None)
    assert params.as_slice() == slice(None, 10)


def test_raw_params_as_slice_with_zero_offset():
    params = RawParams(limit=10, offset=0)
    assert params.as_slice() == slice(0, 10)


# ---------------------------------------------------------------------------
# connect_page_and_params
# ---------------------------------------------------------------------------


def test_connect_page_and_params_sets_both_directions():
    class _ParamsA(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> BaseRawParams:
            return RawParams(limit=1, offset=0)

    class _FakePage:
        __params_type__ = None

    connect_page_and_params(_FakePage, _ParamsA)

    assert _FakePage.__params_type__ is _ParamsA
    assert _ParamsA.__page_type__ is _FakePage


# ---------------------------------------------------------------------------
# AbstractParams.set_page
# ---------------------------------------------------------------------------


def test_abstract_params_set_page_delegates_to_connect():
    class _ParamsB(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> BaseRawParams:
            return RawParams(limit=1, offset=0)

    class _FakePage2:
        __params_type__ = None

    _ParamsB.set_page(_FakePage2)

    assert _ParamsB.__page_type__ is _FakePage2
    assert _FakePage2.__params_type__ is _ParamsB


# ---------------------------------------------------------------------------
# AbstractPage.__init_subclass__
# ---------------------------------------------------------------------------


def test_abstract_page_init_subclass_connects_unbound_params():
    """When a page subclass declares __params_type__ whose __page_type__ is None,
    __init_subclass__ should call set_page to connect them."""

    class _ParamsC(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> BaseRawParams:
            return RawParams(limit=1, offset=0)

    class _TestPage(AbstractPage[Any]):
        items: list = []
        __params_type__ = _ParamsC

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> "_TestPage":
            return cls(items=list(items))

    assert _ParamsC.__page_type__ is _TestPage


def test_abstract_page_init_subclass_does_not_override_existing_page():
    """If __page_type__ is already set on params, __init_subclass__ must not overwrite it."""

    class _ParamsD(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> BaseRawParams:
            return RawParams(limit=1, offset=0)

    class _FirstPage(AbstractPage[Any]):
        items: list = []
        __params_type__ = _ParamsD

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> "_FirstPage":
            return cls(items=list(items))

    # _ParamsD is now connected to _FirstPage
    assert _ParamsD.__page_type__ is _FirstPage

    # Creating a second page with the same params must NOT overwrite the link
    class _SecondPage(AbstractPage[Any]):
        items: list = []
        __params_type__ = _ParamsD

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> "_SecondPage":
            return cls(items=list(items))

    assert _ParamsD.__page_type__ is _FirstPage  # unchanged


# ---------------------------------------------------------------------------
# AbstractPage.set_params
# ---------------------------------------------------------------------------


def test_abstract_page_set_params():
    class _ParamsE(AbstractParams):
        __page_type__ = None

        def to_raw_params(self) -> BaseRawParams:
            return RawParams(limit=1, offset=0)

    class _PageForSetParams(AbstractPage[Any]):
        items: list = []

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> "_PageForSetParams":
            return cls(items=list(items))

    _PageForSetParams.set_params(_ParamsE)

    assert _PageForSetParams.__params_type__ is _ParamsE
    assert _ParamsE.__page_type__ is _PageForSetParams


# ---------------------------------------------------------------------------
# AbstractPage.__pydantic_init_subclass__  (pydantic v2 only)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="Pydantic v2 only")
def test_pydantic_init_subclass_with_model_exclude():
    class _PageWithExclude(AbstractPage[Any]):
        items: list = []
        hidden_field: str = "secret"
        __model_exclude__ = {"hidden_field"}

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> "_PageWithExclude":
            return cls(items=list(items))

    assert _PageWithExclude.model_fields["hidden_field"].exclude is True


@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="Pydantic v2 only")
def test_pydantic_init_subclass_with_model_aliases():
    class _PageWithAlias(AbstractPage[Any]):
        items: list = []
        total_count: int = 0
        __model_aliases__ = {"total_count": "totalCount"}

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> "_PageWithAlias":
            return cls(items=list(items))

    assert _PageWithAlias.model_fields["total_count"].serialization_alias == "totalCount"


@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="Pydantic v2 only")
def test_pydantic_init_subclass_no_customization_skips_rebuild():
    """When __model_exclude__ and __model_aliases__ are both empty, model_rebuild is NOT called
    (no error, fields unchanged)."""

    class _PlainPage(AbstractPage[Any]):
        items: list = []

        @classmethod
        def create(cls, items: Sequence[Any], params: AbstractParams, **kwargs: Any) -> "_PlainPage":
            return cls(items=list(items))

    # Just verifying that creation succeeds and model_fields are accessible
    assert "items" in _PlainPage.model_fields
