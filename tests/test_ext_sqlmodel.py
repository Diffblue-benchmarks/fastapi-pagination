from __future__ import annotations

import warnings
from typing import Optional

import pytest
from sqlmodel import Field, SQLModel, select
from sqlmodel.sql.expression import Select, SelectOfScalar
from unittest.mock import AsyncMock, MagicMock

from fastapi_pagination.ext.sqlmodel import _prepare_query, apaginate, paginate


class User(SQLModel, table=True):
    __tablename__ = "users_sqlmodel_test"
    id: Optional[int] = Field(default=None, primary_key=True)


# _prepare_query tests

def test_prepare_query_with_select_returns_as_is():
    query = select(User)
    result = _prepare_query(query)
    assert result is query


def test_prepare_query_with_sqlmodel_class_wraps_in_select():
    result = _prepare_query(User)
    assert isinstance(result, (Select, SelectOfScalar))


def test_prepare_query_with_select_of_scalar_returns_as_is():
    query = select(User.id)
    result = _prepare_query(query)
    assert result is query


# paginate (sync path) tests

def test_paginate_sync_calls_sqlalchemy_paginate(mocker):
    mock_paginate = mocker.patch("fastapi_pagination.ext.sqlmodel._paginate", return_value="page_result")
    session = MagicMock()
    query = select(User)

    result = paginate(session, query)

    mock_paginate.assert_called_once()
    assert result == "page_result"


def test_paginate_sync_with_count_query(mocker):
    mock_paginate = mocker.patch("fastapi_pagination.ext.sqlmodel._paginate", return_value="page_result")
    session = MagicMock()
    query = select(User)
    count_query = select(User)

    result = paginate(session, query, count_query=count_query)

    call_kwargs = mock_paginate.call_args
    assert call_kwargs is not None
    assert result == "page_result"


def test_paginate_sync_with_model_class(mocker):
    mock_paginate = mocker.patch("fastapi_pagination.ext.sqlmodel._paginate", return_value="page_result")
    session = MagicMock()

    result = paginate(session, User)

    mock_paginate.assert_called_once()
    assert result == "page_result"


def test_paginate_async_session_warns_and_calls_apaginate(mocker):
    from sqlalchemy.ext.asyncio import AsyncSession

    mock_apaginate = mocker.patch("fastapi_pagination.ext.sqlmodel.apaginate", return_value=AsyncMock())
    session = MagicMock(spec=AsyncSession)
    query = select(User)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        paginate(session, query)
        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert any("apaginate" in str(x.message) for x in deprecation_warnings)

    mock_apaginate.assert_called_once()


def test_paginate_async_connection_warns_and_calls_apaginate(mocker):
    from sqlalchemy.ext.asyncio import AsyncConnection

    mock_apaginate = mocker.patch("fastapi_pagination.ext.sqlmodel.apaginate", return_value=AsyncMock())
    session = MagicMock(spec=AsyncConnection)
    query = select(User)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        paginate(session, query)
        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_warnings) >= 1

    mock_apaginate.assert_called_once()


# apaginate tests

@pytest.mark.asyncio
async def test_apaginate_calls_sqlalchemy_apaginate(mocker):
    mock_apaginate = mocker.patch(
        "fastapi_pagination.ext.sqlmodel._apaginate",
        new_callable=AsyncMock,
        return_value="async_page",
    )
    from sqlalchemy.ext.asyncio import AsyncSession

    session = MagicMock(spec=AsyncSession)
    query = select(User)

    result = await apaginate(session, query)

    mock_apaginate.assert_awaited_once()
    assert result == "async_page"


@pytest.mark.asyncio
async def test_apaginate_with_count_query(mocker):
    mock_apaginate = mocker.patch(
        "fastapi_pagination.ext.sqlmodel._apaginate",
        new_callable=AsyncMock,
        return_value="async_page",
    )
    from sqlalchemy.ext.asyncio import AsyncSession

    session = MagicMock(spec=AsyncSession)
    query = select(User)
    count_query = select(User)

    result = await apaginate(session, query, count_query=count_query)

    mock_apaginate.assert_awaited_once()
    assert result == "async_page"


@pytest.mark.asyncio
async def test_apaginate_with_model_class(mocker):
    mock_apaginate = mocker.patch(
        "fastapi_pagination.ext.sqlmodel._apaginate",
        new_callable=AsyncMock,
        return_value="async_page",
    )
    from sqlalchemy.ext.asyncio import AsyncSession

    session = MagicMock(spec=AsyncSession)

    result = await apaginate(session, User)

    mock_apaginate.assert_awaited_once()
    assert result == "async_page"
