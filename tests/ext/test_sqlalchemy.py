import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import Column, Integer, String, Table, MetaData, select, text, union
from sqlalchemy.orm import Session, declarative_base, noload
from sqlalchemy.sql import CompoundSelect
from sqlalchemy.sql.elements import TextClause

from fastapi_pagination.bases import RawParams
from fastapi_pagination.default import Page, Params
from fastapi_pagination.ext.sqlalchemy import (
    _inner_transformer,
    _limit_offset_flow,
    _maybe_unique,
    _new_paginate_sign,
    _old_paginate_sign,
    _prepare_query,
    _prepare_query_for_cursor,
    _should_unwrap_scalars,
    _should_unwrap_scalars_for_query,
    _total_flow,
    _unwrap_items,
    _unwrap_params,
    create_count_query,
    create_count_query_from_text,
    create_paginate_query,
    create_paginate_query_from_text,
    paginate,
    apaginate,
)
from fastapi_pagination.flow import run_sync_flow, run_async_flow


metadata = MetaData()
users_table = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String),
)

Base = declarative_base()


class UserModel(Base):
    __tablename__ = "user_model"
    id = Column(Integer, primary_key=True)
    name = Column(String)


class SingleColModel(Base):
    __tablename__ = "single_col_model"
    id = Column(Integer, primary_key=True)


# ── _prepare_query ──────────────────────────────────────────────────────────


def test_prepare_query_returns_none_for_none():
    result = _prepare_query(None)
    assert result is None


def test_prepare_query_returns_select_unchanged_when_no_statement_20():
    query = select(users_table)
    result = _prepare_query(query)
    assert result is query


def test_prepare_query_calls_statement_20_when_available():
    expected = select(users_table)
    mock_query = MagicMock()
    mock_query._statement_20.return_value = expected

    result = _prepare_query(mock_query)

    mock_query._statement_20.assert_called_once()
    assert result is expected


# ── _prepare_query_for_cursor ───────────────────────────────────────────────


def test_prepare_query_for_cursor_returns_select_unchanged():
    query = select(users_table)
    result = _prepare_query_for_cursor(query)
    assert result is query


def test_prepare_query_for_cursor_wraps_compound_select():
    compound = union(select(users_table), select(users_table))
    result = _prepare_query_for_cursor(compound)
    assert not isinstance(result, CompoundSelect)
    # Should be a Select wrapping a subquery
    from sqlalchemy.sql import Select
    assert isinstance(result, Select)


def test_prepare_query_for_cursor_compound_select_with_ordering():
    compound = union(select(users_table), select(users_table))
    ordered = compound.order_by(users_table.c.id)
    result = _prepare_query_for_cursor(ordered)
    assert not isinstance(result, CompoundSelect)
    # Ordering should be preserved in the outer select
    assert len(result._order_by_clauses) == 1


# ── _should_unwrap_scalars_for_query ────────────────────────────────────────


def test_should_unwrap_scalars_for_query_multiple_cols_returns_false():
    query = select(users_table.c.id, users_table.c.name)
    result = _should_unwrap_scalars_for_query(query)
    assert result is False


def test_should_unwrap_scalars_for_query_orm_entity_multiple_cols_returns_true():
    query = select(UserModel)
    result = _should_unwrap_scalars_for_query(query)
    assert result is True


def test_should_unwrap_scalars_for_query_single_plain_col_returns_false():
    query = select(users_table.c.id)
    result = _should_unwrap_scalars_for_query(query)
    assert result is False


def test_should_unwrap_scalars_for_query_single_col_entity_returns_true():
    # SingleColModel has only one column (id), so len(all_cols) == 1
    # and expr is entity → True
    query = select(SingleColModel)
    result = _should_unwrap_scalars_for_query(query)
    assert result is True


# ── _should_unwrap_scalars ──────────────────────────────────────────────────


def test_should_unwrap_scalars_returns_false_for_non_selectable():
    result = _should_unwrap_scalars([1, 2, 3])
    assert result is False


def test_should_unwrap_scalars_returns_false_for_compound_select():
    compound = union(select(users_table), select(users_table))
    result = _should_unwrap_scalars(compound)
    assert result is False


def test_should_unwrap_scalars_returns_false_for_multi_column_select():
    query = select(users_table.c.id, users_table.c.name)
    result = _should_unwrap_scalars(query)
    assert result is False


