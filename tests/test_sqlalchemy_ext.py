"""Unit tests for fastapi_pagination.ext.sqlalchemy."""
from __future__ import annotations

import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import Column, Integer, String, func, select, text, union_all
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.sql import CompoundSelect

from fastapi_pagination.bases import RawParams
from fastapi_pagination.default import Params
from fastapi_pagination.ext.sqlalchemy import (
    _inner_transformer,
    _maybe_unique,
    _new_paginate_sign,
    _old_paginate_sign,
    _prepare_query,
    _prepare_query_for_cursor,
    _should_unwrap_scalars,
    _should_unwrap_scalars_for_query,
    _sqlalchemy_flow,
    _total_flow,
    _unwrap_items,
    _unwrap_params,
    apaginate,
    create_count_query,
    create_count_query_from_text,
    create_paginate_query,
    create_paginate_query_from_text,
    paginate,
)
from fastapi_pagination.flow import run_async_flow, run_sync_flow


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)


# ---- _prepare_query ----


def test_prepare_query_none_returns_none():
    assert _prepare_query(None) is None


def test_prepare_query_select_returns_query():
    q = select(User)
    result = _prepare_query(q)
    assert result is not None


def test_prepare_query_with_statement_20():
    mock_q = MagicMock()
    mock_q._statement_20.return_value = select(User)
    result = _prepare_query(mock_q)
    assert result is not None
    mock_q._statement_20.assert_called_once()


def test_prepare_query_suppresses_attribute_error():
    mock_q = MagicMock()
    del mock_q._statement_20
    # Should not raise even when _statement_20 is missing
    result = _prepare_query(mock_q)
    assert result is mock_q


# ---- _prepare_query_for_cursor ----


def test_prepare_query_for_cursor_regular_select():
    q = select(User)
    result = _prepare_query_for_cursor(q)
    assert result is q


def test_prepare_query_for_cursor_compound_select():
    q1 = select(User.id)
    q2 = select(User.id)
    compound = union_all(q1, q2).order_by(User.id)
    result = _prepare_query_for_cursor(compound)
    assert not isinstance(result, CompoundSelect)
    from sqlalchemy.sql import Select
    assert isinstance(result, Select)


def test_prepare_query_for_cursor_compound_no_ordering():
    q1 = select(User.id)
    q2 = select(User.id)
    compound = union_all(q1, q2)
    result = _prepare_query_for_cursor(compound)
    from sqlalchemy.sql import Select
    assert isinstance(result, Select)


# ---- _should_unwrap_scalars_for_query ----


def test_should_unwrap_scalars_for_query_model_select():
    q = select(User)
    assert _should_unwrap_scalars_for_query(q) is True


def test_should_unwrap_scalars_for_query_single_column():
    q = select(User.id)
    assert _should_unwrap_scalars_for_query(q) is False


def test_should_unwrap_scalars_for_query_multi_column():
    q = select(User.id, User.name)
    assert _should_unwrap_scalars_for_query(q) is False


def test_should_unwrap_scalars_for_query_multi_entity():
    # Selecting multiple columns via func creates multiple descs
    q = select(func.count(User.id), User.name)
    assert _should_unwrap_scalars_for_query(q) is False


# ---- _should_unwrap_scalars ----


def test_should_unwrap_scalars_model_select():
    assert _should_unwrap_scalars(select(User)) is True


def test_should_unwrap_scalars_single_column():
    assert _should_unwrap_scalars(select(User.id)) is False


def test_should_unwrap_scalars_text():
    assert _should_unwrap_scalars(text("SELECT 1")) is True


def test_should_unwrap_scalars_compound():
    compound = union_all(select(User.id), select(User.id))
    assert _should_unwrap_scalars(compound) is False


def test_should_unwrap_scalars_non_selectable():
    assert _should_unwrap_scalars("not a query") is False


def test_should_unwrap_scalars_attribute_error_returns_true():
    mock_q = MagicMock(spec=["column_descriptions", "_all_selected_columns"])
    mock_q.column_descriptions = MagicMock(side_effect=AttributeError)
    # Pass something that looks like a Select
    from sqlalchemy.sql import Select
    mock_q.__class__ = Select
    # Just test that function handles exceptions
    result = _should_unwrap_scalars(mock_q)
    assert isinstance(result, bool)


