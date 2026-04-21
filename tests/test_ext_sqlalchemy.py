"""Tests for fastapi_pagination/ext/sqlalchemy.py"""
from __future__ import annotations

import warnings
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import Column, Integer, String, func, select, text
from sqlalchemy.orm import DeclarativeBase, Query
from sqlalchemy.sql import CompoundSelect

from fastapi_pagination.bases import RawParams
from fastapi_pagination.ext.sqlalchemy import (
    _maybe_unique,
    _prepare_query,
    _prepare_query_for_cursor,
    _should_unwrap_scalars,
    _should_unwrap_scalars_for_query,
    _unwrap_items,
    _unwrap_params,
    create_count_query,
    create_count_query_from_text,
    create_paginate_query,
    create_paginate_query_from_text,
)


# ---------------------------------------------------------------------------
# Minimal ORM model for tests
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String)


# ---------------------------------------------------------------------------
# _prepare_query
# ---------------------------------------------------------------------------

def test_prepare_query_returns_none_for_none():
    result = _prepare_query(None)
    assert result is None


def test_prepare_query_returns_select_unchanged():
    q = select(Item)
    result = _prepare_query(q)
    assert result is q


def test_prepare_query_calls_statement_20_when_present():
    q = select(Item)
    converted = select(Item).where(Item.id == 1)
    mock_query = MagicMock()
    mock_query._statement_20 = MagicMock(return_value=converted)
    result = _prepare_query(mock_query)
    assert result is converted


def test_prepare_query_ignores_missing_statement_20():
    q = select(Item)
    # No _statement_20 attribute, should just return q
    result = _prepare_query(q)
    assert result is q


# ---------------------------------------------------------------------------
# _prepare_query_for_cursor
# ---------------------------------------------------------------------------

def test_prepare_query_for_cursor_returns_select_unchanged():
    q = select(Item)
    result = _prepare_query_for_cursor(q)
    assert result is q


def test_prepare_query_for_cursor_wraps_compound_select():
    q1 = select(Item)
    q2 = select(Item)
    compound = q1.union(q2)
    assert isinstance(compound, CompoundSelect)
    result = _prepare_query_for_cursor(compound)
    # Result should be a Select wrapping a subquery
    assert hasattr(result, "froms")


def test_prepare_query_for_cursor_compound_with_ordering():
    q1 = select(Item).order_by(Item.id)
    q2 = select(Item)
    compound = q1.union(q2)
    result = _prepare_query_for_cursor(compound)
    assert hasattr(result, "froms")


# ---------------------------------------------------------------------------
# _should_unwrap_scalars_for_query
# ---------------------------------------------------------------------------

def test_should_unwrap_scalars_for_query_multiple_cols_returns_false():
    q = select(Item.id, Item.name)
    result = _should_unwrap_scalars_for_query(q)
    assert result is False


def test_should_unwrap_scalars_for_query_single_model_entity_returns_true():
    q = select(Item)
    result = _should_unwrap_scalars_for_query(q)
    assert result is True


def test_should_unwrap_scalars_for_query_single_column_returns_false():
    q = select(Item.id)
    result = _should_unwrap_scalars_for_query(q)
    assert result is False


# ---------------------------------------------------------------------------
# _should_unwrap_scalars
# ---------------------------------------------------------------------------

def test_should_unwrap_scalars_non_selectable_returns_false():
    result = _should_unwrap_scalars("not a query")
    assert result is False


def test_should_unwrap_scalars_compound_select_returns_false():
    q1 = select(Item)
    q2 = select(Item)
    compound = q1.union(q2)
    result = _should_unwrap_scalars(compound)
    assert result is False


def test_should_unwrap_scalars_single_model_returns_true():
    q = select(Item)
    result = _should_unwrap_scalars(q)
    assert result is True


def test_should_unwrap_scalars_single_column_returns_false():
    q = select(Item.id)
    result = _should_unwrap_scalars(q)
    assert result is False


def test_should_unwrap_scalars_multiple_columns_returns_false():
    q = select(Item.id, Item.name)
    result = _should_unwrap_scalars(q)
    assert result is False


def test_should_unwrap_scalars_text_clause_returns_true():
    # TextClause has no column_descriptions -> AttributeError -> returns True
    q = text("SELECT * FROM t")
    result = _should_unwrap_scalars(q)
    assert result is True


# ---------------------------------------------------------------------------
# _unwrap_params
# ---------------------------------------------------------------------------

def test_unwrap_params_with_raw_params():
    raw = RawParams(limit=10, offset=20)
    result = _unwrap_params(raw)
    assert result is raw


def test_unwrap_params_with_abstract_params():
    from fastapi_pagination.default import Params
    params = Params(page=2, size=10)
    result = _unwrap_params(params)
    assert isinstance(result, RawParams)
    assert result.limit == 10
    assert result.offset == 10  # page=2 means offset = size*(page-1) = 10*1 = 10


