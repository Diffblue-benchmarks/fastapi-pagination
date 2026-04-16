from __future__ import annotations

import sys
import warnings
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock sqlmodel and its submodules before importing the extension
_sqlmodel_mock = ModuleType("sqlmodel")
_sqlmodel_sql_mock = ModuleType("sqlmodel.sql")
_sqlmodel_sql_expression_mock = ModuleType("sqlmodel.sql.expression")
_sqlmodel_sql_cls_mock = ModuleType("sqlmodel.sql._expression_select_cls")


class _MockSelect:
    def __class_getitem__(cls, item):
        return cls


class _MockSelectOfScalar:
    def __class_getitem__(cls, item):
        return cls


class _MockSelectBase:
    def __class_getitem__(cls, item):
        return cls


class _MockSQLModel:
    pass


class _MockSession:
    pass


def _mock_select(model):
    result = _MockSelect()
    result._model = model
    return result


_sqlmodel_mock.Session = _MockSession
_sqlmodel_mock.SQLModel = _MockSQLModel
_sqlmodel_mock.select = _mock_select
_sqlmodel_sql_expression_mock.Select = _MockSelect
_sqlmodel_sql_expression_mock.SelectOfScalar = _MockSelectOfScalar
_sqlmodel_sql_cls_mock.SelectBase = _MockSelectBase

sys.modules.setdefault("sqlmodel", _sqlmodel_mock)
sys.modules.setdefault("sqlmodel.sql", _sqlmodel_sql_mock)
sys.modules.setdefault("sqlmodel.sql.expression", _sqlmodel_sql_expression_mock)
sys.modules.setdefault("sqlmodel.sql._expression_select_cls", _sqlmodel_sql_cls_mock)
sys.modules.pop("fastapi_pagination.ext.sqlmodel", None)

from fastapi_pagination import Params  # noqa: E402
from fastapi_pagination.ext.sqlmodel import _prepare_query, apaginate, paginate  # noqa: E402


class TestPrepareQuery:
    def test_prepare_query_with_select_returns_unchanged(self):
        query = _MockSelect()

        result = _prepare_query(query)

        assert result is query

    def test_prepare_query_with_select_of_scalar_returns_unchanged(self):
        query = _MockSelectOfScalar()

        result = _prepare_query(query)

        assert result is query

    def test_prepare_query_with_model_class_calls_select(self):
        class MyModel(_MockSQLModel):
            pass

        result = _prepare_query(MyModel)

        assert isinstance(result, _MockSelect)
        assert result._model is MyModel


