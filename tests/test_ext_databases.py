"""Tests for fastapi_pagination.ext.databases module."""
from __future__ import annotations

import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Patch unavailable third-party modules before importing the module under test
# ---------------------------------------------------------------------------

def _make_module(name: str) -> types.ModuleType:
    return types.ModuleType(name)


def _install_sqlalchemy_mocks() -> None:
    sa = _make_module("sqlalchemy")
    sa_sql = _make_module("sqlalchemy.sql")
    sa_sql_elements = _make_module("sqlalchemy.sql.elements")
    sa_engine = _make_module("sqlalchemy.engine")
    sa_exc = _make_module("sqlalchemy.exc")
    sa_orm = _make_module("sqlalchemy.orm")

    for attr in ("func", "select", "text", "Column", "Integer", "String", "Table", "MetaData"):
        setattr(sa, attr, MagicMock())
    for attr in ("Select", "CompoundSelect"):
        setattr(sa_sql, attr, MagicMock())
    setattr(sa_sql_elements, "TextClause", MagicMock())
    setattr(sa_engine, "Connection", MagicMock())
    setattr(sa_exc, "InvalidRequestError", Exception)
    for attr in ("Query", "Session", "noload", "scoped_session", "FromStatement"):
        setattr(sa_orm, attr, MagicMock())

    sa.sql = sa_sql
    sa.engine = sa_engine
    sa.exc = sa_exc
    sa.orm = sa_orm

    db_mod = _make_module("databases")
    db_mod.Database = MagicMock()

    mocks = {
        "databases": db_mod,
        "sqlalchemy": sa,
        "sqlalchemy.sql": sa_sql,
        "sqlalchemy.sql.elements": sa_sql_elements,
        "sqlalchemy.engine": sa_engine,
        "sqlalchemy.exc": sa_exc,
        "sqlalchemy.orm": sa_orm,
    }
    for name, mod in mocks.items():
        if name not in sys.modules:
            sys.modules[name] = mod


_install_sqlalchemy_mocks()


# ---------------------------------------------------------------------------
# Helpers shared across tests
# ---------------------------------------------------------------------------

def _make_row(mapping: dict):
    """Return a mock row whose _mapping attribute mirrors a dict."""
    row = MagicMock()
    row._mapping = mapping
    return row


# ---------------------------------------------------------------------------
# _to_mappings
# ---------------------------------------------------------------------------

def test_to_mappings_returns_list_of_dicts():
    from fastapi_pagination.ext.databases import _to_mappings

    rows = [_make_row({"id": 1, "name": "alice"}), _make_row({"id": 2, "name": "bob"})]
    result = _to_mappings(rows)

    assert result == [{"id": 1, "name": "alice"}, {"id": 2, "name": "bob"}]


def test_to_mappings_empty_sequence():
    from fastapi_pagination.ext.databases import _to_mappings

    assert _to_mappings([]) == []


def test_to_mappings_single_item():
    from fastapi_pagination.ext.databases import _to_mappings

    rows = [_make_row({"x": 42})]
    result = _to_mappings(rows)

    assert result == [{"x": 42}]


# ---------------------------------------------------------------------------
# apaginate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_apaginate_calls_run_async_flow():
    """apaginate should delegate to run_async_flow / generic_flow."""
    mock_page = MagicMock()
    mock_db = MagicMock()
    mock_query = MagicMock()

    with (
        patch("fastapi_pagination.ext.databases.run_async_flow", new_callable=AsyncMock, return_value=mock_page) as mock_run,
        patch("fastapi_pagination.ext.databases.generic_flow", return_value=MagicMock()) as mock_gflow,
        patch("fastapi_pagination.ext.databases.flow_expr", side_effect=lambda f: f) as _mock_fexpr,
        patch("fastapi_pagination.ext.databases.create_count_query", return_value=MagicMock()),
        patch("fastapi_pagination.ext.databases.create_paginate_query", return_value=MagicMock()),
    ):
        from fastapi_pagination.ext.databases import apaginate

        result = await apaginate(mock_db, mock_query)

    assert result is mock_page
    mock_run.assert_awaited_once()
    mock_gflow.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_convert_to_mapping_true_sets_inner_transformer():
    """When convert_to_mapping=True the inner_transformer should be _to_mappings."""
    mock_page = MagicMock()
    captured = {}

    async def fake_run(gen):
        return mock_page

    def fake_gflow(**kwargs):
        captured.update(kwargs)
        return MagicMock()

    with (
        patch("fastapi_pagination.ext.databases.run_async_flow", side_effect=fake_run),
        patch("fastapi_pagination.ext.databases.generic_flow", side_effect=fake_gflow),
        patch("fastapi_pagination.ext.databases.flow_expr", side_effect=lambda f: f),
        patch("fastapi_pagination.ext.databases.create_count_query", return_value=MagicMock()),
        patch("fastapi_pagination.ext.databases.create_paginate_query", return_value=MagicMock()),
    ):
        from fastapi_pagination.ext.databases import _to_mappings, apaginate

        await apaginate(MagicMock(), MagicMock(), convert_to_mapping=True)

    assert captured.get("inner_transformer") is _to_mappings


@pytest.mark.asyncio
async def test_apaginate_convert_to_mapping_false_leaves_inner_transformer_none():
    """When convert_to_mapping=False inner_transformer should be None."""
    captured = {}

    async def fake_run(gen):
        return MagicMock()

    def fake_gflow(**kwargs):
        captured.update(kwargs)
        return MagicMock()

    with (
        patch("fastapi_pagination.ext.databases.run_async_flow", side_effect=fake_run),
        patch("fastapi_pagination.ext.databases.generic_flow", side_effect=fake_gflow),
        patch("fastapi_pagination.ext.databases.flow_expr", side_effect=lambda f: f),
        patch("fastapi_pagination.ext.databases.create_count_query", return_value=MagicMock()),
        patch("fastapi_pagination.ext.databases.create_paginate_query", return_value=MagicMock()),
    ):
        from fastapi_pagination.ext.databases import apaginate

        await apaginate(MagicMock(), MagicMock(), convert_to_mapping=False)

    assert captured.get("inner_transformer") is None


# ---------------------------------------------------------------------------
# paginate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate():
    """paginate should forward all arguments to apaginate and return its result."""
    mock_page = MagicMock()
    mock_db = MagicMock()
    mock_query = MagicMock()

    with patch("fastapi_pagination.ext.databases.apaginate", new_callable=AsyncMock, return_value=mock_page) as mock_ap:
        from fastapi_pagination.ext.databases import paginate

        result = await paginate(mock_db, mock_query, convert_to_mapping=False)

    assert result is mock_page
    mock_ap.assert_awaited_once_with(
        mock_db,
        mock_query,
        params=None,
        transformer=None,
        additional_data=None,
        convert_to_mapping=False,
        use_subquery=True,
        config=None,
    )


@pytest.mark.asyncio
async def test_paginate_passes_params_through():
    """paginate should pass optional params down to apaginate."""
    mock_page = MagicMock()
    mock_params = MagicMock()

    with patch("fastapi_pagination.ext.databases.apaginate", new_callable=AsyncMock, return_value=mock_page) as mock_ap:
        from fastapi_pagination.ext.databases import paginate

        result = await paginate(MagicMock(), MagicMock(), params=mock_params)

    assert result is mock_page
    _, call_kwargs = mock_ap.call_args
    assert call_kwargs.get("params") is mock_params
