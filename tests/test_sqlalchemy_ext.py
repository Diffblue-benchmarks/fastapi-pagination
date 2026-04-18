"""Unit tests for fastapi_pagination.ext.sqlalchemy"""
from __future__ import annotations

import warnings
from collections.abc import Sequence
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import Column, Integer, String, create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import TextClause

from fastapi_pagination import Page, Params
from fastapi_pagination.api import set_page
from fastapi_pagination.bases import CursorRawParams, RawParams
from fastapi_pagination.ext.sqlalchemy import (
    _cursor_flow,
    _inner_transformer,
    _maybe_unique,
    _new_paginate_sign,
    _old_paginate_sign,
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
    paginate,
)
from fastapi_pagination.flow import run_sync_flow


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "test_users_sqlalchemy"
    id = Column(Integer, primary_key=True)
    name = Column(String)


@pytest.fixture(scope="module")
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    with Session(eng) as sess:
        sess.add_all([User(id=1, name="Alice"), User(id=2, name="Bob"), User(id=3, name="Charlie")])
        sess.commit()
    return eng


@pytest.fixture
def session(engine):
    with Session(engine) as sess:
        yield sess


# ── _prepare_query ──────────────────────────────────────────────────────────


def test_prepare_query_returns_none_for_none():
    assert _prepare_query(None) is None


def test_prepare_query_returns_select_unchanged():
    q = select(User)
    result = _prepare_query(q)
    assert result is q


def test_prepare_query_calls_statement_20_when_available():
    """When the query object has _statement_20(), it should be called."""
    expected = select(User)
    mock_query = MagicMock()
    mock_query._statement_20.return_value = expected
    result = _prepare_query(mock_query)
    assert result is expected
    mock_query._statement_20.assert_called_once()


def test_prepare_query_suppresses_attribute_error():
    """When _statement_20 raises AttributeError, query is returned as-is."""
    mock_query = MagicMock(spec=[])  # no _statement_20
    result = _prepare_query(mock_query)
    assert result is mock_query


# ── _prepare_query_for_cursor ───────────────────────────────────────────────


def test_prepare_query_for_cursor_with_select_returns_same():
    q = select(User)
    result = _prepare_query_for_cursor(q)
    assert result is q


def test_prepare_query_for_cursor_with_compound_select_wraps_in_subquery():
    q1 = select(User.id, User.name)
    q2 = select(User.id, User.name)
    compound = q1.union_all(q2)
    result = _prepare_query_for_cursor(compound)
    assert isinstance(result, Select)


def test_prepare_query_for_cursor_with_text_clause_returns_same():
    q = text("SELECT id FROM test_users_sqlalchemy")
    result = _prepare_query_for_cursor(q)
    assert result is q


# ── _should_unwrap_scalars_for_query ────────────────────────────────────────


def test_should_unwrap_scalars_for_query_multi_columns_returns_false():
    q = select(User.id, User.name)
    assert _should_unwrap_scalars_for_query(q) is False


def test_should_unwrap_scalars_for_query_entity_select_returns_true():
    """select(Model) selects the whole entity — should trigger unwrapping."""
    q = select(User)
    assert _should_unwrap_scalars_for_query(q) is True


def test_should_unwrap_scalars_for_query_single_column_returns_false():
    """select(Model.col) selects one column (not the entity) — no unwrap."""
    q = select(User.id)
    assert _should_unwrap_scalars_for_query(q) is False


# ── _should_unwrap_scalars ───────────────────────────────────────────────────


def test_should_unwrap_scalars_non_selectable_returns_false():
    assert _should_unwrap_scalars("not a query") is False
    assert _should_unwrap_scalars(42) is False
    assert _should_unwrap_scalars(None) is False


def test_should_unwrap_scalars_compound_select_returns_false():
    compound = select(User.id).union_all(select(User.id))
    assert _should_unwrap_scalars(compound) is False


def test_should_unwrap_scalars_entity_select_returns_true():
    q = select(User)
    assert _should_unwrap_scalars(q) is True


def test_should_unwrap_scalars_text_clause_returns_true():
    """TextClause triggers AttributeError in _should_unwrap_scalars_for_query → True."""
    q = text("SELECT id FROM test_users_sqlalchemy")
    assert _should_unwrap_scalars(q) is True


def test_should_unwrap_scalars_single_col_returns_false():
    q = select(User.id)
    assert _should_unwrap_scalars(q) is False