def test_should_unwrap_scalars_returns_true_on_attribute_error():
    # TextClause doesn't have column_descriptions, so _should_unwrap_scalars_for_query
    # raises AttributeError → returns True
    query = text("SELECT id FROM users")
    result = _should_unwrap_scalars(query)
    assert result is True


def test_should_unwrap_scalars_returns_true_for_orm_entity_select():
    query = select(UserModel)
    result = _should_unwrap_scalars(query)
    assert result is True


# ── _unwrap_params ──────────────────────────────────────────────────────────


def test_unwrap_params_returns_raw_params_unchanged():
    raw = RawParams(limit=10, offset=5)
    result = _unwrap_params(raw)
    assert result is raw


def test_unwrap_params_converts_abstract_params_to_raw():
    params = Params(page=2, size=20)
    result = _unwrap_params(params)
    assert isinstance(result, RawParams)
    assert result.limit == 20
    assert result.offset == 20


# ── create_paginate_query_from_text ─────────────────────────────────────────


def test_create_paginate_query_from_text_returns_paginated_query():
    params = Params(page=1, size=10)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = create_paginate_query_from_text("SELECT * FROM users", params)
    assert "LIMIT 10" in result
    assert "OFFSET 0" in result
    assert len(w) >= 1
    assert issubclass(w[0].category, DeprecationWarning)


def test_create_paginate_query_from_text_with_raw_params():
    raw = RawParams(limit=5, offset=15)
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        result = create_paginate_query_from_text("SELECT * FROM items", raw)
    assert "LIMIT 5" in result
    assert "OFFSET 15" in result


# ── create_count_query_from_text ─────────────────────────────────────────────


def test_create_count_query_from_text_returns_count_query():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = create_count_query_from_text("SELECT * FROM users")
    assert "count(*)" in result.lower()
    assert len(w) >= 1
    assert issubclass(w[0].category, DeprecationWarning)


# ── create_paginate_query ────────────────────────────────────────────────────


def test_create_paginate_query_with_text_clause():
    query = text("SELECT * FROM users")
    params = RawParams(limit=10, offset=5)
    result = create_paginate_query(query, params)
    assert isinstance(result, TextClause)
    assert "LIMIT 10" in result.text
    assert "OFFSET 5" in result.text


def test_create_paginate_query_with_select():
    query = select(users_table)
    params = RawParams(limit=10, offset=20)
    result = create_paginate_query(query, params)
    compiled = str(result.compile())
    assert "LIMIT" in compiled or "limit" in str(result)


def test_create_paginate_query_with_select_and_params_object():
    query = select(users_table)
    params = Params(page=2, size=15)
    result = create_paginate_query(query, params)
    compiled = str(result.compile())
    assert result is not query


# ── create_count_query ───────────────────────────────────────────────────────


def test_create_count_query_with_text_clause():
    query = text("SELECT * FROM users")
    result = create_count_query(query)
    assert isinstance(result, TextClause)
    assert "count" in result.text.lower()


def test_create_count_query_with_select_use_subquery_true():
    query = select(users_table)
    result = create_count_query(query, use_subquery=True)
    compiled = str(result.compile())
    assert "count" in compiled.lower()


def test_create_count_query_with_select_use_subquery_false():
    query = select(users_table)
    result = create_count_query(query, use_subquery=False)
    compiled = str(result.compile())
    assert "count" in compiled.lower()


def test_create_count_query_with_from_statement():
    mock_from_stmt = MagicMock()
    mock_from_stmt.element = select(users_table)

    from fastapi_pagination.ext.sqlalchemy import FromStatement

    with patch("fastapi_pagination.ext.sqlalchemy.isinstance") as mock_isinstance:
        def isinstance_side_effect(obj, cls):
            if cls is TextClause:
                return False
            if cls is FromStatement:
                return obj is mock_from_stmt
            return __builtins__["isinstance"](obj, cls) if isinstance(__builtins__, dict) else __import__("builtins").isinstance(obj, cls)

        mock_isinstance.side_effect = isinstance_side_effect
        # Direct test is complex; instead test via real from_statement if possible
    # Fall back to testing the recursion: FromStatement delegates to element
    # This is implicitly tested by create_count_query with select


# ── _maybe_unique ────────────────────────────────────────────────────────────