# ---------------------------------------------------------------------------
# create_paginate_query_from_text (deprecated)
# ---------------------------------------------------------------------------

def test_create_paginate_query_from_text_basic():
    raw = RawParams(limit=10, offset=5)
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        result = create_paginate_query_from_text("SELECT * FROM t", raw)
    assert "LIMIT 10" in result
    assert "OFFSET 5" in result


def test_create_paginate_query_from_text_emits_deprecation():
    raw = RawParams(limit=10, offset=0)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        create_paginate_query_from_text("SELECT * FROM t", raw)
    assert len(w) > 0


# ---------------------------------------------------------------------------
# create_count_query_from_text (deprecated)
# ---------------------------------------------------------------------------

def test_create_count_query_from_text_basic():
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        result = create_count_query_from_text("SELECT * FROM t")
    assert "count" in result.lower()
    assert "SELECT * FROM t" in result


def test_create_count_query_from_text_emits_deprecation():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        create_count_query_from_text("SELECT * FROM t")
    assert len(w) > 0


# ---------------------------------------------------------------------------
# create_paginate_query
# ---------------------------------------------------------------------------

def test_create_paginate_query_with_text_clause():
    t = text("SELECT * FROM t")
    raw = RawParams(limit=5, offset=2)
    result = create_paginate_query(t, raw)
    # Should return a text with LIMIT/OFFSET applied
    assert "LIMIT 5" in result.text
    assert "OFFSET 2" in result.text


def test_create_paginate_query_with_select():
    q = select(Item)
    raw = RawParams(limit=10, offset=0)
    result = create_paginate_query(q, raw)
    compiled = str(result.compile(compile_kwargs={"literal_binds": True}))
    assert "LIMIT" in compiled


def test_create_paginate_query_with_params_object():
    from fastapi_pagination.default import Params
    q = select(Item)
    params = Params(page=1, size=15)
    result = create_paginate_query(q, params)
    compiled = str(result.compile(compile_kwargs={"literal_binds": True}))
    assert "LIMIT" in compiled


# ---------------------------------------------------------------------------
# create_count_query
# ---------------------------------------------------------------------------

def test_create_count_query_with_text_clause():
    t = text("SELECT * FROM t")
    result = create_count_query(t)
    assert "count" in result.text.lower()


def test_create_count_query_with_select_use_subquery_true():
    q = select(Item)
    result = create_count_query(q, use_subquery=True)
    compiled = str(result.compile())
    assert "count" in compiled.lower()


def test_create_count_query_with_select_use_subquery_false():
    q = select(Item)
    result = create_count_query(q, use_subquery=False)
    compiled = str(result.compile())
    assert "count" in compiled.lower()


def test_create_count_query_from_statement_recurses():
    # FromStatement wraps another query - count should recurse into element
    try:
        from sqlalchemy.orm import FromStatement
    except ImportError:
        pytest.skip("FromStatement not available")
    inner_q = select(Item)
    from_stmt = FromStatement([Item], inner_q)
    result = create_count_query(from_stmt)
    compiled = str(result.compile())
    assert "count" in compiled.lower()


# ---------------------------------------------------------------------------
# _maybe_unique
# ---------------------------------------------------------------------------

def test_maybe_unique_with_unique_false():
    mock_result = MagicMock()
    mock_result.all.return_value = [1, 2, 3]
    result = _maybe_unique(mock_result, unique=False)
    assert result == [1, 2, 3]
    mock_result.unique.assert_not_called()
    mock_result.all.assert_called_once()


def test_maybe_unique_with_unique_true():
    unique_mock = MagicMock()
    unique_mock.all.return_value = [1, 2]
    mock_result = MagicMock()
    mock_result.unique.return_value = unique_mock
    result = _maybe_unique(mock_result, unique=True)
    assert result == [1, 2]
    mock_result.unique.assert_called_once()


# ---------------------------------------------------------------------------
# _unwrap_items
# ---------------------------------------------------------------------------

def test_unwrap_items_legacy_mode_with_text_clause():
    items = [(1,), (2,), (3,)]
    q = text("SELECT id FROM t")
    result = _unwrap_items(items, q)
    assert list(result) == [1, 2, 3]


def test_unwrap_items_no_unwrap_mode():
    items = [(1, "a"), (2, "b")]
    q = select(Item.id, Item.name)
    result = _unwrap_items(items, q, unwrap_mode="no-unwrap")
    assert list(result) == [(1, "a"), (2, "b")]


def test_unwrap_items_unwrap_mode_force():
    items = [(1,), (2,)]
    q = select(Item.id)
    result = _unwrap_items(items, q, unwrap_mode="unwrap")
    assert list(result) == [1, 2]