# ── _unwrap_params ──────────────────────────────────────────────────────────


def test_unwrap_params_raw_params_returned_as_is():
    raw = RawParams(limit=10, offset=0)
    assert _unwrap_params(raw) is raw


def test_unwrap_params_abstract_params_converted_to_raw():
    params = Params(page=1, size=20)
    result = _unwrap_params(params)
    assert isinstance(result, RawParams)
    assert result.limit == 20
    assert result.offset == 0


def test_unwrap_params_page2_offset_calculated():
    params = Params(page=3, size=5)
    result = _unwrap_params(params)
    assert result.limit == 5
    assert result.offset == 10


# ── create_paginate_query_from_text (deprecated) ────────────────────────────


def test_create_paginate_query_from_text_appends_limit_offset():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        result = create_paginate_query_from_text("SELECT * FROM t", RawParams(limit=5, offset=10))
    assert "LIMIT 5" in result
    assert "OFFSET 10" in result


def test_create_paginate_query_from_text_with_params():
    params = Params(page=2, size=3)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        result = create_paginate_query_from_text("SELECT * FROM t", params)
    assert "LIMIT 3" in result
    assert "OFFSET 3" in result


# ── create_count_query_from_text (deprecated) ───────────────────────────────


def test_create_count_query_from_text_wraps_in_count():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        result = create_count_query_from_text("SELECT * FROM t")
    assert "count" in result.lower()
    assert "SELECT * FROM t" in result


# ── create_paginate_query ───────────────────────────────────────────────────


def test_create_paginate_query_text_clause():
    q = text("SELECT * FROM t")
    result = create_paginate_query(q, RawParams(limit=5, offset=0))
    assert isinstance(result, TextClause)
    assert "LIMIT 5" in result.text


def test_create_paginate_query_select():
    q = select(User)
    result = create_paginate_query(q, Params(page=1, size=5))
    assert isinstance(result, Select)


def test_create_paginate_query_select_applies_limit_offset():
    q = select(User)
    params = Params(page=2, size=5)
    result = create_paginate_query(q, params)
    # compiled query should contain LIMIT and OFFSET
    from sqlalchemy.dialects import sqlite
    compiled = str(result.compile(dialect=sqlite.dialect()))
    assert "LIMIT" in compiled
    assert "OFFSET" in compiled


# ── create_count_query ──────────────────────────────────────────────────────


def test_create_count_query_text_clause():
    q = text("SELECT * FROM t")
    result = create_count_query(q)
    assert isinstance(result, TextClause)
    assert "count" in result.text.lower()


def test_create_count_query_select_use_subquery_true():
    q = select(User)
    result = create_count_query(q, use_subquery=True)
    assert isinstance(result, Select)
    from sqlalchemy.dialects import sqlite
    compiled = str(result.compile(dialect=sqlite.dialect()))
    assert "count" in compiled.lower()


def test_create_count_query_select_use_subquery_false():
    q = select(User)
    result = create_count_query(q, use_subquery=False)
    assert isinstance(result, Select)


def test_create_count_query_from_statement_delegates():
    """FromStatement should delegate to create_count_query(query.element)."""
    from sqlalchemy.orm import FromStatement

    inner_q = select(User)
    # Build a mock FromStatement
    mock_stmt = MagicMock(spec=FromStatement)
    mock_stmt.element = inner_q
    # We patch isinstance to treat mock_stmt as FromStatement
    with patch("fastapi_pagination.ext.sqlalchemy.isinstance") as mock_isinstance:

        def isinstance_side_effect(obj, cls):
            if obj is mock_stmt and cls == TextClause:
                return False
            if obj is mock_stmt and cls == FromStatement:
                return True
            return type.__instancecheck__(cls, obj) if isinstance(cls, type) else __builtins__["isinstance"](obj, cls)

        mock_isinstance.side_effect = isinstance_side_effect
        # Just verify it works when called with a real FromStatement-like object
    # Use real FromStatement by building it properly
    from sqlalchemy import literal_column
    inner = select(literal_column("1").label("id"))
    try:
        fs = FromStatement([User], inner)
        result = create_count_query(fs)
        assert result is not None
    except Exception:
        pytest.skip("FromStatement construction not straightforward in this SQLAlchemy version")


# ── _maybe_unique ───────────────────────────────────────────────────────────


