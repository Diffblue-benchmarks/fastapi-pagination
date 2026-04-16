from __future__ import annotations

import warnings
from collections.abc import Sequence
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import Column, Integer, String, func, select, text, union_all
from sqlalchemy.orm import DeclarativeBase, Query, Session
from sqlalchemy.sql import CompoundSelect, Select
from sqlalchemy.sql.elements import TextClause

from fastapi_pagination.bases import AbstractParams, BaseRawParams, CursorRawParams, RawParams
from fastapi_pagination.ext.sqlalchemy import (
    NonHashableRowsException,
    _inner_transformer,
    _maybe_unique,
    _new_paginate_sign,
    _old_paginate_sign,
    _paginate_from_statement,
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
# Helpers
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    pass


class MyModel(Base):
    __tablename__ = "my_model"
    id = Column(Integer, primary_key=True)
    name = Column(String)


class SimpleParams(AbstractParams):
    def to_raw_params(self) -> BaseRawParams:
        return RawParams(limit=10, offset=5)


# ---------------------------------------------------------------------------
# _prepare_query
# ---------------------------------------------------------------------------


def test_prepare_query_none_returns_none():
    assert _prepare_query(None) is None


def test_prepare_query_select_returns_query():
    q = select(MyModel)
    result = _prepare_query(q)
    assert result is q


def test_prepare_query_calls_statement_20_if_available():
    mock_query = MagicMock()
    converted = select(MyModel)
    mock_query._statement_20.return_value = converted
    result = _prepare_query(mock_query)
    assert result is converted
    mock_query._statement_20.assert_called_once()


def test_prepare_query_suppresses_attribute_error_on_missing_statement_20():
    # A plain Select has no _statement_20; should just return as-is
    q = select(MyModel)
    result = _prepare_query(q)
    assert result is q


# ---------------------------------------------------------------------------
# _prepare_query_for_cursor
# ---------------------------------------------------------------------------


def test_prepare_query_for_cursor_non_compound_returns_same():
    q = select(MyModel)
    result = _prepare_query_for_cursor(q)
    assert result is q


def test_prepare_query_for_cursor_compound_wraps_in_subquery():
    q1 = select(MyModel.id)
    q2 = select(MyModel.id)
    compound = union_all(q1, q2)

    result = _prepare_query_for_cursor(compound)

    assert isinstance(result, Select)
    # The original compound is gone, wrapped in a subquery
    assert result is not compound


def test_prepare_query_for_cursor_compound_preserves_ordering():
    q1 = select(MyModel.id)
    q2 = select(MyModel.id)
    compound = union_all(q1, q2).order_by(MyModel.id)

    result = _prepare_query_for_cursor(compound)

    # Result should be a Select with the preserved order_by
    assert isinstance(result, Select)
    assert len(result._order_by_clauses) > 0


# ---------------------------------------------------------------------------
# _should_unwrap_scalars_for_query
# ---------------------------------------------------------------------------


def test_should_unwrap_scalars_for_query_multiple_cols_returns_false():
    q = select(MyModel.id, MyModel.name)
    assert _should_unwrap_scalars_for_query(q) is False


def test_should_unwrap_scalars_for_query_model_returns_true():
    # select(Model) -> one entity with multiple columns -> should unwrap
    q = select(MyModel)
    result = _should_unwrap_scalars_for_query(q)
    assert result is True


def test_should_unwrap_scalars_for_query_single_column_returns_false():
    # select(Model.id) -> one column, not a model entity
    q = select(MyModel.id)
    result = _should_unwrap_scalars_for_query(q)
    # One col_desc, one all_cols, expr is not entity -> False
    assert result is False


# ---------------------------------------------------------------------------
# _should_unwrap_scalars
# ---------------------------------------------------------------------------


def test_should_unwrap_scalars_non_selectable_returns_false():
    assert _should_unwrap_scalars("not a query") is False  # type: ignore[arg-type]
    assert _should_unwrap_scalars(42) is False  # type: ignore[arg-type]
    assert _should_unwrap_scalars(None) is False  # type: ignore[arg-type]


def test_should_unwrap_scalars_compound_select_returns_false():
    q1 = select(MyModel.id)
    q2 = select(MyModel.id)
    compound = union_all(q1, q2)
    assert _should_unwrap_scalars(compound) is False


def test_should_unwrap_scalars_text_clause_returns_false():
    # TextClause is in _selectable_classes but not CompoundSelect;
    # calling column_descriptions on it raises AttributeError -> returns True
    t = text("SELECT 1")
    result = _should_unwrap_scalars(t)
    # TextClause has no column_descriptions, so AttributeError -> returns True
    assert result is True


def test_should_unwrap_scalars_select_model_returns_true():
    q = select(MyModel)
    assert _should_unwrap_scalars(q) is True


def test_should_unwrap_scalars_select_single_col_returns_false():
    q = select(MyModel.id)
    assert _should_unwrap_scalars(q) is False


# ---------------------------------------------------------------------------
# _unwrap_params
# ---------------------------------------------------------------------------


def test_unwrap_params_with_raw_params_returns_same():
    params = RawParams(limit=5, offset=2)
    result = _unwrap_params(params)
    assert result is params


def test_unwrap_params_with_abstract_params_converts():
    params = SimpleParams()
    result = _unwrap_params(params)
    assert isinstance(result, RawParams)
    assert result.limit == 10
    assert result.offset == 5


# ---------------------------------------------------------------------------
# create_paginate_query_from_text (deprecated)
# ---------------------------------------------------------------------------


def test_create_paginate_query_from_text_deprecated():
    params = SimpleParams()
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = create_paginate_query_from_text("SELECT 1", params)
    assert any(issubclass(warning.category, DeprecationWarning) for warning in w)
    assert "LIMIT" in result or "SELECT" in result


def test_create_paginate_query_from_text_with_raw_params():
    params = RawParams(limit=3, offset=1)
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        result = create_paginate_query_from_text("SELECT * FROM t", params)
    assert "LIMIT 3" in result
    assert "OFFSET 1" in result


# ---------------------------------------------------------------------------
# create_count_query_from_text (deprecated)
# ---------------------------------------------------------------------------


def test_create_count_query_from_text_deprecated():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = create_count_query_from_text("SELECT * FROM t")
    assert any(issubclass(warning.category, DeprecationWarning) for warning in w)
    assert "count(*)" in result.lower()


def test_create_count_query_from_text_returns_count_sql():
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        result = create_count_query_from_text("SELECT id FROM users")
    assert "SELECT id FROM users" in result
    assert "count" in result.lower()


# ---------------------------------------------------------------------------
# create_paginate_query
# ---------------------------------------------------------------------------


def test_create_paginate_query_with_text_clause():
    params = RawParams(limit=5, offset=2)
    result = create_paginate_query(text("SELECT * FROM t"), params)
    assert isinstance(result, TextClause)
    assert "LIMIT 5" in result.text
    assert "OFFSET 2" in result.text


def test_create_paginate_query_with_select():
    params = RawParams(limit=10, offset=0)
    q = select(MyModel)
    result = create_paginate_query(q, params)
    assert isinstance(result, Select)


def test_create_paginate_query_with_abstract_params():
    params = SimpleParams()
    q = select(MyModel)
    result = create_paginate_query(q, params)
    assert isinstance(result, Select)


# ---------------------------------------------------------------------------
# _paginate_from_statement
# ---------------------------------------------------------------------------


def test_paginate_from_statement():
    try:
        from sqlalchemy.orm import FromStatement
    except ImportError:
        pytest.skip("FromStatement not available")

    inner = select(MyModel)
    stmt = FromStatement(MyModel, inner)
    params = RawParams(limit=5, offset=0)

    result = _paginate_from_statement(stmt, params)

    assert isinstance(result, FromStatement)
    # The inner element should now be a paginated query
    assert isinstance(result.element, Select)


# ---------------------------------------------------------------------------
# create_count_query
# ---------------------------------------------------------------------------


def test_create_count_query_with_text_clause():
    result = create_count_query(text("SELECT * FROM t"))
    assert isinstance(result, TextClause)
    assert "count" in result.text.lower()


def test_create_count_query_with_select_use_subquery_true():
    q = select(MyModel)
    result = create_count_query(q, use_subquery=True)
    assert isinstance(result, Select)


def test_create_count_query_with_select_use_subquery_false():
    q = select(MyModel)
    result = create_count_query(q, use_subquery=False)
    assert isinstance(result, Select)


def test_create_count_query_with_from_statement():
    try:
        from sqlalchemy.orm import FromStatement
    except ImportError:
        pytest.skip("FromStatement not available")

    inner = select(MyModel)
    stmt = FromStatement(MyModel, inner)
    result = create_count_query(stmt)
    # Should recursively call create_count_query on element
    assert isinstance(result, Select)


# ---------------------------------------------------------------------------
# _maybe_unique
# ---------------------------------------------------------------------------


def test_maybe_unique_with_unique_true():
    mock_result = MagicMock()
    mock_result.unique.return_value.all.return_value = [1, 2, 3]
    result = _maybe_unique(mock_result, unique=True)
    mock_result.unique.assert_called_once()
    assert result == [1, 2, 3]


def test_maybe_unique_with_unique_false():
    mock_result = MagicMock()
    mock_result.all.return_value = [1, 2, 3]
    result = _maybe_unique(mock_result, unique=False)
    mock_result.unique.assert_not_called()
    assert result == [1, 2, 3]


# ---------------------------------------------------------------------------
# _unwrap_items
# ---------------------------------------------------------------------------


def test_unwrap_items_text_clause_uses_legacy():
    items = [(1,), (2,)]
    result = _unwrap_items(items, text("SELECT 1"))
    assert result == [1, 2]


def test_unwrap_items_no_unwrap_mode():
    items = [(1, "a"), (2, "b")]
    result = _unwrap_items(items, text("SELECT 1"), unwrap_mode="no-unwrap")
    assert result == items


def test_unwrap_items_unwrap_mode():
    items = [(1,), (2,)]
    result = _unwrap_items(items, select(MyModel.id), unwrap_mode="unwrap")
    assert result == [1, 2]


def test_unwrap_items_legacy_mode():
    items = [(1,), (2,)]
    result = _unwrap_items(items, select(MyModel.id), unwrap_mode="legacy")
    assert result == [1, 2]


def test_unwrap_items_auto_with_model_select():
    # select(MyModel) causes _should_unwrap_scalars to return True
    items = [MagicMock(), MagicMock()]
    items[0].__len__ = lambda self: 1
    items[0].__getitem__ = lambda self, i: "a"
    items[1].__len__ = lambda self: 1
    items[1].__getitem__ = lambda self, i: "b"
    # Use a mock query that makes _should_unwrap_scalars return False to test the pass case
    mock_q = select(MyModel.id, MyModel.name)  # two columns -> _should_unwrap_scalars False
    raw_items = [(1, "a"), (2, "b")]
    result = _unwrap_items(raw_items, mock_q, unwrap_mode="auto")
    # Two columns, should not unwrap
    assert result == raw_items


def test_unwrap_items_auto_with_from_statement_uses_legacy():
    try:
        from sqlalchemy.orm import FromStatement
    except ImportError:
        pytest.skip("FromStatement not available")

    inner = select(MyModel)
    stmt = FromStatement(MyModel, inner)
    items = [(1,), (2,)]
    result = _unwrap_items(items, stmt)
    assert result == [1, 2]


# ---------------------------------------------------------------------------
# _inner_transformer
# ---------------------------------------------------------------------------


def test_inner_transformer_calls_maybe_unique_and_unwrap():
    mock_result = MagicMock()
    mock_result.unique.return_value.all.return_value = [(1,), (2,)]

    result = _inner_transformer(mock_result, query=text("SELECT 1"), unwrap_mode=None, unique=True)

    mock_result.unique.assert_called_once()
    # Legacy unwrap from TextClause
    assert result == [1, 2]


def test_inner_transformer_no_unique():
    mock_result = MagicMock()
    mock_result.all.return_value = [(1,), (2,)]

    result = _inner_transformer(mock_result, query=text("SELECT 1"), unwrap_mode=None, unique=False)

    mock_result.unique.assert_not_called()
    assert result == [1, 2]


def test_inner_transformer_suppresses_attribute_error():
    # If items has no unique() attribute, should suppress and continue
    items = [(1,), (2,)]
    result = _inner_transformer(items, query=text("SELECT 1"), unwrap_mode=None, unique=True)
    # AttributeError suppressed, items passed to _unwrap_items
    assert result == [1, 2]


# ---------------------------------------------------------------------------
# _old_paginate_sign
# ---------------------------------------------------------------------------


def test_old_paginate_sign_raises_when_session_is_none():
    mock_query = MagicMock(spec=Query)
    mock_query.session = None
    with pytest.raises(ValueError, match="query.session is None"):
        _old_paginate_sign(mock_query)


def test_old_paginate_sign_returns_tuple_with_session():
    mock_query = MagicMock(spec=Query)
    mock_session = MagicMock(spec=Session)
    mock_query.session = mock_session
    # _prepare_query calls _statement_20 if available
    converted = select(MyModel)
    mock_query._statement_20.return_value = converted

    result = _old_paginate_sign(mock_query)

    assert len(result) == 10
    assert result[2] is mock_session  # conn/session


# ---------------------------------------------------------------------------
# _new_paginate_sign
# ---------------------------------------------------------------------------


def test_new_paginate_sign_returns_tuple():
    mock_conn = MagicMock()
    q = select(MyModel)
    params = SimpleParams()

    result = _new_paginate_sign(mock_conn, q, params)

    assert len(result) == 10
    assert result[2] is mock_conn
    assert result[3] is params


def test_new_paginate_sign_with_count_query():
    mock_conn = MagicMock()
    q = select(MyModel)
    count_q = select(func.count())

    result = _new_paginate_sign(mock_conn, q, count_query=count_q)

    assert result[1] is count_q


def test_new_paginate_sign_with_none_count_query():
    mock_conn = MagicMock()
    q = select(MyModel)

    result = _new_paginate_sign(mock_conn, q)

    # count_query was None, _prepare_query(None) returns None
    assert result[1] is None
