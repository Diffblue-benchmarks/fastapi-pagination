from __future__ import annotations

import sys
import types
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _install_missing_mocks():
    """Install mock modules for optional dependencies not installed in this env."""
    if "databases" not in sys.modules:
        mock_db_mod = types.ModuleType("databases")
        mock_db_mod.Database = MagicMock  # type: ignore[attr-defined]
        sys.modules["databases"] = mock_db_mod

    if "sqlalchemy" not in sys.modules:
        sq = types.ModuleType("sqlalchemy")
        sq_sql = types.ModuleType("sqlalchemy.sql")
        sq_sql.Select = MagicMock  # type: ignore[attr-defined]
        sys.modules["sqlalchemy"] = sq
        sys.modules["sqlalchemy.sql"] = sq_sql

    if "fastapi_pagination.ext.sqlalchemy" not in sys.modules:
        mock_sa_ext = types.ModuleType("fastapi_pagination.ext.sqlalchemy")
        mock_sa_ext.create_count_query = MagicMock()  # type: ignore[attr-defined]
        mock_sa_ext.create_paginate_query = MagicMock()  # type: ignore[attr-defined]
        sys.modules["fastapi_pagination.ext.sqlalchemy"] = mock_sa_ext


_install_missing_mocks()

# Force re-import if already cached without the mocked deps
if "fastapi_pagination.ext.databases" in sys.modules:
    del sys.modules["fastapi_pagination.ext.databases"]


def _make_row(mapping: dict):
    row = MagicMock()
    row._mapping = mapping
    return row


def test_to_mappings_basic():
    from fastapi_pagination.ext.databases import _to_mappings

    rows = [_make_row({"id": 1, "name": "Alice"}), _make_row({"id": 2, "name": "Bob"})]
    result = _to_mappings(rows)

    assert result == [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]


def test_to_mappings_empty():
    from fastapi_pagination.ext.databases import _to_mappings

    result = _to_mappings([])

    assert result == []


def test_to_mappings_single():
    from fastapi_pagination.ext.databases import _to_mappings

    rows = [_make_row({"key": "value"})]
    result = _to_mappings(rows)

    assert result == [{"key": "value"}]


@pytest.mark.asyncio
async def test_apaginate_with_convert_to_mapping_true():
    from fastapi_pagination.ext.databases import _to_mappings, apaginate

    db = MagicMock()
    query = MagicMock()
    captured = {}

    with patch("fastapi_pagination.ext.databases.generic_flow") as mock_generic_flow:
        mock_generic_flow.return_value = MagicMock()
        with patch("fastapi_pagination.ext.databases.run_async_flow", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = "page_result"

            with pytest.warns(DeprecationWarning):
                result = await apaginate(db, query, convert_to_mapping=True)

            assert result == "page_result"
            kwargs = mock_generic_flow.call_args[1]
            captured["inner_transformer"] = kwargs.get("inner_transformer")

    assert captured["inner_transformer"] is _to_mappings


@pytest.mark.asyncio
async def test_apaginate_with_convert_to_mapping_false():
    from fastapi_pagination.ext.databases import apaginate

    db = MagicMock()
    query = MagicMock()
    captured = {}

    with patch("fastapi_pagination.ext.databases.generic_flow") as mock_generic_flow:
        mock_generic_flow.return_value = MagicMock()
        with patch("fastapi_pagination.ext.databases.run_async_flow", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = []

            with pytest.warns(DeprecationWarning):
                result = await apaginate(db, query, convert_to_mapping=False)

            assert result == []
            kwargs = mock_generic_flow.call_args[1]
            captured["inner_transformer"] = kwargs.get("inner_transformer")

    assert captured["inner_transformer"] is None


@pytest.mark.asyncio
async def test_apaginate_passes_params_to_generic_flow():
    from fastapi_pagination.ext.databases import apaginate

    db = MagicMock()
    query = MagicMock()
    params = MagicMock()
    transformer = AsyncMock()
    additional_data = {"extra": "data"}
    config = MagicMock()
    captured = {}

    with patch("fastapi_pagination.ext.databases.generic_flow") as mock_generic_flow:
        mock_generic_flow.return_value = MagicMock()
        with patch("fastapi_pagination.ext.databases.run_async_flow", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = "result"

            with pytest.warns(DeprecationWarning):
                await apaginate(
                    db,
                    query,
                    params=params,
                    transformer=transformer,
                    additional_data=additional_data,
                    convert_to_mapping=False,
                    use_subquery=False,
                    config=config,
                )

            kwargs = mock_generic_flow.call_args[1]
            captured.update(kwargs)

    assert captured["params"] is params
    assert captured["transformer"] is transformer
    assert captured["additional_data"] is additional_data
    assert captured["config"] is config
    assert captured["async_"] is True


@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate():
    from fastapi_pagination.ext.databases import paginate

    db = MagicMock()
    query = MagicMock()

    with patch("fastapi_pagination.ext.databases.apaginate", new_callable=AsyncMock) as mock_apaginate:
        mock_apaginate.return_value = "page_result"

        with pytest.warns(DeprecationWarning):
            result = await paginate(db, query)

        assert result == "page_result"
        mock_apaginate.assert_called_once_with(
            db,
            query,
            params=None,
            transformer=None,
            additional_data=None,
            convert_to_mapping=True,
            use_subquery=True,
            config=None,
        )


@pytest.mark.asyncio
async def test_paginate_passes_all_kwargs():
    from fastapi_pagination.ext.databases import paginate

    db = MagicMock()
    query = MagicMock()
    params = MagicMock()
    transformer = AsyncMock()
    additional_data = {"extra": "data"}
    config = MagicMock()

    with patch("fastapi_pagination.ext.databases.apaginate", new_callable=AsyncMock) as mock_apaginate:
        mock_apaginate.return_value = "result"

        with pytest.warns(DeprecationWarning):
            await paginate(
                db,
                query,
                params=params,
                transformer=transformer,
                additional_data=additional_data,
                convert_to_mapping=False,
                use_subquery=False,
                config=config,
            )

        mock_apaginate.assert_called_once_with(
            db,
            query,
            params=params,
            transformer=transformer,
            additional_data=additional_data,
            convert_to_mapping=False,
            use_subquery=False,
            config=config,
        )