def test_unwrap_items_auto_mode_single_model():
    # select(Item) - should unwrap because _should_unwrap_scalars returns True
    items = [MagicMock(), MagicMock()]
    items[0].__len__ = lambda self: 1
    items[0].__getitem__ = lambda self, i: "item_0"
    items[1].__len__ = lambda self: 1
    items[1].__getitem__ = lambda self, i: "item_1"

    q = select(Item)
    result = _unwrap_items(items, q, unwrap_mode="auto")
    # auto mode with select(Item) should trigger force_unwrap
    assert len(result) == 2


def test_unwrap_items_auto_mode_multiple_cols_no_unwrap():
    items = [(1, "a"), (2, "b")]
    q = select(Item.id, Item.name)
    result = _unwrap_items(items, q, unwrap_mode="auto")
    # Multiple columns - no unwrap
    assert list(result) == [(1, "a"), (2, "b")]


def test_unwrap_items_legacy_explicit_mode():
    items = [(10,), (20,)]
    q = select(Item.id)
    result = _unwrap_items(items, q, unwrap_mode="legacy")
    assert list(result) == [10, 20]


# ---------------------------------------------------------------------------
# paginate / apaginate (integration tests using mocked sessions)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_apaginate_basic():
    """Test apaginate with a mocked AsyncSession."""
    from unittest.mock import AsyncMock, MagicMock

    from fastapi_pagination.api import set_page, set_params
    from fastapi_pagination.default import Page, Params
    from fastapi_pagination.ext.sqlalchemy import apaginate

    mock_session = AsyncMock()
    mock_session.scalar = AsyncMock(return_value=3)

    # Use (id,) tuples - Row-like results that are subscriptable
    rows = [(1,), (2,), (3,)]
    execute_result = MagicMock()
    execute_result.unique.return_value = execute_result
    execute_result.all.return_value = rows
    mock_session.execute = AsyncMock(return_value=execute_result)

    params = Params(page=1, size=10)
    # Use select(Item.id) to avoid scalar unwrapping complexity
    q = select(Item.id)

    with set_page(Page), set_params(params):
        result = await apaginate(mock_session, q)

    assert result is not None


@pytest.mark.asyncio
async def test_apaginate_with_explicit_params():
    """Test apaginate with explicitly passed params."""
    from unittest.mock import AsyncMock, MagicMock

    from fastapi_pagination.api import set_page
    from fastapi_pagination.default import Page, Params
    from fastapi_pagination.ext.sqlalchemy import apaginate

    mock_session = AsyncMock()
    mock_session.scalar = AsyncMock(return_value=0)

    execute_result = MagicMock()
    execute_result.unique.return_value = execute_result
    execute_result.all.return_value = []
    mock_session.execute = AsyncMock(return_value=execute_result)

    params = Params(page=1, size=5)
    q = select(Item.id)

    with set_page(Page):
        result = await apaginate(mock_session, q, params=params)

    assert result is not None


def test_paginate_sync_basic():
    """Test synchronous paginate with a mocked Session."""
    from unittest.mock import MagicMock

    from fastapi_pagination.api import set_page, set_params
    from fastapi_pagination.default import Page, Params
    from fastapi_pagination.ext.sqlalchemy import paginate

    mock_session = MagicMock(spec=["execute", "scalar", "bind"])
    mock_session.scalar.return_value = 2

    rows = [(1,), (2,)]
    execute_result = MagicMock()
    execute_result.unique.return_value = execute_result
    execute_result.all.return_value = rows
    mock_session.execute.return_value = execute_result

    params = Params(page=1, size=10)
    q = select(Item.id)

    with set_page(Page), set_params(params):
        result = paginate(mock_session, q)

    assert result is not None


def test_new_paginate_sign_prepares_queries():
    from fastapi_pagination.ext.sqlalchemy import _new_paginate_sign

    conn = MagicMock()
    q = select(Item)
    count_q = select(func.count()).select_from(q.subquery())

    result = _new_paginate_sign(conn, q, count_query=count_q)
    # Returns a 10-tuple
    assert len(result) == 10
    assert result[2] is conn


def test_old_paginate_sign_raises_when_no_session():
    from fastapi_pagination.ext.sqlalchemy import _old_paginate_sign

    mock_query = MagicMock(spec=Query)
    mock_query.session = None

    with pytest.raises(ValueError, match="query.session is None"):
        _old_paginate_sign(mock_query)


def test_old_paginate_sign_returns_session_and_prepared_query():
    from fastapi_pagination.ext.sqlalchemy import _old_paginate_sign

    mock_session = MagicMock()
    mock_query = MagicMock(spec=Query)
    mock_query.session = mock_session
    prepared = select(Item)
    mock_query._statement_20 = MagicMock(return_value=prepared)

    result = _old_paginate_sign(mock_query)
    assert len(result) == 10
    assert result[0] is prepared
    assert result[2] is mock_session