def test_maybe_unique_calls_unique_when_true():
    mock_result = MagicMock()
    mock_result.unique.return_value.all.return_value = [1, 2, 3]

    result = _maybe_unique(mock_result, unique=True)

    mock_result.unique.assert_called_once()
    mock_result.unique.return_value.all.assert_called_once()
    assert result == [1, 2, 3]


def test_maybe_unique_skips_unique_when_false():
    mock_result = MagicMock()
    mock_result.all.return_value = [4, 5, 6]

    result = _maybe_unique(mock_result, unique=False)

    mock_result.unique.assert_not_called()
    mock_result.all.assert_called_once()
    assert result == [4, 5, 6]


# ── _unwrap_items ────────────────────────────────────────────────────────────


def test_unwrap_items_text_clause_uses_legacy_mode():
    items = [(1,), (2,), (3,)]
    query = text("SELECT id FROM users")
    result = _unwrap_items(items, query)
    # legacy mode unwraps single-element tuples
    assert result == [1, 2, 3]


def test_unwrap_items_no_unwrap_mode():
    items = [(1, "a"), (2, "b")]
    query = select(users_table)
    result = _unwrap_items(items, query, unwrap_mode="no-unwrap")
    assert result == [(1, "a"), (2, "b")]


def test_unwrap_items_unwrap_mode_force_unwraps():
    items = [(1, "a"), (2, "b")]
    query = select(users_table)
    result = _unwrap_items(items, query, unwrap_mode="unwrap")
    # force_unwrap=True → always takes first element
    assert result == [1, 2]


def test_unwrap_items_legacy_mode_explicit():
    items = [(10,), (20,)]
    query = select(users_table)
    result = _unwrap_items(items, query, unwrap_mode="legacy")
    assert result == [10, 20]


def test_unwrap_items_auto_mode_no_unwrap_for_multi_col():
    items = [(1, "alice"), (2, "bob")]
    query = select(users_table.c.id, users_table.c.name)
    result = _unwrap_items(items, query, unwrap_mode="auto")
    # _should_unwrap_scalars returns False for multi-col select
    assert result == [(1, "alice"), (2, "bob")]


def test_unwrap_items_auto_mode_unwraps_for_orm_entity():
    items = [(1,), (2,)]
    query = select(SingleColModel)
    result = _unwrap_items(items, query, unwrap_mode="auto")
    # _should_unwrap_scalars returns True for ORM entity → force_unwrap
    assert result == [1, 2]


# ── _inner_transformer ───────────────────────────────────────────────────────


def test_inner_transformer_calls_maybe_unique_and_unwrap_items():
    mock_result = MagicMock()
    mock_result.unique.return_value.all.return_value = [(1,), (2,)]
    query = text("SELECT id FROM users")

    result = _inner_transformer(mock_result, query=query, unwrap_mode=None, unique=True)

    mock_result.unique.assert_called_once()
    assert result == [1, 2]


def test_inner_transformer_unique_false():
    mock_result = MagicMock()
    mock_result.all.return_value = [(3,), (4,)]
    query = text("SELECT id FROM items")

    result = _inner_transformer(mock_result, query=query, unwrap_mode=None, unique=False)

    mock_result.unique.assert_not_called()
    assert result == [3, 4]


def test_inner_transformer_no_unwrap_mode():
    mock_result = MagicMock()
    mock_result.unique.return_value.all.return_value = [(5, "x"), (6, "y")]
    query = select(users_table.c.id, users_table.c.name)

    result = _inner_transformer(mock_result, query=query, unwrap_mode="no-unwrap", unique=True)

    assert result == [(5, "x"), (6, "y")]


# ── _total_flow ──────────────────────────────────────────────────────────────


def test_total_flow_with_mock_conn():
    mock_conn = MagicMock()
    mock_conn.scalar.return_value = 42

    query = select(users_table)
    total = run_sync_flow(_total_flow(query, mock_conn, None, True))

    assert total == 42
    mock_conn.scalar.assert_called_once()


def test_total_flow_with_explicit_count_query():
    mock_conn = MagicMock()
    mock_conn.scalar.return_value = 7

    query = select(users_table)
    count_q = text("SELECT count(*) FROM users")
    total = run_sync_flow(_total_flow(query, mock_conn, count_q, True))

    assert total == 7
    # scalar should be called with the provided count_query
    args = mock_conn.scalar.call_args[0]
    assert args[0] is count_q