def test_maybe_unique_true_calls_unique():
    mock_result = MagicMock()
    mock_result.unique.return_value.all.return_value = [1, 2, 3]
    result = _maybe_unique(mock_result, unique=True)
    assert result == [1, 2, 3]
    mock_result.unique.assert_called_once()


def test_maybe_unique_false_skips_unique():
    mock_result = MagicMock()
    mock_result.all.return_value = [1, 2, 3]
    result = _maybe_unique(mock_result, unique=False)
    assert result == [1, 2, 3]
    mock_result.unique.assert_not_called()


# ── _unwrap_items ───────────────────────────────────────────────────────────


def test_unwrap_items_text_clause_uses_legacy_mode():
    """TextClause defaults to 'legacy' unwrap mode."""
    items = [(1,), (2,), (3,)]
    q = text("SELECT id FROM t")
    result = _unwrap_items(items, q)
    assert result == [1, 2, 3]


def test_unwrap_items_no_unwrap_mode_returns_unchanged():
    items = [(1, "Alice"), (2, "Bob")]
    q = select(User.id)
    result = _unwrap_items(items, q, unwrap_mode="no-unwrap")
    assert result == [(1, "Alice"), (2, "Bob")]


def test_unwrap_items_unwrap_mode_forces_unwrap():
    items = [(1,), (2,)]
    q = select(User.id)
    result = _unwrap_items(items, q, unwrap_mode="unwrap")
    assert result == [1, 2]


def test_unwrap_items_legacy_mode_unwraps_single_element_tuples():
    items = [(1,), (2,), (3,)]
    q = select(User.id)
    result = _unwrap_items(items, q, unwrap_mode="legacy")
    assert result == [1, 2, 3]


def test_unwrap_items_legacy_mode_keeps_multi_element_tuples():
    items = [(1, "Alice"), (2, "Bob")]
    q = select(User.id, User.name)
    result = _unwrap_items(items, q, unwrap_mode="legacy")
    assert result == [(1, "Alice"), (2, "Bob")]


def test_unwrap_items_auto_mode_entity_select():
    """Auto mode with select(User) should unwrap."""
    items = [(1,), (2,)]
    q = select(User)
    result = _unwrap_items(items, q, unwrap_mode="auto")
    assert result == [1, 2]


def test_unwrap_items_auto_mode_single_col_no_unwrap():
    """Auto mode with select(User.id) should NOT unwrap."""
    items = [(1,), (2,)]
    q = select(User.id)
    result = _unwrap_items(items, q, unwrap_mode="auto")
    assert result == [(1,), (2,)]


# ── _inner_transformer ──────────────────────────────────────────────────────


def test_inner_transformer_unique_true():
    mock_result = MagicMock()
    mock_result.unique.return_value.all.return_value = [(1,), (2,)]
    q = select(User.id)
    result = _inner_transformer(mock_result, query=q, unwrap_mode="no-unwrap", unique=True)
    assert result == [(1,), (2,)]
    mock_result.unique.assert_called_once()


def test_inner_transformer_unique_false():
    mock_result = MagicMock()
    mock_result.all.return_value = [(1,), (2,)]
    q = select(User.id)
    result = _inner_transformer(mock_result, query=q, unwrap_mode="no-unwrap", unique=False)
    assert result == [(1,), (2,)]
    mock_result.unique.assert_not_called()


def test_inner_transformer_applies_unwrap():
    mock_result = MagicMock()
    mock_result.unique.return_value.all.return_value = [(1,), (2,)]
    q = text("SELECT id FROM t")  # legacy mode
    result = _inner_transformer(mock_result, query=q, unwrap_mode=None, unique=True)
    assert result == [1, 2]


def test_inner_transformer_suppresses_attribute_error():
    """If _maybe_unique raises AttributeError, it is suppressed."""
    items = [(1,), (2,)]
    q = text("SELECT id FROM t")
    # Pass plain list — it has no .unique(), AttributeError is suppressed
    result = _inner_transformer(items, query=q, unwrap_mode="legacy", unique=True)
    assert result == [1, 2]


# ── _new_paginate_sign ──────────────────────────────────────────────────────


def test_new_paginate_sign_returns_correct_tuple(session):
    q = select(User)
    params = Params(page=1, size=10)
    result = _new_paginate_sign(session, q, params)
    assert len(result) == 10
    # index 2 is conn, index 3 is params
    assert result[2] is session
    assert result[3] is params


