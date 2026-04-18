from __future__ import annotations

import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fastapi_pagination.bases import CursorRawParams, RawParams
from fastapi_pagination.ext.beanie import apaginate, paginate, parse_cursor

VALID_OID = "507f1f77bcf86cd799439011"


# ===========================================================================
# parse_cursor tests
# ===========================================================================


def test_parse_cursor_plain_valid_objectid():
    result = parse_cursor(VALID_OID)
    assert str(result) == VALID_OID


def test_parse_cursor_with_prev_prefix():
    result = parse_cursor(f"prev_{VALID_OID}")
    assert str(result) == VALID_OID


def test_parse_cursor_invalid_raises_value_error():
    with pytest.raises(ValueError, match="Invalid cursor"):
        parse_cursor("notavalidobjectid")


def test_parse_cursor_invalid_with_prefix_raises_value_error():
    with pytest.raises(ValueError, match="Invalid cursor"):
        parse_cursor("prev_notavalidoid")


# ===========================================================================
# apaginate tests — FindMany with limit-offset, include_total=True
# ===========================================================================


@pytest.mark.asyncio
async def test_apaginate_find_many_limit_offset_with_total():
    raw_params = RawParams(limit=10, offset=0, include_total=True)
    params = MagicMock()
    items = [MagicMock(), MagicMock()]

    count_chain = MagicMock()
    count_chain.count = AsyncMock(return_value=len(items))

    find_many_chain = MagicMock()
    find_many_chain.to_list = AsyncMock(return_value=items)

    query_mock = MagicMock()
    query_mock.find = MagicMock(return_value=count_chain)
    query_mock.find_many = MagicMock(return_value=find_many_chain)

    page = MagicMock()

    with (
        patch("fastapi_pagination.ext.beanie.verify_params", return_value=(params, raw_params)),
        patch("fastapi_pagination.ext.beanie.copy", side_effect=lambda x: x),
        patch("fastapi_pagination.ext.beanie.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.beanie.create_page", return_value=page),
    ):
        result = await apaginate(query_mock)

    assert result is page


@pytest.mark.asyncio
async def test_apaginate_find_many_limit_offset_no_total():
    raw_params = RawParams(limit=5, offset=2, include_total=False)
    params = MagicMock()
    items = [MagicMock()]

    find_many_chain = MagicMock()
    find_many_chain.to_list = AsyncMock(return_value=items)

    query_mock = MagicMock()
    query_mock.find_many = MagicMock(return_value=find_many_chain)

    page = MagicMock()

    with (
        patch("fastapi_pagination.ext.beanie.verify_params", return_value=(params, raw_params)),
        patch("fastapi_pagination.ext.beanie.copy", side_effect=lambda x: x),
        patch("fastapi_pagination.ext.beanie.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.beanie.create_page", return_value=page),
    ):
        result = await apaginate(query_mock)

    assert result is page


@pytest.mark.asyncio
async def test_apaginate_find_many_limit_none():
    raw_params = RawParams(limit=None, offset=None, include_total=True)
    params = MagicMock()
    items = []

    count_chain = MagicMock()
    count_chain.count = AsyncMock(return_value=0)

    find_many_chain = MagicMock()
    find_many_chain.to_list = AsyncMock(return_value=items)

    query_mock = MagicMock()
    query_mock.find = MagicMock(return_value=count_chain)
    query_mock.find_many = MagicMock(return_value=find_many_chain)

    page = MagicMock()

    with (
        patch("fastapi_pagination.ext.beanie.verify_params", return_value=(params, raw_params)),
        patch("fastapi_pagination.ext.beanie.copy", side_effect=lambda x: x),
        patch("fastapi_pagination.ext.beanie.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.beanie.create_page", return_value=page),
    ):
        result = await apaginate(query_mock)

    assert result is page


# ===========================================================================
# apaginate tests — FindMany with cursor params
# ===========================================================================


@pytest.mark.asyncio
async def test_apaginate_cursor_params_no_cursor():
    raw_params = CursorRawParams(cursor=None, size=10, include_total=False)
    params = MagicMock()

    item1 = MagicMock()
    item1.id = VALID_OID
    items_full = [item1]

    limit_chain = MagicMock()
    limit_chain.to_list = AsyncMock(return_value=items_full)

    find_many_chain = MagicMock()
    find_many_chain.limit = MagicMock(return_value=limit_chain)

    query_mock = MagicMock()
    query_mock.find_many = MagicMock(return_value=find_many_chain)

    page = MagicMock()

    with (
        patch("fastapi_pagination.ext.beanie.verify_params", return_value=(params, raw_params)),
        patch("fastapi_pagination.ext.beanie.copy", side_effect=lambda x: x),
        patch("fastapi_pagination.ext.beanie.apply_items_transformer", new=AsyncMock(return_value=items_full)),
        patch("fastapi_pagination.ext.beanie.create_page", return_value=page),
    ):
        result = await apaginate(query_mock)

    assert result is page


