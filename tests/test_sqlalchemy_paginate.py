from __future__ import annotations

import sys
import warnings
from unittest.mock import MagicMock, patch

# Mock sqlalchemy and related modules before importing fastapi_pagination.ext.sqlalchemy
# to handle environments where sqlalchemy is not installed
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

from fastapi_pagination import Page, Params, set_page, set_params
from fastapi_pagination.ext.sqlalchemy import paginate


@pytest.fixture
def pagination_ctx():
    with set_page(Page):
        with set_params(Params(page=1, size=10)):
            yield


def make_mock_query():
    query = MagicMock()
    query._statement_20.return_value = MagicMock()
    return query


def test_paginate_new_sign_sync_conn_calls_run_sync_flow(mocker, pagination_ctx):
    """Test paginate with sync conn calls run_sync_flow (line 478)"""
    mock_page = MagicMock()
    mock_run = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.run_sync_flow",
        return_value=mock_page,
    )
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._get_sync_conn_from_async",
        side_effect=TypeError("not an async conn"),
    )

    conn = MagicMock()
    query = make_mock_query()

    result = paginate(conn, query)

    assert result is mock_page
    mock_run.assert_called_once()


def test_paginate_new_sign_async_conn_warns_and_calls_apaginate(mocker, pagination_ctx):
    """Test paginate with async conn issues DeprecationWarning and calls apaginate (lines 459, 465)"""
    mock_page = MagicMock()
    # Use new_callable=MagicMock to avoid AsyncMock (apaginate is async def)
    mock_apaginate = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.apaginate",
        new_callable=MagicMock,
        return_value=mock_page,
    )
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._get_sync_conn_from_async",
        return_value=MagicMock(),  # no TypeError → async path
    )

    conn = MagicMock()
    query = make_mock_query()

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = paginate(conn, query)

    assert result is mock_page
    mock_apaginate.assert_called_once()
    assert any(issubclass(warning.category, DeprecationWarning) for warning in w)


def test_paginate_old_sign_dispatches_to_old_paginate_sign(mocker, pagination_ctx):
    """Test paginate dispatches to _old_paginate_sign when first arg is a Query (lines 444-448)"""
    mock_page = MagicMock()
    mock_conn = MagicMock()

    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.run_sync_flow",
        return_value=mock_page,
    )
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._get_sync_conn_from_async",
        side_effect=TypeError("not async"),
    )
    mock_old_sign = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._old_paginate_sign",
        return_value=(MagicMock(), None, mock_conn, None, None, None, True, True, None, None),
    )

    # Use a real class so isinstance check in paginate passes
    class FakeQuery:
        session = mock_conn

        def _statement_20(self):
            return MagicMock()

    with patch("fastapi_pagination.ext.sqlalchemy.Query", FakeQuery):
        query_instance = FakeQuery()
        result = paginate(query_instance)

    mock_old_sign.assert_called_once_with(query_instance)
    assert result is mock_page


def test_paginate_async_conn_passes_kwargs_to_apaginate(mocker, pagination_ctx):
    """Test paginate passes all relevant kwargs to apaginate when conn is async"""
    mock_page = MagicMock()
    # Use new_callable=MagicMock to avoid AsyncMock (apaginate is async def)
    mock_apaginate = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.apaginate",
        new_callable=MagicMock,
        return_value=mock_page,
    )
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._get_sync_conn_from_async",
        return_value=MagicMock(),
    )

    conn = MagicMock()
    query = make_mock_query()

    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        result = paginate(conn, query, unique=False, subquery_count=False)

    assert result is mock_page
    call_kwargs = mock_apaginate.call_args[1]
    assert call_kwargs.get("unique") is False
    assert call_kwargs.get("subquery_count") is False


def test_paginate_new_sign_with_params(mocker, pagination_ctx):
    """Test paginate with explicit params passes them through"""
    mock_page = MagicMock()
    mock_run = mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.run_sync_flow",
        return_value=mock_page,
    )
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._get_sync_conn_from_async",
        side_effect=TypeError("not async"),
    )

    conn = MagicMock()
    query = make_mock_query()
    params = Params(page=2, size=20)

    result = paginate(conn, query, params=params)

    assert result is mock_page
    mock_run.assert_called_once()


def test_paginate_async_conn_deprecation_warning_message(mocker, pagination_ctx):
    """Test that the deprecation warning contains expected text"""
    # Use new_callable=MagicMock to avoid AsyncMock (apaginate is async def)
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy.apaginate",
        new_callable=MagicMock,
        return_value=MagicMock(),
    )
    mocker.patch(
        "fastapi_pagination.ext.sqlalchemy._get_sync_conn_from_async",
        return_value=MagicMock(),
    )

    conn = MagicMock()
    query = make_mock_query()

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        paginate(conn, query)

    assert len(w) >= 1
    deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
    assert any("apaginate" in str(warning.message) for warning in deprecation_warnings)