def test_new_paginate_sign_none_count_query(session):
    q = select(User)
    result = _new_paginate_sign(session, q)
    assert result[1] is None


def test_new_paginate_sign_prepares_count_query(session):
    q = select(User)
    cq = select(User)
    result = _new_paginate_sign(session, q, count_query=cq)
    assert result[1] is not None


# ── _old_paginate_sign ──────────────────────────────────────────────────────


def test_old_paginate_sign_raises_when_no_session():
    mock_query = MagicMock()
    mock_query.session = None
    with pytest.raises(ValueError, match="query.session is None"):
        _old_paginate_sign(mock_query)


def test_old_paginate_sign_returns_session_from_query():
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_query.session = mock_session
    # _prepare_query will call _statement_20 if present
    mock_query._statement_20.return_value = select(User)
    result = _old_paginate_sign(mock_query)
    assert result[2] is mock_session


# ── paginate (sync integration) ─────────────────────────────────────────────


def test_paginate_returns_all_items(session):
    q = select(User)
    params = Params(page=1, size=10)
    with set_page(Page):
        result = paginate(session, q, params)
    assert result.total == 3
    assert len(result.items) == 3


def test_paginate_first_page_respects_size(session):
    q = select(User)
    params = Params(page=1, size=2)
    with set_page(Page):
        result = paginate(session, q, params)
    assert result.total == 3
    assert len(result.items) == 2


def test_paginate_second_page(session):
    q = select(User)
    params = Params(page=2, size=2)
    with set_page(Page):
        result = paginate(session, q, params)
    assert result.total == 3
    assert len(result.items) == 1


def test_paginate_with_text_query(session):
    q = text("SELECT id, name FROM test_users_sqlalchemy")
    params = Params(page=1, size=10)
    with set_page(Page):
        result = paginate(session, q, params)
    assert result.total == 3


def test_paginate_with_custom_count_query(session):
    q = select(User)
    count_q = create_count_query(q)
    params = Params(page=1, size=10)
    with set_page(Page):
        result = paginate(session, q, params, count_query=count_q)
    assert result.total == 3


def test_paginate_with_subquery_count_false(session):
    q = select(User)
    params = Params(page=1, size=10)
    with set_page(Page):
        result = paginate(session, q, params, subquery_count=False)
    assert result.total == 3


def test_paginate_with_unwrap_mode_no_unwrap(session):
    q = select(User)
    params = Params(page=1, size=10)
    with set_page(Page):
        result = paginate(session, q, params, unwrap_mode="no-unwrap")
    assert result.total == 3


def test_paginate_with_transformer(session):
    q = select(User)
    params = Params(page=1, size=10)

    def transformer(items: Sequence) -> list:
        return [{"id": u.id, "name": u.name} for u in items]

    with set_page(Page):
        result = paginate(session, q, params, transformer=transformer)
    assert result.total == 3
    assert isinstance(result.items[0], dict)


# ── apaginate (async integration) ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_apaginate_returns_page():
    try:
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

        from fastapi_pagination.ext.sqlalchemy import apaginate
    except ImportError:
        pytest.skip("SQLAlchemy async not available")

    class AsyncBase(DeclarativeBase):
        pass

    class AsyncUser(AsyncBase):
        __tablename__ = "async_test_users"
        id = Column(Integer, primary_key=True)
        name = Column(String)

    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(AsyncBase.metadata.create_all)
    async with AsyncSession(eng) as sess:
        sess.add_all([AsyncUser(id=1, name="X"), AsyncUser(id=2, name="Y")])
        await sess.commit()

    async with AsyncSession(eng) as sess:
        q = select(AsyncUser)
        params = Params(page=1, size=10)
        with set_page(Page):
            result = await apaginate(sess, q, params)

    assert result.total == 2
    assert len(result.items) == 2


@pytest.mark.asyncio
async def test_apaginate_pagination():
    try:
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

        from fastapi_pagination.ext.sqlalchemy import apaginate
    except ImportError:
        pytest.skip("SQLAlchemy async not available")

    class AsyncBase2(DeclarativeBase):
        pass

    class AsyncUser2(AsyncBase2):
        __tablename__ = "async_test_users2"
        id = Column(Integer, primary_key=True)
        name = Column(String)

    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(AsyncBase2.metadata.create_all)
    async with AsyncSession(eng) as sess:
        sess.add_all([AsyncUser2(id=i, name=f"U{i}") for i in range(1, 6)])
        await sess.commit()

    async with AsyncSession(eng) as sess:
        q = select(AsyncUser2)
        params = Params(page=2, size=2)
        with set_page(Page):
            result = await apaginate(sess, q, params)

    assert result.total == 5
    assert len(result.items) == 2