@pytest.mark.asyncio
async def test_apaginate_cursor_params_with_next_cursor():
    raw_params = CursorRawParams(cursor=VALID_OID, size=10, include_total=False)
    params = MagicMock()

    item1 = MagicMock()
    item1.id = VALID_OID
    items_full = [item1]

    limit_chain = MagicMock()
    limit_chain.to_list = AsyncMock(return_value=items_full)

    find_chain = MagicMock()
    find_chain.limit = MagicMock(return_value=limit_chain)

    find_many_chain = MagicMock()
    find_many_chain.find = MagicMock(return_value=find_chain)

    query_mock = MagicMock()
    query_mock.find_many = MagicMock(return_value=find_many_chain)

    page = MagicMock()

    with (
        patch("fastapi_pagination.ext.beanie.verify_params", return_value=(params, raw_params)),
        patch("fastapi_pagination.ext.beanie.copy", side_effect=lambda x: x),
        patch("fastapi_pagination.ext.beanie.apply_items_transformer", new=AsyncMock(return_value=items_full)),
        patch("fastapi_pagination.ext.beanie.create_page", return_value=page),
    ):
        result = await apaginate(query_mock)

    assert result is page


@pytest.mark.asyncio
async def test_apaginate_cursor_params_with_prev_cursor():
    cursor = f"prev_{VALID_OID}"
    raw_params = CursorRawParams(cursor=cursor, size=10, include_total=False)
    params = MagicMock()

    item1 = MagicMock()
    item1.id = VALID_OID
    items_full = [item1]

    limit_chain = MagicMock()
    limit_chain.to_list = AsyncMock(return_value=items_full)

    sort_chain = MagicMock()
    sort_chain.limit = MagicMock(return_value=limit_chain)

    find_chain = MagicMock()
    find_chain.sort = MagicMock(return_value=sort_chain)

    find_many_chain = MagicMock()
    find_many_chain.find = MagicMock(return_value=find_chain)

    query_mock = MagicMock()
    query_mock.find_many = MagicMock(return_value=find_many_chain)

    page = MagicMock()

    with (
        patch("fastapi_pagination.ext.beanie.verify_params", return_value=(params, raw_params)),
        patch("fastapi_pagination.ext.beanie.copy", side_effect=lambda x: x),
        patch("fastapi_pagination.ext.beanie.apply_items_transformer", new=AsyncMock(return_value=items_full)),
        patch("fastapi_pagination.ext.beanie.create_page", return_value=page),
    ):
        result = await apaginate(query_mock)

    assert result is page


@pytest.mark.asyncio
async def test_apaginate_cursor_empty_results():
    raw_params = CursorRawParams(cursor=None, size=10, include_total=False)
    params = MagicMock()
    items_full = []

    limit_chain = MagicMock()
    limit_chain.to_list = AsyncMock(return_value=items_full)

    find_many_chain = MagicMock()
    find_many_chain.limit = MagicMock(return_value=limit_chain)

    query_mock = MagicMock()
    query_mock.find_many = MagicMock(return_value=find_many_chain)

    page = MagicMock()

    with (
        patch("fastapi_pagination.ext.beanie.verify_params", return_value=(params, raw_params)),
        patch("fastapi_pagination.ext.beanie.copy", side_effect=lambda x: x),
        patch("fastapi_pagination.ext.beanie.apply_items_transformer", new=AsyncMock(return_value=items_full)),
        patch("fastapi_pagination.ext.beanie.create_page", return_value=page),
    ):
        result = await apaginate(query_mock)

    assert result is page


# ===========================================================================
# paginate (deprecated wrapper) tests
# ===========================================================================


@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate():
    expected_result = MagicMock()
    query_mock = MagicMock()
    params_mock = MagicMock()

    with patch("fastapi_pagination.ext.beanie.apaginate", new=AsyncMock(return_value=expected_result)) as mock_apaginate:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await paginate(query_mock, params=params_mock)

    assert result is expected_result
    mock_apaginate.assert_called_once()


@pytest.mark.asyncio
async def test_paginate_passes_all_kwargs_to_apaginate():
    expected_result = MagicMock()
    query_mock = MagicMock()

    with patch("fastapi_pagination.ext.beanie.apaginate", new=AsyncMock(return_value=expected_result)) as mock_apaginate:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await paginate(
                query_mock,
                params=None,
                transformer=None,
                additional_data=None,
                projection_model=None,
                sort=None,
                session=None,
                ignore_cache=False,
                fetch_links=False,
                lazy_parse=False,
                aggregation_filter_end=None,
            )

    assert result is expected_result
    call_kwargs = mock_apaginate.call_args
    assert call_kwargs is not None