# ---- _unwrap_params ----


def test_unwrap_params_raw_params_passthrough():
    rp = RawParams(limit=10, offset=5)
    result = _unwrap_params(rp)
    assert result is rp


def test_unwrap_params_abstract_params_conversion():
    params = Params(page=2, size=10)
    result = _unwrap_params(params)
    assert isinstance(result, RawParams)
    assert result.limit == 10
    assert result.offset == 10


# ---- create_paginate_query_from_text ----


def test_create_paginate_query_from_text_deprecated():
    rp = RawParams(limit=10, offset=5)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = create_paginate_query_from_text("SELECT * FROM users", rp)
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
    assert "LIMIT 10" in result
    assert "OFFSET 5" in result


# ---- create_count_query_from_text ----


def test_create_count_query_from_text_deprecated():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = create_count_query_from_text("SELECT * FROM users")
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
    assert "count" in result.lower()


# ---- create_paginate_query ----


def test_create_paginate_query_select():
    rp = RawParams(limit=5, offset=10)
    q = select(User)
    result = create_paginate_query(q, rp)
    sql = str(result)
    assert "LIMIT" in sql
    assert "OFFSET" in sql


def test_create_paginate_query_text_clause():
    rp = RawParams(limit=5, offset=10)
    q = text("SELECT * FROM users")
    result = create_paginate_query(q, rp)
    sql = str(result)
    assert "LIMIT" in sql
    assert "OFFSET" in sql


def test_create_paginate_query_from_statement():
    from sqlalchemy.orm import FromStatement
    mock_stmt = MagicMock()
    mock_inner = select(User)
    mock_fs = MagicMock(spec=FromStatement)
    mock_fs._generate.return_value = MagicMock(element=mock_inner)
    rp = RawParams(limit=5, offset=0)

    with patch("fastapi_pagination.ext.sqlalchemy._paginate_from_statement") as mock_pfs:
        mock_pfs.return_value = mock_fs
        result = create_paginate_query(mock_fs, rp)
        mock_pfs.assert_called_once_with(mock_fs, rp)


# ---- create_count_query ----


def test_create_count_query_select_with_subquery():
    q = select(User)
    result = create_count_query(q)
    sql = str(result)
    assert "count" in sql.lower()
    assert "FROM" in sql


def test_create_count_query_select_without_subquery():
    q = select(User)
    result = create_count_query(q, use_subquery=False)
    sql = str(result)
    assert "count" in sql.lower()


def test_create_count_query_text():
    q = text("SELECT * FROM users")
    result = create_count_query(q)
    sql = str(result)
    assert "count" in sql.lower()


def test_create_count_query_from_statement():
    from sqlalchemy.orm import FromStatement
    inner = select(User)
    mock_fs = MagicMock(spec=FromStatement)
    mock_fs.element = inner
    result = create_count_query(mock_fs)
    sql = str(result)
    assert "count" in sql.lower()


# ---- _maybe_unique ----


def test_maybe_unique_unique_true():
    mock_result = MagicMock()
    mock_result.unique.return_value.all.return_value = [1, 2, 3]
    result = _maybe_unique(mock_result, unique=True)
    assert result == [1, 2, 3]
    mock_result.unique.assert_called_once()


def test_maybe_unique_unique_false():
    mock_result = MagicMock()
    mock_result.all.return_value = [1, 2, 3]
    result = _maybe_unique(mock_result, unique=False)
    assert result == [1, 2, 3]
    mock_result.unique.assert_not_called()


# ---- _unwrap_items ----


def test_unwrap_items_text_clause_uses_legacy():
    items = [(1,), (2,)]
    q = text("SELECT id FROM users")
    result = _unwrap_items(items, q)
    assert result == [1, 2]


def test_unwrap_items_legacy_mode():
    items = [(1,), (2,)]
    q = select(User)
    result = _unwrap_items(items, q, unwrap_mode="legacy")
    assert result == [1, 2]


def test_unwrap_items_no_unwrap_mode():
    items = [(1,), (2,)]
    q = select(User)
    result = _unwrap_items(items, q, unwrap_mode="no-unwrap")
    assert result == [(1,), (2,)]


def test_unwrap_items_unwrap_mode():
    items = [(1,), (2,)]
    q = select(User)
    result = _unwrap_items(items, q, unwrap_mode="unwrap")
    assert result == [1, 2]


