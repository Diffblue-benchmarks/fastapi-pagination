from __future__ import annotations

import warnings
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Query

from fastapi_pagination.ext.sqlalchemy import paginate


class Base:
    pass


# A minimal 10-tuple returned by _old_paginate_sign / _new_paginate_sign
# (query, count_query, conn, params, transformer, additional_data, unique, subquery_count, unwrap_mode, config)
def _make_sign_tuple(conn):
    q = MagicMock()
    return (q, None, conn, None, None, None, True, True, None, None)


# ---------------------------------------------------------------------------
# paginate – old signature (first arg is Query)
# ---------------------------------------------------------------------------


def test_paginate_old_sign_with_sync_conn_calls_run_sync_flow(mocker):
    mock_conn = MagicMock()
    ten_tuple = _make_sign_tuple(mock_conn)

    mocker.patch("fastapi_pagination.ext.sqlalchemy._old_paginate_sign", return_value=ten_tuple)
    # Sync conn → _get_sync_conn_from_async raises TypeError
    mocker.patch("fastapi_pagination.ext.sqlalchemy._get_sync_conn_from_async", side_effect=TypeError)
    mock_run_sync = mocker.patch("fastapi_pagination.ext.sqlalchemy.run_sync_flow", return_value="result")

    mock_query = MagicMock(spec=Query)
    result = paginate(mock_query)

    assert result == "result"
    mock_run_sync.assert_called_once()


# ---------------------------------------------------------------------------
# paginate – new signature (first arg is NOT a Query)
# ---------------------------------------------------------------------------


def test_paginate_new_sign_with_sync_conn_calls_run_sync_flow(mocker):
    mock_conn = MagicMock()
    ten_tuple = _make_sign_tuple(mock_conn)

    mocker.patch("fastapi_pagination.ext.sqlalchemy._new_paginate_sign", return_value=ten_tuple)
    mocker.patch("fastapi_pagination.ext.sqlalchemy._get_sync_conn_from_async", side_effect=TypeError)
    mock_run_sync = mocker.patch("fastapi_pagination.ext.sqlalchemy.run_sync_flow", return_value="sync_page")

    result = paginate(mock_conn, MagicMock())

    assert result == "sync_page"
    mock_run_sync.assert_called_once()


def test_paginate_no_args_falls_back_to_new_sign(mocker):
    mock_conn = MagicMock()
    ten_tuple = _make_sign_tuple(mock_conn)

    mock_new = mocker.patch("fastapi_pagination.ext.sqlalchemy._new_paginate_sign", return_value=ten_tuple)
    mocker.patch("fastapi_pagination.ext.sqlalchemy._get_sync_conn_from_async", side_effect=TypeError)
    mocker.patch("fastapi_pagination.ext.sqlalchemy.run_sync_flow", return_value="no_args_result")

    result = paginate()

    assert result == "no_args_result"
    mock_new.assert_called_once()


# ---------------------------------------------------------------------------
# paginate – async conn path: warns and returns apaginate(...)
# ---------------------------------------------------------------------------


def test_paginate_async_conn_warns_and_returns_apaginate(mocker):
    mock_conn = MagicMock()
    ten_tuple = _make_sign_tuple(mock_conn)

    mocker.patch("fastapi_pagination.ext.sqlalchemy._new_paginate_sign", return_value=ten_tuple)
    # _get_sync_conn_from_async succeeds (returns a sync conn) → async path taken
    mocker.patch("fastapi_pagination.ext.sqlalchemy._get_sync_conn_from_async", return_value=MagicMock())
    mock_apaginate = mocker.patch("fastapi_pagination.ext.sqlalchemy.apaginate", new=MagicMock(return_value="async_page"))

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = paginate(mock_conn, MagicMock())

    assert result == "async_page"
    mock_apaginate.assert_called_once()
    assert any(issubclass(warning.category, DeprecationWarning) for warning in w)


def test_paginate_async_conn_deprecation_message(mocker):
    mock_conn = MagicMock()
    ten_tuple = _make_sign_tuple(mock_conn)

    mocker.patch("fastapi_pagination.ext.sqlalchemy._new_paginate_sign", return_value=ten_tuple)
    mocker.patch("fastapi_pagination.ext.sqlalchemy._get_sync_conn_from_async", return_value=MagicMock())
    mocker.patch("fastapi_pagination.ext.sqlalchemy.apaginate", new=MagicMock(return_value="async_page"))

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        paginate(mock_conn, MagicMock())

    deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
    assert len(deprecation_warnings) >= 1
    assert "apaginate" in str(deprecation_warnings[0].message)