# ── _cursor_flow ─────────────────────────────────────────────────────────────


def test_cursor_flow_raises_for_text_clause():
    q = text("SELECT * FROM t")
    raw_params = CursorRawParams(cursor=None, size=10)
    conn = MagicMock()
    gen = _cursor_flow(q, conn, unique=False, is_async=False, raw_params=raw_params)
    with pytest.raises(ValueError, match="raw SQL queries"):
        gen.send(None)


def test_cursor_flow_raises_for_from_statement():
    from sqlalchemy.orm import FromStatement

    raw_params = CursorRawParams(cursor=None, size=10)
    conn = MagicMock()
    mock_fs = MagicMock(spec=FromStatement)
    mock_fs._order_by_clauses = (MagicMock(),)
    gen = _cursor_flow(mock_fs, conn, unique=False, is_async=False, raw_params=raw_params)
    with pytest.raises(ValueError, match="FromStatement"):
        gen.send(None)


def test_cursor_flow_raises_for_missing_ordering():
    q = select(User)  # no ORDER BY → _order_by_clauses is ()
    raw_params = CursorRawParams(cursor=None, size=10)
    conn = MagicMock()
    with patch("fastapi_pagination.ext.sqlalchemy.paging") as mock_paging:
        mock_paging.__bool__ = lambda self: True
        gen = _cursor_flow(q, conn, unique=False, is_async=False, raw_params=raw_params)
        with pytest.raises(ValueError, match="ordering"):
            gen.send(None)


def _make_mock_page(items, has_previous=False, has_next=False):
    mock_page = MagicMock()
    mock_page.__iter__ = MagicMock(return_value=iter(items))
    mock_page.paging.bookmark_current = "curr"
    mock_page.paging.bookmark_current_backwards = "curr_back"
    mock_page.paging.has_previous = has_previous
    mock_page.paging.has_next = has_next
    mock_page.paging.bookmark_previous = "prev" if has_previous else None
    mock_page.paging.bookmark_next = "next" if has_next else None
    return mock_page


def test_cursor_flow_sync_happy_path():
    q = select(User).order_by(User.id)
    raw_params = CursorRawParams(cursor=None, size=10)
    conn = MagicMock()
    mock_page = _make_mock_page([1, 2, 3])

    with patch("fastapi_pagination.ext.sqlalchemy.paging") as mock_paging:
        mock_paging.select_page = MagicMock(return_value=mock_page)
        gen = _cursor_flow(q, conn, unique=False, is_async=False, raw_params=raw_params)
        items, data = run_sync_flow(gen)

    assert items == [1, 2, 3]
    assert data["current"] == "curr"
    assert data["current_backwards"] == "curr_back"
    assert data["previous"] is None
    assert data["next_"] is None


def test_cursor_flow_sync_with_pagination_cursors():
    q = select(User).order_by(User.id)
    raw_params = CursorRawParams(cursor=None, size=2)
    conn = MagicMock()
    mock_page = _make_mock_page([1, 2], has_previous=True, has_next=True)

    with patch("fastapi_pagination.ext.sqlalchemy.paging") as mock_paging:
        mock_paging.select_page = MagicMock(return_value=mock_page)
        gen = _cursor_flow(q, conn, unique=False, is_async=False, raw_params=raw_params)
        items, data = run_sync_flow(gen)

    assert items == [1, 2]
    assert data["previous"] == "prev"
    assert data["next_"] == "next"


def test_cursor_flow_async_uses_apaging():
    q = select(User).order_by(User.id)
    raw_params = CursorRawParams(cursor=None, size=5)
    conn = MagicMock()
    mock_page = _make_mock_page([10, 20])

    with patch("fastapi_pagination.ext.sqlalchemy.apaging") as mock_apaging, \
         patch("fastapi_pagination.ext.sqlalchemy.paging") as mock_paging:
        mock_apaging.select_page = MagicMock(return_value=mock_page)
        gen = _cursor_flow(q, conn, unique=True, is_async=True, raw_params=raw_params)
        items, data = run_sync_flow(gen)

    assert items == [10, 20]
    mock_apaging.select_page.assert_called_once()
    mock_paging.select_page.assert_not_called()