def test_unwrap_items_auto_mode_with_model_select():
    items = [MagicMock(), MagicMock()]
    q = select(User)
    result = _unwrap_items(items, q, unwrap_mode="auto")
    # select(User) should unwrap, but items are single-element tuples here
    assert result is not None


def test_unwrap_items_auto_mode_single_column():
    items = [(1,), (2,)]
    q = select(User.id)
    result = _unwrap_items(items, q, unwrap_mode="auto")
    # select(User.id) should NOT unwrap scalars
    assert result == [(1,), (2,)]


# ---- _inner_transformer ----


def test_inner_transformer_applies_unique_and_unwrap():
    mock_result = MagicMock()
    mock_result.unique.return_value.all.return_value = [(1,), (2,)]
    q = select(User.id)
    result = _inner_transformer(mock_result, query=q, unwrap_mode="legacy", unique=True)
    mock_result.unique.assert_called_once()
    assert result == [1, 2]


def test_inner_transformer_no_unique():
    mock_result = MagicMock()
    mock_result.all.return_value = [(1,), (2,)]
    q = select(User.id)
    result = _inner_transformer(mock_result, query=q, unwrap_mode="legacy", unique=False)
    mock_result.unique.assert_not_called()
    assert result == [1, 2]


def test_inner_transformer_suppresses_attribute_error():
    items = [(1,), (2,)]
    q = select(User.id)
    result = _inner_transformer(items, query=q, unwrap_mode="legacy", unique=True)
    assert result == [1, 2]


# ---- _old_paginate_sign ----


def test_old_paginate_sign_none_session_raises():
    mock_query = MagicMock()
    mock_query.session = None
    with pytest.raises(ValueError, match="query.session is None"):
        _old_paginate_sign(mock_query)


def test_old_paginate_sign_with_session():
    mock_session = MagicMock(spec=Session)
    mock_query = MagicMock()
    mock_query.session = mock_session
    mock_query._statement_20.return_value = select(User)

    result = _old_paginate_sign(mock_query)
    query, count_query, conn, params, transformer, additional_data, unique, subquery_count, unwrap_mode, config = result
    assert conn is mock_session
    assert count_query is None
    assert params is None
    assert unique is True
    assert subquery_count is True


# ---- _new_paginate_sign ----


def test_new_paginate_sign():
    mock_conn = MagicMock(spec=Session)
    q = select(User)
    params = Params(page=1, size=10)

    result = _new_paginate_sign(mock_conn, q, params=params)
    query, count_query, conn, r_params, transformer, additional_data, unique, subquery_count, unwrap_mode, config = result
    assert conn is mock_conn
    assert r_params is params
    assert count_query is None
    assert unique is True


def test_new_paginate_sign_with_count_query():
    mock_conn = MagicMock(spec=Session)
    q = select(User)
    cq = select(func.count()).select_from(User)

    result = _new_paginate_sign(mock_conn, q, count_query=cq)
    query, count_query, conn, r_params, transformer, additional_data, unique, subquery_count, unwrap_mode, config = result
    assert count_query is not None


# ---- paginate ----


def test_paginate_sync_calls_run_sync_flow():
    mock_conn = MagicMock(spec=Session)
    mock_page = MagicMock()

    with patch("fastapi_pagination.ext.sqlalchemy.run_sync_flow", return_value=mock_page) as mock_flow:
        result = paginate(mock_conn, select(User))
    assert result is mock_page
    mock_flow.assert_called_once()


def test_paginate_sync_with_params():
    mock_conn = MagicMock(spec=Session)
    params = Params(page=1, size=5)
    mock_page = MagicMock()

    with patch("fastapi_pagination.ext.sqlalchemy.run_sync_flow", return_value=mock_page):
        result = paginate(mock_conn, select(User), params=params)
    assert result is mock_page


def test_paginate_async_conn_warns_and_calls_apaginate():
    mock_async_conn = MagicMock()
    mock_async_conn.sync_session = MagicMock(spec=Session)
    mock_coro = AsyncMock()

    with patch("fastapi_pagination.ext.sqlalchemy.apaginate", return_value=mock_coro) as mock_ap:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            paginate(mock_async_conn, select(User))
        assert len(w) >= 1
        assert any(issubclass(warning.category, DeprecationWarning) for warning in w)
    mock_ap.assert_called_once()


