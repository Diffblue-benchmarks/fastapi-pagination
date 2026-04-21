"""Unit tests for fastapi_pagination.ext.sqlmodel module."""
from __future__ import annotations

import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlmodel import Field, SQLModel, Session, select
from sqlmodel.sql.expression import Select, SelectOfScalar

from fastapi_pagination.ext.sqlmodel import _prepare_query, apaginate, paginate


class UserModel(SQLModel, table=True):
    __tablename__ = "test_sqlmodel_users"
    id: int | None = Field(default=None, primary_key=True)
    name: str


# ---------------------------------------------------------------------------
# _prepare_query
# ---------------------------------------------------------------------------


def test_prepare_query_with_select_returns_unchanged():
    query = select(UserModel)
    result = _prepare_query(query)
    assert result is query


def test_prepare_query_with_model_class_returns_select():
    result = _prepare_query(UserModel)
    assert isinstance(result, (Select, SelectOfScalar))


def test_prepare_query_with_select_of_scalar_returns_unchanged():
    query = select(UserModel.id)
    result = _prepare_query(query)
    assert result is query


# ---------------------------------------------------------------------------
# paginate (sync path)
# ---------------------------------------------------------------------------


def test_paginate_sync_calls_paginate_backend(mocker):
    mock_result = MagicMock()
    mock_paginate = mocker.patch("fastapi_pagination.ext.sqlmodel._paginate", return_value=mock_result)

    mock_session = MagicMock(spec=Session)
    query = select(UserModel)

    result = paginate(mock_session, query)

    assert result is mock_result
    mock_paginate.assert_called_once()


def test_paginate_sync_with_count_query(mocker):
    mock_result = MagicMock()
    mock_paginate = mocker.patch("fastapi_pagination.ext.sqlmodel._paginate", return_value=mock_result)

    mock_session = MagicMock(spec=Session)
    query = select(UserModel)
    count_query = select(UserModel)

    result = paginate(mock_session, query, count_query=count_query)

    assert result is mock_result
    call_kwargs = mock_paginate.call_args
    assert call_kwargs.kwargs.get("count_query") is not None


def test_paginate_sync_with_model_class(mocker):
    mock_result = MagicMock()
    mock_paginate = mocker.patch("fastapi_pagination.ext.sqlmodel._paginate", return_value=mock_result)

    mock_session = MagicMock(spec=Session)

    result = paginate(mock_session, UserModel)

    assert result is mock_result
    mock_paginate.assert_called_once()


# ---------------------------------------------------------------------------
# paginate (async path via deprecation warning)
# ---------------------------------------------------------------------------


def test_paginate_with_async_session_emits_deprecation_warning(mocker):
    from sqlalchemy.ext.asyncio import AsyncSession

    mock_apaginate = mocker.patch("fastapi_pagination.ext.sqlmodel.apaginate", return_value=MagicMock())

    mock_async_session = MagicMock(spec=AsyncSession)
    query = select(UserModel)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        paginate(mock_async_session, query)

    assert any(issubclass(warning.category, DeprecationWarning) for warning in w)
    mock_apaginate.assert_called_once()


# ---------------------------------------------------------------------------
# apaginate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_calls_apaginate_backend(mocker):
    from sqlalchemy.ext.asyncio import AsyncSession

    mock_result = MagicMock()
    mock_apaginate_backend = mocker.patch(
        "fastapi_pagination.ext.sqlmodel._apaginate",
        new_callable=AsyncMock,
        return_value=mock_result,
    )

    mock_session = MagicMock(spec=AsyncSession)
    query = select(UserModel)

    result = await apaginate(mock_session, query)

    assert result is mock_result
    mock_apaginate_backend.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_with_count_query(mocker):
    from sqlalchemy.ext.asyncio import AsyncSession

    mock_result = MagicMock()
    mock_apaginate_backend = mocker.patch(
        "fastapi_pagination.ext.sqlmodel._apaginate",
        new_callable=AsyncMock,
        return_value=mock_result,
    )

    mock_session = MagicMock(spec=AsyncSession)
    query = select(UserModel)
    count_query = select(UserModel)

    result = await apaginate(mock_session, query, count_query=count_query)

    assert result is mock_result
    call_kwargs = mock_apaginate_backend.call_args
    assert call_kwargs.kwargs.get("count_query") is not None


@pytest.mark.asyncio
async def test_apaginate_with_model_class(mocker):
    from sqlalchemy.ext.asyncio import AsyncSession

    mock_result = MagicMock()
    mocker.patch(
        "fastapi_pagination.ext.sqlmodel._apaginate",
        new_callable=AsyncMock,
        return_value=mock_result,
    )

    mock_session = MagicMock(spec=AsyncSession)

    result = await apaginate(mock_session, UserModel)

    assert result is mock_result
