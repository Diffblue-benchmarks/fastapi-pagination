from __future__ import annotations

import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Inject fake modules into sys.modules *before* importing the extension
# under test, because gino and sqlalchemy are not installed in this env.
# ---------------------------------------------------------------------------

# --- fake gino.crud -------------------------------------------------------
if "gino.crud" not in sys.modules:
    _fake_gino_crud = types.ModuleType("gino.crud")

    class _FakeCRUDModel:
        """Minimal stand-in for gino.crud.CRUDModel."""

        query: MagicMock = MagicMock()

    _fake_gino_crud.CRUDModel = _FakeCRUDModel  # type: ignore[attr-defined]
    sys.modules["gino.crud"] = _fake_gino_crud

if "gino" not in sys.modules:
    _fake_gino = types.ModuleType("gino")
    _fake_gino.crud = sys.modules["gino.crud"]  # type: ignore[attr-defined]
    sys.modules["gino"] = _fake_gino

# --- fake sqlalchemy (minimal surface needed by gino.py directly) ---------
if "sqlalchemy" not in sys.modules:
    _fake_sqla = types.ModuleType("sqlalchemy")
    _fake_sqla.func = MagicMock()
    _fake_sqla.literal_column = MagicMock()
    sys.modules["sqlalchemy"] = _fake_sqla

if "sqlalchemy.sql" not in sys.modules:
    _fake_sqla_sql = types.ModuleType("sqlalchemy.sql")

    class _FakeSelect:
        pass

    _fake_sqla_sql.Select = _FakeSelect  # type: ignore[attr-defined]
    sys.modules["sqlalchemy.sql"] = _fake_sqla_sql

# --- fake fastapi_pagination.ext.sqlalchemy (provides create_paginate_query)
if "fastapi_pagination.ext.sqlalchemy" not in sys.modules:
    _fake_ext_sqla = types.ModuleType("fastapi_pagination.ext.sqlalchemy")
    _fake_ext_sqla.create_paginate_query = MagicMock()  # type: ignore[attr-defined]
    sys.modules["fastapi_pagination.ext.sqlalchemy"] = _fake_ext_sqla

# Now it is safe to import the module under test.
from fastapi_pagination.ext.gino import apaginate, paginate  # noqa: E402

# Grab the CRUDModel class that was injected (for subclass creation in tests).
_CRUDModel = sys.modules["gino.crud"].CRUDModel  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# apaginate – with a plain Select-like query object (not a CRUDModel class)
# Lines covered: 22, 33
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_with_select_query_returns_flow_result():
    mock_query = MagicMock()  # instance, not a class → issubclass branch skipped
    expected = [{"id": 1}]

    with patch("fastapi_pagination.ext.gino.run_async_flow", new_callable=AsyncMock) as mock_flow:
        with patch("fastapi_pagination.ext.gino.generic_flow") as mock_generic:
            mock_flow.return_value = expected
            mock_generic.return_value = MagicMock()

            result = await apaginate(mock_query)

    assert result == expected
    mock_flow.assert_awaited_once()


@pytest.mark.asyncio
async def test_apaginate_forwards_kwargs_to_generic_flow():
    mock_query = MagicMock()
    mock_transformer = AsyncMock()
    mock_additional = {"extra": True}
    mock_config = MagicMock()

    with patch("fastapi_pagination.ext.gino.run_async_flow", new_callable=AsyncMock) as mock_flow:
        with patch("fastapi_pagination.ext.gino.generic_flow") as mock_generic:
            mock_flow.return_value = []
            mock_generic.return_value = MagicMock()

            await apaginate(
                mock_query,
                transformer=mock_transformer,
                additional_data=mock_additional,
                config=mock_config,
            )

    _, kwargs = mock_generic.call_args
    assert kwargs.get("transformer") is mock_transformer
    assert kwargs.get("additional_data") is mock_additional
    assert kwargs.get("config") is mock_config
    assert kwargs.get("async_") is True


# ---------------------------------------------------------------------------
# apaginate – with a CRUDModel subclass (lines 30, 31)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_converts_crud_model_class_to_query():
    inner_query = MagicMock()

    class SomeModel(_CRUDModel):
        query = inner_query

    expected = [{"id": 2}]

    with patch("fastapi_pagination.ext.gino.run_async_flow", new_callable=AsyncMock) as mock_flow:
        with patch("fastapi_pagination.ext.gino.generic_flow") as mock_generic:
            mock_flow.return_value = expected
            mock_generic.return_value = MagicMock()

            result = await apaginate(SomeModel)

    assert result == expected
    mock_flow.assert_awaited_once()


# ---------------------------------------------------------------------------
# paginate – delegates to apaginate (lines 58, 66)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate_with_defaults():
    mock_query = MagicMock()
    expected = [{"id": 3}]

    with patch("fastapi_pagination.ext.gino.apaginate", new_callable=AsyncMock) as mock_apaginate:
        mock_apaginate.return_value = expected

        result = await paginate(mock_query)

    assert result == expected
    mock_apaginate.assert_awaited_once_with(
        mock_query,
        params=None,
        transformer=None,
        additional_data=None,
        config=None,
    )


@pytest.mark.asyncio
async def test_paginate_forwards_all_kwargs_to_apaginate():
    mock_query = MagicMock()
    mock_params = MagicMock()
    mock_transformer = AsyncMock()
    mock_additional = {"key": "value"}
    mock_config = MagicMock()

    with patch("fastapi_pagination.ext.gino.apaginate", new_callable=AsyncMock) as mock_apaginate:
        mock_apaginate.return_value = []

        await paginate(
            mock_query,
            mock_params,
            transformer=mock_transformer,
            additional_data=mock_additional,
            config=mock_config,
        )

    mock_apaginate.assert_awaited_once_with(
        mock_query,
        params=mock_params,
        transformer=mock_transformer,
        additional_data=mock_additional,
        config=mock_config,
    )