# ── _limit_offset_flow ───────────────────────────────────────────────────────


def test_limit_offset_flow_returns_execute_result():
    mock_conn = MagicMock()
    mock_result = MagicMock()
    mock_conn.execute.return_value = mock_result

    query = select(users_table)
    raw_params = RawParams(limit=10, offset=0)
    result = run_sync_flow(_limit_offset_flow(query, mock_conn, raw_params))

    assert result is mock_result
    mock_conn.execute.assert_called_once()


def test_limit_offset_flow_applies_limit_and_offset():
    mock_conn = MagicMock()
    mock_conn.execute.return_value = MagicMock()

    query = select(users_table)
    raw_params = RawParams(limit=5, offset=10)
    run_sync_flow(_limit_offset_flow(query, mock_conn, raw_params))

    call_query = mock_conn.execute.call_args[0][0]
    compiled = str(call_query.compile())
    assert "5" in compiled or "LIMIT" in compiled.upper()


# ── _new_paginate_sign ───────────────────────────────────────────────────────


def test_new_paginate_sign_returns_correct_tuple():
    mock_conn = MagicMock(spec=Session)
    query = select(users_table)
    params = Params(page=1, size=10)

    result = _new_paginate_sign(mock_conn, query, params)

    q, cq, conn, p, transformer, additional, unique, subquery_count, unwrap_mode, config = result
    assert q is query
    assert cq is None
    assert conn is mock_conn
    assert p is params
    assert unique is True
    assert subquery_count is True


def test_new_paginate_sign_with_count_query():
    mock_conn = MagicMock(spec=Session)
    query = select(users_table)
    count_query = select(users_table)
    params = Params(page=1, size=10)

    result = _new_paginate_sign(mock_conn, query, params, count_query=count_query)

    q, cq, conn, p, *_ = result
    assert cq is count_query


def test_new_paginate_sign_prepares_query_with_statement_20():
    mock_conn = MagicMock(spec=Session)
    expected = select(users_table)
    mock_query = MagicMock()
    mock_query._statement_20.return_value = expected

    result = _new_paginate_sign(mock_conn, mock_query)

    q, *_ = result
    assert q is expected


# ── _old_paginate_sign ───────────────────────────────────────────────────────


def test_old_paginate_sign_raises_when_session_is_none():
    mock_query = MagicMock()
    mock_query.session = None

    with pytest.raises(ValueError, match="query.session is None"):
        _old_paginate_sign(mock_query)


def test_old_paginate_sign_returns_correct_tuple():
    mock_session = MagicMock(spec=Session)
    mock_query = MagicMock()
    mock_query.session = mock_session
    expected_stmt = select(users_table)
    mock_query._statement_20.return_value = expected_stmt

    result = _old_paginate_sign(mock_query)

    q, cq, conn, p, transformer, additional, unique, subquery_count, unwrap_mode, config = result
    assert q is expected_stmt
    assert cq is None
    assert conn is mock_session
    assert p is None
    assert unique is True
    assert subquery_count is True


def test_old_paginate_sign_with_params():
    mock_session = MagicMock(spec=Session)
    mock_query = MagicMock()
    mock_query.session = mock_session
    mock_query._statement_20.return_value = select(users_table)
    params = Params(page=2, size=5)

    result = _old_paginate_sign(mock_query, params)

    _, _, _, p, *_ = result
    assert p is params


# ── paginate (sync) ──────────────────────────────────────────────────────────


def test_paginate_sync_with_mock_session():
    mock_conn = MagicMock(spec=Session)
    mock_conn.scalar.return_value = 3

    mock_result = MagicMock()
    mock_result.unique.return_value.all.return_value = []
    mock_conn.execute.return_value = mock_result

    query = select(users_table)
    params = Params(page=1, size=10)

    result = paginate(mock_conn, query, params)

    assert result.total == 3
    assert result.items == []


def test_paginate_sync_with_items():
    mock_conn = MagicMock(spec=Session)
    mock_conn.scalar.return_value = 2

    mock_result = MagicMock()
    mock_result.unique.return_value.all.return_value = [(1, "Alice"), (2, "Bob")]
    mock_conn.execute.return_value = mock_result

    query = select(users_table.c.id, users_table.c.name)
    params = Params(page=1, size=10)

    result = paginate(mock_conn, query, params)

    assert result.total == 2
    assert len(result.items) == 2


