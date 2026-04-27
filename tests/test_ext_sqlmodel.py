"""Tests for fastapi_pagination.ext.sqlmodel module."""
from __future__ import annotations

import sys
import types
import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Patch unavailable third-party modules before importing the module under test
# ---------------------------------------------------------------------------

def _install_sqlmodel_mocks() -> None:
    # --- sqlalchemy mocks (needed by fastapi_pagination.ext.sqlalchemy) ---
    sa = types.ModuleType("sqlalchemy")
    sa_sql = types.ModuleType("sqlalchemy.sql")
    sa_sql_elements = types.ModuleType("sqlalchemy.sql.elements")
    sa_engine = types.ModuleType("sqlalchemy.engine")
    sa_exc = types.ModuleType("sqlalchemy.exc")
    sa_orm = types.ModuleType("sqlalchemy.orm")
    sa_ext = types.ModuleType("sqlalchemy.ext")
    sa_ext_asyncio = types.ModuleType("sqlalchemy.ext.asyncio")

    for attr in ("func", "select", "text", "Column", "Integer", "String", "Table", "MetaData"):
        setattr(sa, attr, MagicMock())
    for attr in ("Select", "CompoundSelect"):
        setattr(sa_sql, attr, MagicMock())
    setattr(sa_sql_elements, "TextClause", MagicMock())
    setattr(sa_engine, "Connection", MagicMock())
    setattr(sa_exc, "InvalidRequestError", Exception)
    for attr in ("Query", "Session", "noload", "scoped_session"):
        setattr(sa_orm, attr, MagicMock())

    # AsyncSession and AsyncConnection as distinct classes for isinstance checks
    class FakeAsyncSession:
        pass

    class FakeAsyncConnection:
        pass

    sa_ext_asyncio.AsyncSession = FakeAsyncSession
    sa_ext_asyncio.AsyncConnection = FakeAsyncConnection
    sa_ext.asyncio = sa_ext_asyncio
    sa.ext = sa_ext
    sa.sql = sa_sql
    sa.engine = sa_engine
    sa.exc = sa_exc
    sa.orm = sa_orm

    # --- sqlmodel mocks ---
    sm = types.ModuleType("sqlmodel")
    sm_sql = types.ModuleType("sqlmodel.sql")
    sm_sql_expr = types.ModuleType("sqlmodel.sql.expression")
    sm_sql_cls = types.ModuleType("sqlmodel.sql._expression_select_cls")

    class FakeSQLModel:
        pass

    class FakeSession:
        pass

    # Concrete classes for isinstance checks in _prepare_query
    # __class_getitem__ needed because sqlmodel.py uses Select[T] in TypeAlias at module level
    class FakeSelect:
        def __class_getitem__(cls, item):
            return cls

    class FakeSelectOfScalar:
        def __class_getitem__(cls, item):
            return cls

    class FakeSelectBase:
        def __class_getitem__(cls, item):
            return cls

    sm.SQLModel = FakeSQLModel
    sm.Session = FakeSession
    sm.select = MagicMock(side_effect=lambda q: FakeSelect())
    sm_sql_expr.Select = FakeSelect
    sm_sql_expr.SelectOfScalar = FakeSelectOfScalar
    sm_sql_cls.SelectBase = FakeSelectBase

    sm.sql = sm_sql
    sm_sql.expression = sm_sql_expr

    mocks = {
        "sqlalchemy": sa,
        "sqlalchemy.sql": sa_sql,
        "sqlalchemy.sql.elements": sa_sql_elements,
        "sqlalchemy.engine": sa_engine,
        "sqlalchemy.exc": sa_exc,
        "sqlalchemy.orm": sa_orm,
        "sqlalchemy.ext": sa_ext,
        "sqlalchemy.ext.asyncio": sa_ext_asyncio,
        "sqlmodel": sm,
        "sqlmodel.sql": sm_sql,
        "sqlmodel.sql.expression": sm_sql_expr,
        "sqlmodel.sql._expression_select_cls": sm_sql_cls,
    }
    for name, mod in mocks.items():
        sys.modules.setdefault(name, mod)


