from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest


# ──────────────────────────────────────────────────────────────────────────────
# gino is an optional (unmaintained) dependency not installed in this environment.
# sqlalchemy is also not installed in this environment.
# Inject minimal mock modules into sys.modules BEFORE importing the extension so
# that the top-level imports in ext/gino.py succeed.
# ──────────────────────────────────────────────────────────────────────────────


class _FakeCRUDModel:
    """Stand-in for gino.crud.CRUDModel."""

    query: MagicMock = MagicMock()


_fake_gino_crud = MagicMock(name="gino.crud")
_fake_gino_crud.CRUDModel = _FakeCRUDModel

sys.modules.setdefault("gino", MagicMock(name="gino"))
sys.modules.setdefault("gino.crud", _fake_gino_crud)

# sqlalchemy stubs — gino.py imports func, literal_column and Select directly
_fake_sqlalchemy = MagicMock(name="sqlalchemy")
_fake_sqlalchemy_sql = MagicMock(name="sqlalchemy.sql")
sys.modules.setdefault("sqlalchemy", _fake_sqlalchemy)
sys.modules.setdefault("sqlalchemy.sql", _fake_sqlalchemy_sql)
sys.modules.setdefault("sqlalchemy.engine", MagicMock(name="sqlalchemy.engine"))
sys.modules.setdefault("sqlalchemy.exc", MagicMock(name="sqlalchemy.exc"))
sys.modules.setdefault("sqlalchemy.orm", MagicMock(name="sqlalchemy.orm"))
sys.modules.setdefault("sqlalchemy.sql.elements", MagicMock(name="sqlalchemy.sql.elements"))
sys.modules.setdefault("sqlalchemy.util", MagicMock(name="sqlalchemy.util"))
sys.modules.setdefault("sqlalchemy.ext", MagicMock(name="sqlalchemy.ext"))
sys.modules.setdefault("sqlalchemy.ext.asyncio", MagicMock(name="sqlalchemy.ext.asyncio"))

# fastapi_pagination.ext.sqlalchemy also imports sqlalchemy heavily.
# Mock it so that "from .sqlalchemy import create_paginate_query" succeeds.
_fake_ext_sqlalchemy = MagicMock(name="fastapi_pagination.ext.sqlalchemy")
sys.modules.setdefault("fastapi_pagination.ext.sqlalchemy", _fake_ext_sqlalchemy)

# Safe to import the extension now that all mocks are in place.
from fastapi_pagination.ext.gino import apaginate, paginate  # noqa: E402


# ──────────────────────────────────────────────────────────────────────────────
# Helper: a concrete subclass of _FakeCRUDModel, mimicking a Gino Model class
# ──────────────────────────────────────────────────────────────────────────────


class _FakeModel(_FakeCRUDModel):
    """Fake Gino Model class: issubclass(_FakeModel, _FakeCRUDModel) is True."""

    query: MagicMock = MagicMock()


# ──────────────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_apaginate_with_plain_query_does_not_reassign_query(mocker):
    """When query is not a CRUDModel subclass, it is used as-is."""
    mock_query = MagicMock()
    mock_result = MagicMock()
    mock_run_async = mocker.patch(
        "fastapi_pagination.ext.gino.run_async_flow",
        new_callable=AsyncMock,
        return_value=mock_result,
    )

    result = await apaginate(mock_query)

    assert result is mock_result
    mock_run_async.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_with_crud_model_class_uses_model_query(mocker):
    """When query is a CRUDModel subclass class, apaginate replaces it with model.query."""
    mock_result = MagicMock()
    mocker.patch(
        "fastapi_pagination.ext.gino.run_async_flow",
        new_callable=AsyncMock,
        return_value=mock_result,
    )
    _FakeModel.query = MagicMock()

    result = await apaginate(_FakeModel)

    assert result is mock_result


@pytest.mark.asyncio
async def test_apaginate_returns_value_from_run_async_flow(mocker):
    """The return value of apaginate is exactly what run_async_flow returns."""
    mock_query = MagicMock()
    expected = {"items": [1, 2, 3], "total": 3}
    mocker.patch(
        "fastapi_pagination.ext.gino.run_async_flow",
        new_callable=AsyncMock,
        return_value=expected,
    )

    result = await apaginate(mock_query)

    assert result == expected


@pytest.mark.asyncio
async def test_apaginate_forwards_optional_args_to_generic_flow(mocker):
    """transformer, additional_data and config are forwarded to generic_flow."""
    mock_query = MagicMock()
    mock_generic = mocker.patch(
        "fastapi_pagination.ext.gino.generic_flow",
        return_value=MagicMock(),
    )
    mocker.patch(
        "fastapi_pagination.ext.gino.run_async_flow",
        new_callable=AsyncMock,
        return_value=MagicMock(),
    )

    transformer = AsyncMock()
    additional_data = {"key": "value"}
    config = MagicMock()

    await apaginate(mock_query, transformer=transformer, additional_data=additional_data, config=config)

    _, kwargs = mock_generic.call_args
    assert kwargs["transformer"] is transformer
    assert kwargs["additional_data"] is additional_data
    assert kwargs["config"] is config


@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate(mocker):
    """paginate should call apaginate with the same arguments."""
    mock_query = MagicMock()
    mock_result = MagicMock()
    mock_apaginate = mocker.patch(
        "fastapi_pagination.ext.gino.apaginate",
        new_callable=AsyncMock,
        return_value=mock_result,
    )

    result = await paginate(mock_query)

    assert result is mock_result
    mock_apaginate.assert_called_once()


@pytest.mark.asyncio
async def test_paginate_returns_value_from_apaginate(mocker):
    """The return value of paginate matches what apaginate returns."""
    mock_query = MagicMock()
    expected = [{"id": 1}, {"id": 2}]
    mocker.patch(
        "fastapi_pagination.ext.gino.apaginate",
        new_callable=AsyncMock,
        return_value=expected,
    )

    result = await paginate(mock_query)

    assert result == expected
