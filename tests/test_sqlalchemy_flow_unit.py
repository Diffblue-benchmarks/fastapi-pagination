from __future__ import annotations

from functools import partial
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.orm import DeclarativeBase

from fastapi_pagination.api import set_page, set_params
from fastapi_pagination.default import Page, Params
from fastapi_pagination.ext.sqlalchemy import _sqlalchemy_flow
from fastapi_pagination.flow import run_sync_flow


class Base(DeclarativeBase):
    pass


class MyModel(Base):
    __tablename__ = "my_model_flow"
    id = Column(Integer, primary_key=True)
    name = Column(String)


def _make_sync_conn(total: int = 3, items: list[Any] | None = None):
    if items is None:
        items = []
    mock_execute_result = MagicMock()
    mock_execute_result.unique.return_value.all.return_value = items
    conn = MagicMock()
    conn.scalar.return_value = total
    conn.execute.return_value = mock_execute_result
    return conn


# ---------------------------------------------------------------------------
# _sqlalchemy_flow – sync path (is_async=False)
# covers lines 346, 347, 350, 363
# ---------------------------------------------------------------------------


def test_sqlalchemy_flow_sync_returns_page():
    conn = _make_sync_conn(total=0, items=[])

    with set_page(Page):
        with set_params(Params()):
            result = run_sync_flow(
                _sqlalchemy_flow(
                    is_async=False,
                    conn=conn,
                    query=select(MyModel),
                )
            )

    assert result is not None
    assert result.total == 0
    assert result.items == []


def test_sqlalchemy_flow_sync_with_items():
    mock_item = MagicMock()
    mock_item.__iter__ = MagicMock(return_value=iter([mock_item]))
    conn = _make_sync_conn(total=1, items=[(mock_item,)])

    with set_page(Page):
        with set_params(Params()):
            result = run_sync_flow(
                _sqlalchemy_flow(
                    is_async=False,
                    conn=conn,
                    query=select(MyModel),
                    unwrap_mode="no-unwrap",
                )
            )

    assert result is not None
    assert result.total == 1


def test_sqlalchemy_flow_sync_with_explicit_params():
    conn = _make_sync_conn(total=5, items=[])
    params = Params(page=2, size=10)

    with set_page(Page):
        result = run_sync_flow(
            _sqlalchemy_flow(
                is_async=False,
                conn=conn,
                query=select(MyModel),
                params=params,
            )
        )

    assert result is not None
    assert result.total == 5


# ---------------------------------------------------------------------------
# _sqlalchemy_flow – async path (is_async=True)
# covers line 348 (create_page_factory = partial(greenlet_spawn, create_page))
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sqlalchemy_flow_async_uses_greenlet_spawn():
    from fastapi_pagination.flow import run_async_flow

    total_val = 2

    async def async_scalar(_query: Any) -> int:
        return total_val

    async def async_execute(_query: Any) -> Any:
        result = MagicMock()
        result.unique.return_value.all.return_value = []
        return result

    conn = MagicMock()
    conn.scalar = AsyncMock(return_value=total_val)
    conn.execute = AsyncMock(return_value=MagicMock(**{"unique.return_value.all.return_value": []}))

    with set_page(Page):
        with set_params(Params()):
            result = await run_async_flow(
                _sqlalchemy_flow(
                    is_async=True,
                    conn=conn,
                    query=select(MyModel),
                )
            )

    assert result is not None
    assert result.total == total_val
    assert result.items == []


@pytest.mark.asyncio
async def test_sqlalchemy_flow_async_with_explicit_params():
    from fastapi_pagination.flow import run_async_flow

    conn = MagicMock()
    conn.scalar = AsyncMock(return_value=0)
    conn.execute = AsyncMock(return_value=MagicMock(**{"unique.return_value.all.return_value": []}))

    params = Params(page=1, size=20)

    with set_page(Page):
        result = await run_async_flow(
            _sqlalchemy_flow(
                is_async=True,
                conn=conn,
                query=select(MyModel),
                params=params,
            )
        )

    assert result is not None
    assert result.total == 0