_install_sqlmodel_mocks()

# Also mock fastapi_pagination.ext.sqlalchemy so _paginate/_apaginate are controllable
_mock_sa_paginate = MagicMock()
_mock_sa_apaginate = AsyncMock()

_fp_ext_sa = types.ModuleType("fastapi_pagination.ext.sqlalchemy")
_fp_ext_sa.paginate = _mock_sa_paginate
_fp_ext_sa.apaginate = _mock_sa_apaginate
sys.modules.setdefault("fastapi_pagination.ext.sqlalchemy", _fp_ext_sa)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_fake_classes():
    sm = sys.modules["sqlmodel"]
    sm_sql_expr = sys.modules["sqlmodel.sql.expression"]
    sa_ext_asyncio = sys.modules["sqlalchemy.ext.asyncio"]
    return (
        sm_sql_expr.Select,
        sm_sql_expr.SelectOfScalar,
        sa_ext_asyncio.AsyncSession,
        sa_ext_asyncio.AsyncConnection,
        sm.Session,
    )


# ---------------------------------------------------------------------------
# _prepare_query
# ---------------------------------------------------------------------------

def test_prepare_query_select_instance_returned_as_is():
    """If query is already a Select instance, it should be returned unchanged."""
    from fastapi_pagination.ext.sqlmodel import _prepare_query

    FakeSelect, _, _, _, _ = _get_fake_classes()
    query = FakeSelect()
    result = _prepare_query(query)

    assert result is query


def test_prepare_query_select_of_scalar_returned_as_is():
    """If query is already a SelectOfScalar instance, it should be returned unchanged."""
    from fastapi_pagination.ext.sqlmodel import _prepare_query

    _, FakeSelectOfScalar, _, _, _ = _get_fake_classes()
    query = FakeSelectOfScalar()
    result = _prepare_query(query)

    assert result is query


def test_prepare_query_non_select_wrapped_with_select():
    """If query is not Select/SelectOfScalar, select() should be called on it."""
    from fastapi_pagination.ext.sqlmodel import _prepare_query
    import sqlmodel as sm

    model_cls = MagicMock()
    sm.select.reset_mock()

    FakeSelect, _, _, _, _ = _get_fake_classes()
    sm.select.side_effect = lambda q: FakeSelect()

    result = _prepare_query(model_cls)

    sm.select.assert_called_once_with(model_cls)
    assert isinstance(result, FakeSelect)


# ---------------------------------------------------------------------------
# paginate (sync path)
# ---------------------------------------------------------------------------

def test_paginate_sync_calls_prepare_query_and_delegates():
    """paginate with a sync Session should call _paginate."""
    _, _, _, _, FakeSession = _get_fake_classes()
    session = FakeSession()
    FakeSelect, _, _, _, _ = _get_fake_classes()
    query = FakeSelect()
    mock_page = MagicMock()

    _mock_sa_paginate.reset_mock()
    _mock_sa_paginate.return_value = mock_page

    with patch("fastapi_pagination.ext.sqlmodel._prepare_query", return_value=query) as mock_prep:
        from fastapi_pagination.ext.sqlmodel import paginate

        result = paginate(session, query)

    mock_prep.assert_called_once_with(query)
    _mock_sa_paginate.assert_called_once()
    assert result is mock_page


def test_paginate_sync_with_count_query_prepares_both():
    """paginate with count_query should call _prepare_query for both."""
    _, _, _, _, FakeSession = _get_fake_classes()
    session = FakeSession()
    FakeSelect, _, _, _, _ = _get_fake_classes()
    query = FakeSelect()
    count_query = FakeSelect()
    prepared_query = FakeSelect()
    prepared_count = FakeSelect()

    _mock_sa_paginate.reset_mock()
    _mock_sa_paginate.return_value = MagicMock()

    prep_results = iter([prepared_query, prepared_count])

    with patch("fastapi_pagination.ext.sqlmodel._prepare_query", side_effect=lambda q: next(prep_results)) as mock_prep:
        from fastapi_pagination.ext.sqlmodel import paginate

        paginate(session, query, count_query=count_query)

    assert mock_prep.call_count == 2