class TestPaginate:
    def test_paginate_with_sync_session_calls_underlying_paginate(self):
        session = _MockSession()
        query = _MockSelect()
        params = Params(page=1, size=10)

        mock_page = MagicMock()
        with patch("fastapi_pagination.ext.sqlmodel._paginate", return_value=mock_page) as mock_paginate:
            result = paginate(session, query, params)

        mock_paginate.assert_called_once()
        assert result is mock_page

    def test_paginate_with_sync_session_passes_prepared_query(self):
        session = _MockSession()
        params = Params(page=1, size=10)

        class MyModel(_MockSQLModel):
            pass

        with patch("fastapi_pagination.ext.sqlmodel._paginate", return_value=MagicMock()) as mock_paginate:
            paginate(session, MyModel, params)

        call_args = mock_paginate.call_args
        passed_query = call_args[0][1]
        assert isinstance(passed_query, _MockSelect)
        assert passed_query._model is MyModel

    def test_paginate_with_sync_session_passes_prepared_count_query(self):
        session = _MockSession()
        query = _MockSelect()
        count_query = _MockSelect()
        params = Params(page=1, size=10)

        with patch("fastapi_pagination.ext.sqlmodel._paginate", return_value=MagicMock()) as mock_paginate:
            paginate(session, query, params, count_query=count_query)

        call_kwargs = mock_paginate.call_args[1]
        assert call_kwargs["count_query"] is count_query

    def test_paginate_with_sync_session_prepares_model_count_query(self):
        session = _MockSession()
        query = _MockSelect()
        params = Params(page=1, size=10)

        class MyModel(_MockSQLModel):
            pass

        with patch("fastapi_pagination.ext.sqlmodel._paginate", return_value=MagicMock()) as mock_paginate:
            paginate(session, query, params, count_query=MyModel)

        call_kwargs = mock_paginate.call_args[1]
        assert isinstance(call_kwargs["count_query"], _MockSelect)
        assert call_kwargs["count_query"]._model is MyModel

    def test_paginate_with_async_session_emits_deprecation_warning(self):
        from sqlalchemy.ext.asyncio import AsyncSession

        session = MagicMock(spec=AsyncSession)
        query = _MockSelect()
        params = Params(page=1, size=10)

        mock_coro = AsyncMock()
        with patch("fastapi_pagination.ext.sqlmodel.apaginate", new=mock_coro):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                paginate(session, query, params)

        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_warnings) >= 1
        assert "apaginate" in str(deprecation_warnings[0].message).lower()

    def test_paginate_with_async_session_returns_apaginate_result(self):
        from sqlalchemy.ext.asyncio import AsyncSession

        session = MagicMock(spec=AsyncSession)
        query = _MockSelect()
        params = Params(page=1, size=10)

        mock_coroutine = MagicMock()
        mock_apaginate = MagicMock(return_value=mock_coroutine)
        with patch("fastapi_pagination.ext.sqlmodel.apaginate", new=mock_apaginate):
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                result = paginate(session, query, params)

        assert result is mock_coroutine


class TestApaginate:
    @pytest.mark.asyncio
    async def test_apaginate_calls_underlying_apaginate(self):
        from sqlalchemy.ext.asyncio import AsyncSession

        session = MagicMock(spec=AsyncSession)
        query = _MockSelect()
        params = Params(page=1, size=10)

        mock_page = MagicMock()
        with patch("fastapi_pagination.ext.sqlmodel._apaginate", new=AsyncMock(return_value=mock_page)) as mock:
            result = await apaginate(session, query, params)

        assert result is mock_page

    @pytest.mark.asyncio
    async def test_apaginate_prepares_model_query(self):
        from sqlalchemy.ext.asyncio import AsyncSession

        session = MagicMock(spec=AsyncSession)
        params = Params(page=1, size=10)

        class MyModel(_MockSQLModel):
            pass

        with patch("fastapi_pagination.ext.sqlmodel._apaginate", new=AsyncMock(return_value=MagicMock())) as mock:
            await apaginate(session, MyModel, params)

        call_args = mock.call_args
        passed_query = call_args[0][1]
        assert isinstance(passed_query, _MockSelect)
        assert passed_query._model is MyModel

    @pytest.mark.asyncio
    async def test_apaginate_with_count_query_prepares_it(self):
        from sqlalchemy.ext.asyncio import AsyncSession

        session = MagicMock(spec=AsyncSession)
        query = _MockSelect()
        params = Params(page=1, size=10)

        class MyModel(_MockSQLModel):
            pass

        with patch("fastapi_pagination.ext.sqlmodel._apaginate", new=AsyncMock(return_value=MagicMock())) as mock:
            await apaginate(session, query, params, count_query=MyModel)

        call_kwargs = mock.call_args[1]
        assert isinstance(call_kwargs["count_query"], _MockSelect)
        assert call_kwargs["count_query"]._model is MyModel

    @pytest.mark.asyncio
    async def test_apaginate_without_count_query_passes_none(self):
        from sqlalchemy.ext.asyncio import AsyncSession

        session = MagicMock(spec=AsyncSession)
        query = _MockSelect()
        params = Params(page=1, size=10)

        with patch("fastapi_pagination.ext.sqlmodel._apaginate", new=AsyncMock(return_value=MagicMock())) as mock:
            await apaginate(session, query, params)

        call_kwargs = mock.call_args[1]
        assert call_kwargs["count_query"] is None
