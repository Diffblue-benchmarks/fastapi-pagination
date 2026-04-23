"""Unit tests for fastapi_pagination.ext.sqlmodel."""

from __future__ import annotations

import warnings
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlmodel import Field, SQLModel, select
from sqlmodel.sql.expression import Select, SelectOfScalar
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from fastapi_pagination.default import Params
from fastapi_pagination.ext.sqlmodel import _prepare_query, apaginate, paginate


# ---------------------------------------------------------------------------
# A minimal SQLModel for testing (table=True so select() works)
# ---------------------------------------------------------------------------


class _UnitTestItem(SQLModel, table=True):
    __tablename__ = "test_unit_sqlmodel_ext_items_unique"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = ""


# ---------------------------------------------------------------------------
# _prepare_query
# ---------------------------------------------------------------------------


def test_prepare_query_with_model_class_returns_select():
    """_prepare_query wraps a model class in a select statement."""
    result = _prepare_query(_UnitTestItem)
    assert isinstance(result, (Select, SelectOfScalar))


def test_prepare_query_with_existing_select_returns_same():
    """_prepare_query passes through an existing Select unchanged."""
    stmt = select(_UnitTestItem)
    result = _prepare_query(stmt)
    assert result is stmt


def test_prepare_query_with_select_of_scalar_returns_same():
    """_prepare_query passes through an existing SelectOfScalar unchanged."""
    stmt = select(_UnitTestItem.id)
    result = _prepare_query(stmt)
    assert result is stmt


# ---------------------------------------------------------------------------
# paginate – sync path
# ---------------------------------------------------------------------------


def test_paginate_sync_calls_underlying_paginate(mocker):
    """paginate delegates to _paginate for a sync Session."""
    mock_inner = mocker.patch(
        "fastapi_pagination.ext.sqlmodel._paginate",
        return_value=MagicMock(),
    )
    mock_session = MagicMock()
    params = Params(page=1, size=10)

    paginate(mock_session, select(_UnitTestItem), params)

    mock_inner.assert_called_once()


def test_paginate_sync_converts_model_class_to_select(mocker):
    """paginate converts a model class to a Select before passing to _paginate."""
    mock_inner = mocker.patch(
        "fastapi_pagination.ext.sqlmodel._paginate",
        return_value=MagicMock(),
    )
    mock_session = MagicMock()

    paginate(mock_session, _UnitTestItem)

    mock_inner.assert_called_once()
    call_args = mock_inner.call_args
    assert isinstance(call_args.args[1], (Select, SelectOfScalar))


def test_paginate_sync_prepares_count_query_when_provided(mocker):
    """paginate prepares a count_query when one is supplied."""
    mock_inner = mocker.patch(
        "fastapi_pagination.ext.sqlmodel._paginate",
        return_value=MagicMock(),
    )
    mock_session = MagicMock()
    query = select(_UnitTestItem)
    count_query = select(_UnitTestItem)

    paginate(mock_session, query, count_query=count_query)

    call_kwargs = mock_inner.call_args.kwargs
    assert call_kwargs.get("count_query") is not None


def test_paginate_with_async_session_emits_deprecation_warning(mocker):
    """paginate emits DeprecationWarning and delegates to apaginate for AsyncSession."""
    mocker.patch(
        "fastapi_pagination.ext.sqlmodel.apaginate",
        return_value=MagicMock(),
    )
    mock_session = MagicMock()
    mock_session.__class__ = AsyncSession

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        paginate(mock_session, select(_UnitTestItem))

    deprecation_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(deprecation_warnings) >= 1


def test_paginate_with_async_session_calls_apaginate(mocker):
    """paginate calls apaginate (not _paginate) when given an AsyncSession."""
    mock_apaginate = mocker.patch(
        "fastapi_pagination.ext.sqlmodel.apaginate",
        return_value=MagicMock(),
    )
    mock_inner = mocker.patch(
        "fastapi_pagination.ext.sqlmodel._paginate",
        return_value=MagicMock(),
    )
    mock_session = MagicMock()
    mock_session.__class__ = AsyncSession

    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        paginate(mock_session, select(_UnitTestItem))

    mock_apaginate.assert_called_once()
    mock_inner.assert_not_called()


def test_paginate_with_async_connection_calls_apaginate(mocker):
    """paginate calls apaginate when given an AsyncConnection."""
    mock_apaginate = mocker.patch(
        "fastapi_pagination.ext.sqlmodel.apaginate",
        return_value=MagicMock(),
    )
    mock_conn = MagicMock()
    mock_conn.__class__ = AsyncConnection

    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        paginate(mock_conn, select(_UnitTestItem))

    mock_apaginate.assert_called_once()


# ---------------------------------------------------------------------------
# apaginate – async path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_with_model_class_converts_to_select(mocker):
    """apaginate wraps a model class in a select before calling _apaginate."""
    mock_inner = mocker.patch(
        "fastapi_pagination.ext.sqlmodel._apaginate",
        new_callable=AsyncMock,
        return_value=MagicMock(),
    )
    mock_session = MagicMock()
    mock_session.__class__ = AsyncSession
    params = Params(page=1, size=10)

    await apaginate(mock_session, _UnitTestItem, params)

    mock_inner.assert_awaited_once()
    call_args = mock_inner.call_args
    assert isinstance(call_args.args[1], (Select, SelectOfScalar))


@pytest.mark.asyncio
async def test_apaginate_with_existing_select(mocker):
    """apaginate passes an existing Select through to _apaginate."""
    mock_inner = mocker.patch(
        "fastapi_pagination.ext.sqlmodel._apaginate",
        new_callable=AsyncMock,
        return_value=MagicMock(),
    )
    mock_session = MagicMock()
    mock_session.__class__ = AsyncSession
    query = select(_UnitTestItem)
    params = Params(page=1, size=10)

    await apaginate(mock_session, query, params)

    mock_inner.assert_awaited_once()


@pytest.mark.asyncio
async def test_apaginate_prepares_count_query_when_provided(mocker):
    """apaginate prepares count_query when one is supplied."""
    mock_inner = mocker.patch(
        "fastapi_pagination.ext.sqlmodel._apaginate",
        new_callable=AsyncMock,
        return_value=MagicMock(),
    )
    mock_session = MagicMock()
    mock_session.__class__ = AsyncSession
    query = select(_UnitTestItem)
    count_query = select(_UnitTestItem)

    await apaginate(mock_session, query, count_query=count_query)

    call_kwargs = mock_inner.call_args.kwargs
    assert call_kwargs.get("count_query") is not None


@pytest.mark.asyncio
async def test_apaginate_calls_inner_apaginate(mocker):
    """apaginate returns the awaited result from _apaginate."""
    expected = MagicMock()
    mock_inner = mocker.patch(
        "fastapi_pagination.ext.sqlmodel._apaginate",
        new_callable=AsyncMock,
        return_value=expected,
    )
    mock_session = MagicMock()
    mock_session.__class__ = AsyncSession

    result = await apaginate(mock_session, select(_UnitTestItem))

    assert result is expected
    mock_inner.assert_awaited_once()