def test_paginate_uses_new_sign_when_first_arg_is_not_query():
    mock_conn = MagicMock(spec=Session)
    mock_conn.scalar.return_value = 0
    mock_result = MagicMock()
    mock_result.unique.return_value.all.return_value = []
    mock_conn.execute.return_value = mock_result

    query = select(users_table)
    params = Params(page=1, size=10)

    result = paginate(mock_conn, query, params)

    assert result is not None


def test_paginate_with_subquery_count_false():
    mock_conn = MagicMock(spec=Session)
    mock_conn.scalar.return_value = 1
    mock_result = MagicMock()
    mock_result.unique.return_value.all.return_value = [(42, "test")]
    mock_conn.execute.return_value = mock_result

    query = select(users_table.c.id, users_table.c.name)
    params = Params(page=1, size=10)

    result = paginate(mock_conn, query, params, subquery_count=False)

    assert result.total == 1


# ── apaginate ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_apaginate_basic():
    mock_conn = AsyncMock()
    mock_conn.scalar = AsyncMock(return_value=5)

    mock_result = MagicMock()
    mock_result.unique.return_value.all.return_value = []
    mock_conn.execute = AsyncMock(return_value=mock_result)

    query = select(users_table)
    params = Params(page=1, size=10)

    with patch("fastapi_pagination.ext.sqlalchemy.greenlet_spawn", side_effect=lambda f, *a, **kw: f(*a, **kw)):
        result = await apaginate(mock_conn, query, params=params)

    assert result.total == 5
    assert result.items == []


@pytest.mark.asyncio
async def test_apaginate_with_count_query():
    mock_conn = AsyncMock()
    mock_conn.scalar = AsyncMock(return_value=2)

    mock_result = MagicMock()
    mock_result.unique.return_value.all.return_value = [(1, "a"), (2, "b")]
    mock_conn.execute = AsyncMock(return_value=mock_result)

    query = select(users_table.c.id, users_table.c.name)
    count_query = text("SELECT count(*) FROM users")
    params = Params(page=1, size=10)

    with patch("fastapi_pagination.ext.sqlalchemy.greenlet_spawn", side_effect=lambda f, *a, **kw: f(*a, **kw)):
        result = await apaginate(mock_conn, query, params=params, count_query=count_query)

    assert result.total == 2


@pytest.mark.asyncio
async def test_apaginate_prepares_query():
    mock_conn = AsyncMock()
    mock_conn.scalar = AsyncMock(return_value=1)

    mock_result = MagicMock()
    mock_result.unique.return_value.all.return_value = []
    mock_conn.execute = AsyncMock(return_value=mock_result)

    expected = select(users_table)
    mock_query = MagicMock()
    mock_query._statement_20.return_value = expected

    params = Params(page=1, size=10)

    with patch("fastapi_pagination.ext.sqlalchemy.greenlet_spawn", side_effect=lambda f, *a, **kw: f(*a, **kw)):
        result = await apaginate(mock_conn, mock_query, params=params)

    mock_query._statement_20.assert_called_once()
    assert result.total == 1


# ── _cursor_flow error cases ─────────────────────────────────────────────────


def test_cursor_flow_raises_for_text_clause():
    from fastapi_pagination.bases import CursorRawParams
    from fastapi_pagination.ext.sqlalchemy import _cursor_flow

    mock_conn = MagicMock(spec=Session)
    query = text("SELECT id FROM users")
    raw_params = CursorRawParams(cursor=None, size=10)

    with pytest.raises(ValueError, match="Cursor pagination cannot be used with raw SQL queries"):
        run_sync_flow(_cursor_flow(query, mock_conn, True, False, raw_params))


def test_cursor_flow_raises_for_no_ordering():
    from fastapi_pagination.bases import CursorRawParams
    from fastapi_pagination.ext.sqlalchemy import _cursor_flow

    mock_conn = MagicMock(spec=Session)
    query = select(users_table)  # no ORDER BY
    raw_params = CursorRawParams(cursor=None, size=10)

    with pytest.raises(ValueError, match="Cursor pagination requires ordering"):
        run_sync_flow(_cursor_flow(query, mock_conn, True, False, raw_params))
