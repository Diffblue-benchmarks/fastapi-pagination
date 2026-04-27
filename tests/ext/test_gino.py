"""Tests for fastapi_pagination.ext.gino.

gino and sqlalchemy are not installed in this environment, so they are mocked
at the sys.modules level before importing the module under test.
"""
import sys
import warnings
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Mock all unavailable dependencies before importing the module under test
# ---------------------------------------------------------------------------

class _MockCRUDModel:
    """Minimal stand-in for gino.crud.CRUDModel."""
    query = MagicMock()


_mock_gino_crud = MagicMock()
_mock_gino_crud.CRUDModel = _MockCRUDModel

_mock_gino = MagicMock()
_mock_gino.crud = _mock_gino_crud

_mock_sqlalchemy_ext = MagicMock()
_mock_sqlalchemy_ext.create_paginate_query = MagicMock()

for _mod, _obj in [
    ("gino", _mock_gino),
    ("gino.crud", _mock_gino_crud),
    ("sqlalchemy", MagicMock()),
    ("sqlalchemy.engine", MagicMock()),
    ("sqlalchemy.exc", MagicMock()),
    ("sqlalchemy.orm", MagicMock()),
    ("sqlalchemy.sql", MagicMock()),
    ("sqlalchemy.sql.elements", MagicMock()),
    ("fastapi_pagination.ext.sqlalchemy", _mock_sqlalchemy_ext),
]:
    sys.modules.setdefault(_mod, _obj)

# Now the module can be imported
from fastapi_pagination.ext.gino import apaginate, paginate  # noqa: E402

from fastapi_pagination.api import set_page  # noqa: E402
from fastapi_pagination.default import Page, Params  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_run_async_flow(mocker):
    return mocker.patch(
        "fastapi_pagination.ext.gino.run_async_flow",
        new_callable=AsyncMock,
        return_value=[{"id": 1}],
    )


@pytest.fixture()
def mock_generic_flow(mocker):
    return mocker.patch(
        "fastapi_pagination.ext.gino.generic_flow",
        return_value=MagicMock(),
    )


# ---------------------------------------------------------------------------
# Tests for apaginate (lines 22, 30, 31, 33)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apaginate_with_select_query(mock_run_async_flow, mock_generic_flow):
    """apaginate with a non-CRUDModel query bypasses the model.query conversion."""
    mock_query = MagicMock()
    # Make it NOT a class so the isinstance(query, type) branch is False
    mock_query.__class__ = object

    params = Params(page=1, size=10)

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await apaginate(mock_query, params=params)

    assert result is mock_run_async_flow.return_value
    mock_run_async_flow.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_with_crud_model_class(mock_run_async_flow, mock_generic_flow):
    """apaginate with a CRUDModel subclass converts it to model.query (line 31)."""

    class MyModel(_MockCRUDModel):
        query = MagicMock()

    params = Params(page=1, size=10)

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await apaginate(MyModel, params=params)

    assert result is mock_run_async_flow.return_value
    # After the conversion, generic_flow should have been called with MyModel.query
    generic_flow_call_kwargs = mock_generic_flow.call_args
    assert generic_flow_call_kwargs is not None
    mock_run_async_flow.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_emits_deprecation_warning(mock_run_async_flow, mock_generic_flow):
    """apaginate emits a DeprecationWarning about gino being unmaintained."""
    mock_query = MagicMock()

    params = Params(page=1, size=10)

    with set_page(Page):
        with pytest.warns(DeprecationWarning, match="gino"):
            await apaginate(mock_query, params=params)


# ---------------------------------------------------------------------------
# Tests for paginate (lines 58, 66)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate(mocker):
    """paginate calls apaginate with identical arguments (line 66)."""
    mock_result = MagicMock()
    mock_apaginate = mocker.patch(
        "fastapi_pagination.ext.gino.apaginate",
        new_callable=AsyncMock,
        return_value=mock_result,
    )

    mock_query = MagicMock()
    params = Params(page=1, size=10)

    with set_page(Page):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await paginate(mock_query, params=params)

    assert result is mock_result
    mock_apaginate.assert_called_once_with(
        mock_query,
        params=params,
        transformer=None,
        additional_data=None,
        config=None,
    )


@pytest.mark.asyncio
async def test_paginate_emits_deprecation_warning(mocker):
    """paginate emits a DeprecationWarning about gino being unmaintained."""
    mocker.patch(
        "fastapi_pagination.ext.gino.apaginate",
        new_callable=AsyncMock,
        return_value=MagicMock(),
    )

    mock_query = MagicMock()
    params = Params(page=1, size=10)

    with set_page(Page):
        with pytest.warns(DeprecationWarning, match="gino"):
            await paginate(mock_query, params=params)