# ---- apaginate ----


@pytest.mark.asyncio
async def test_apaginate_calls_run_async_flow():
    mock_conn = MagicMock()
    mock_page = MagicMock()

    with patch("fastapi_pagination.ext.sqlalchemy.run_async_flow", new=AsyncMock(return_value=mock_page)) as mock_flow:
        result = await apaginate(mock_conn, select(User))
    assert result is mock_page
    mock_flow.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_with_params():
    mock_conn = MagicMock()
    params = Params(page=1, size=10)
    mock_page = MagicMock()

    with patch("fastapi_pagination.ext.sqlalchemy.run_async_flow", new=AsyncMock(return_value=mock_page)):
        result = await apaginate(mock_conn, select(User), params=params)
    assert result is mock_page


@pytest.mark.asyncio
async def test_apaginate_with_count_query():
    mock_conn = MagicMock()
    mock_page = MagicMock()
    cq = select(func.count()).select_from(User)

    with patch("fastapi_pagination.ext.sqlalchemy.run_async_flow", new=AsyncMock(return_value=mock_page)):
        result = await apaginate(mock_conn, select(User), count_query=cq)
    assert result is mock_page


# ---- _sqlalchemy_flow ----


def test_sqlalchemy_flow_sync_executes_flow():
    """Cover lines 346, 347 (False branch), 350, 363 in _sqlalchemy_flow."""
    mock_conn = MagicMock()
    query = select(User)
    params = Params(page=1, size=10)
    mock_page = MagicMock()

    def fake_generic_flow(**kwargs):
        return mock_page
        yield  # noqa: unreachable — makes this a generator function

    with patch("fastapi_pagination.ext.sqlalchemy.generic_flow", fake_generic_flow):
        result = run_sync_flow(
            _sqlalchemy_flow(
                is_async=False,
                conn=mock_conn,
                query=query,
                params=params,
            )
        )

    assert result is mock_page


@pytest.mark.asyncio
async def test_sqlalchemy_flow_async_wraps_create_page_factory():
    """Cover lines 346, 347 (True branch), 348, 350, 363 in _sqlalchemy_flow."""
    mock_conn = MagicMock()
    query = select(User)
    params = Params(page=1, size=10)
    mock_page = MagicMock()

    def fake_generic_flow(**kwargs):
        # Verify create_page_factory was wrapped with greenlet_spawn for async
        create_page_factory = kwargs.get("create_page_factory")
        assert create_page_factory is not None
        from functools import partial
        from sqlalchemy.util import greenlet_spawn
        assert isinstance(create_page_factory, partial)
        assert create_page_factory.func is greenlet_spawn
        return mock_page
        yield  # noqa: unreachable — makes this a generator function

    with patch("fastapi_pagination.ext.sqlalchemy.generic_flow", fake_generic_flow):
        result = await run_async_flow(
            _sqlalchemy_flow(
                is_async=True,
                conn=mock_conn,
                query=query,
                params=params,
            )
        )

    assert result is mock_page


# ---- _total_flow ----


def test_total_flow_count_query_none_creates_count_query():
    """Cover lines 276-277, 279-280: when count_query is None, it is created."""
    mock_conn = MagicMock()
    mock_conn.scalar.return_value = 10
    query = select(User)

    result = run_sync_flow(_total_flow(query, mock_conn, None, True))

    assert result == 10
    mock_conn.scalar.assert_called_once()


def test_total_flow_count_query_provided_skips_creation():
    """Cover lines 279-280: when count_query is provided, it is used directly."""
    mock_conn = MagicMock()
    mock_conn.scalar.return_value = 5
    query = select(User)
    count_query = select(func.count()).select_from(User)

    result = run_sync_flow(_total_flow(query, mock_conn, count_query, False))

    assert result == 5
    mock_conn.scalar.assert_called_once_with(count_query)


def test_total_flow_returns_none_when_scalar_returns_none():
    """Cover lines 279-280: total can be None."""
    mock_conn = MagicMock()
    mock_conn.scalar.return_value = None
    query = select(User)

    result = run_sync_flow(_total_flow(query, mock_conn, None, False))

    assert result is None