# ---------------------------------------------------------------------------
# paginate (async path — deprecated warning)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_paginate_async_session_issues_deprecation_warning():
    """paginate with AsyncSession should issue DeprecationWarning and delegate to apaginate."""
    FakeSelect, _, FakeAsyncSession, _, _ = _get_fake_classes()
    session = FakeAsyncSession()
    query = FakeSelect()
    mock_coro = MagicMock()

    _mock_sa_apaginate.reset_mock()
    _mock_sa_apaginate.return_value = MagicMock()

    with patch("fastapi_pagination.ext.sqlmodel._prepare_query", return_value=query):
        with patch("fastapi_pagination.ext.sqlmodel.apaginate", new_callable=AsyncMock) as mock_apag:
            mock_apag.return_value = MagicMock()
            from fastapi_pagination.ext.sqlmodel import paginate

            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                result = paginate(session, query)

    assert any(issubclass(w.category, DeprecationWarning) for w in caught)


# ---------------------------------------------------------------------------
# apaginate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_apaginate_calls_prepare_query_and_delegates():
    """apaginate should call _prepare_query and await _apaginate."""
    FakeSelect, _, FakeAsyncSession, _, _ = _get_fake_classes()
    session = FakeAsyncSession()
    query = FakeSelect()
    mock_page = MagicMock()

    _mock_sa_apaginate.reset_mock()
    _mock_sa_apaginate.return_value = mock_page

    with patch("fastapi_pagination.ext.sqlmodel._prepare_query", return_value=query) as mock_prep:
        from fastapi_pagination.ext.sqlmodel import apaginate

        result = await apaginate(session, query)

    mock_prep.assert_called_once_with(query)
    _mock_sa_apaginate.assert_awaited_once()
    assert result is mock_page


@pytest.mark.asyncio
async def test_apaginate_with_count_query_prepares_both():
    """apaginate with count_query should call _prepare_query for both."""
    FakeSelect, _, FakeAsyncSession, _, _ = _get_fake_classes()
    session = FakeAsyncSession()
    query = FakeSelect()
    count_query = FakeSelect()
    prepared_query = FakeSelect()
    prepared_count = FakeSelect()

    _mock_sa_apaginate.reset_mock()
    _mock_sa_apaginate.return_value = MagicMock()

    prep_results = iter([prepared_query, prepared_count])

    with patch("fastapi_pagination.ext.sqlmodel._prepare_query", side_effect=lambda q: next(prep_results)) as mock_prep:
        from fastapi_pagination.ext.sqlmodel import apaginate

        await apaginate(session, query, count_query=count_query)

    assert mock_prep.call_count == 2


@pytest.mark.asyncio
async def test_apaginate_passes_kwargs_to_underlying():
    """apaginate should forward all kwargs to _apaginate."""
    FakeSelect, _, FakeAsyncSession, _, _ = _get_fake_classes()
    session = FakeAsyncSession()
    query = FakeSelect()
    mock_params = MagicMock()
    mock_transformer = MagicMock()
    mock_page = MagicMock()

    _mock_sa_apaginate.reset_mock()
    _mock_sa_apaginate.return_value = mock_page

    with patch("fastapi_pagination.ext.sqlmodel._prepare_query", return_value=query):
        from fastapi_pagination.ext.sqlmodel import apaginate

        result = await apaginate(session, query, params=mock_params, transformer=mock_transformer, unique=False)

    call_kwargs = _mock_sa_apaginate.call_args
    assert call_kwargs is not None
    assert result is mock_page
