from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Mock sqlalchemy and related modules before importing fastapi_pagination.ext.sqlalchemy
for _mod in [
    "sqlalchemy",
    "sqlalchemy.engine",
    "sqlalchemy.exc",
    "sqlalchemy.orm",
    "sqlalchemy.sql",
    "sqlalchemy.sql.elements",
    "sqlalchemy.ext",
    "sqlalchemy.ext.asyncio",
    "sqlalchemy.util",
    "sqlakeyset",
    "sqlakeyset.asyncio",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

import pytest

from fastapi_pagination.ext.sqlalchemy import _should_unwrap_scalars_for_query


class _FakeQuery:
    def __init__(self, column_descriptions, all_selected_columns):
        self.column_descriptions = column_descriptions
        self._all_selected_columns = all_selected_columns


def test_should_unwrap_scalars_for_query_multiple_col_descs_returns_false():
    """Multiple column descriptions → no need to unwrap → returns False"""
    desc1 = {"expr": MagicMock(), "entity": MagicMock()}
    desc2 = {"expr": MagicMock(), "entity": MagicMock()}
    query = _FakeQuery(
        column_descriptions=[desc1, desc2],
        all_selected_columns=[MagicMock(), MagicMock()],
    )

    result = _should_unwrap_scalars_for_query(query)

    assert result is False


def test_should_unwrap_scalars_for_query_single_desc_many_cols_returns_true():
    """Single column description but multiple columns → should unwrap → returns True"""
    desc = {"expr": MagicMock(), "entity": MagicMock()}
    query = _FakeQuery(
        column_descriptions=[desc],
        all_selected_columns=[MagicMock(), MagicMock(), MagicMock()],
    )

    result = _should_unwrap_scalars_for_query(query)

    assert result is True


def test_should_unwrap_scalars_for_query_single_desc_single_col_expr_is_entity_returns_true():
    """Single desc, single col, expr is not None and expr is entity → returns True"""
    entity = MagicMock()
    desc = {"expr": entity, "entity": entity}
    query = _FakeQuery(
        column_descriptions=[desc],
        all_selected_columns=[MagicMock()],
    )

    result = _should_unwrap_scalars_for_query(query)

    assert result is True


def test_should_unwrap_scalars_for_query_single_desc_single_col_expr_is_not_entity_returns_false():
    """Single desc, single col, expr is not None but expr is not entity → returns False"""
    expr = MagicMock()
    entity = MagicMock()
    desc = {"expr": expr, "entity": entity}
    query = _FakeQuery(
        column_descriptions=[desc],
        all_selected_columns=[MagicMock()],
    )

    result = _should_unwrap_scalars_for_query(query)

    assert result is False


def test_should_unwrap_scalars_for_query_single_desc_single_col_expr_is_none_returns_false():
    """Single desc, single col, expr is None → returns False"""
    entity = MagicMock()
    desc = {"expr": None, "entity": entity}
    query = _FakeQuery(
        column_descriptions=[desc],
        all_selected_columns=[MagicMock()],
    )

    result = _should_unwrap_scalars_for_query(query)

    assert result is False


def test_should_unwrap_scalars_for_query_single_desc_no_cols_returns_false():
    """Single desc, no columns (empty _all_selected_columns) → returns False"""
    desc = {"expr": MagicMock(), "entity": MagicMock()}
    query = _FakeQuery(
        column_descriptions=[desc],
        all_selected_columns=[],
    )

    result = _should_unwrap_scalars_for_query(query)

    assert result is False


def test_should_unwrap_scalars_for_query_no_descs_returns_false():
    """No column descriptions → returns False"""
    query = _FakeQuery(
        column_descriptions=[],
        all_selected_columns=[],
    )

    result = _should_unwrap_scalars_for_query(query)

    assert result is False
