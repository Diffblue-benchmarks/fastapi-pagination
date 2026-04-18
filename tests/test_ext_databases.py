from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from fastapi_pagination.ext.databases import _to_mappings, apaginate, paginate


# --- _to_mappings ---

def test_to_mappings_returns_list_of_dicts():
    row1 = MagicMock()
    row1._mapping = {"id": 1, "name": "Alice"}
    row2 = MagicMock()
    row2._mapping = {"id": 2, "name": "Bob"}

    result = _to_mappings([row1, row2])

    assert result == [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]


def test_to_mappings_empty_sequence():
    result = _to_mappings([])
    assert result == []


# --- apaginate ---

@pytest.mark.asyncio
async def test_apaginate_with_convert_to_mapping_true(mocker):
    mock_run = mocker.patch(
        "fastapi_pagination.ext.databases.run_async_flow",
        new_callable=AsyncMock,
        return_value={"items": [], "total": 0},
    )
    mock_generic_flow = mocker.patch(
        "fastapi_pagination.ext.databases.generic_flow",
        return_value="flow_sentinel",
    )

    db = MagicMock()
    query = MagicMock()

    result = await apaginate(db, query, convert_to_mapping=True)

    assert result == {"items": [], "total": 0}
    mock_run.assert_awaited_once_with("flow_sentinel")
    call_kwargs = mock_generic_flow.call_args.kwargs
    assert call_kwargs["inner_transformer"] is _to_mappings


@pytest.mark.asyncio
async def test_apaginate_with_convert_to_mapping_false(mocker):
    mock_run = mocker.patch(
        "fastapi_pagination.ext.databases.run_async_flow",
        new_callable=AsyncMock,
        return_value={"items": [], "total": 0},
    )
    mock_generic_flow = mocker.patch(
        "fastapi_pagination.ext.databases.generic_flow",
        return_value="flow_sentinel",
    )

    db = MagicMock()
    query = MagicMock()

    await apaginate(db, query, convert_to_mapping=False)

    call_kwargs = mock_generic_flow.call_args.kwargs
    assert call_kwargs["inner_transformer"] is None


# --- paginate ---

@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate(mocker):
    mock_apaginate = mocker.patch(
        "fastapi_pagination.ext.databases.apaginate",
        new_callable=AsyncMock,
        return_value="paginated_result",
    )

    db = MagicMock()
    query = MagicMock()

    result = await paginate(db, query)

    assert result == "paginated_result"
    mock_apaginate.assert_awaited_once_with(
        db,
        query,
        params=None,
        transformer=None,
        additional_data=None,
        convert_to_mapping=True,
        use_subquery=True,
        config=None,
    )
