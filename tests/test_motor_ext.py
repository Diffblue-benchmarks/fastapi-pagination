from __future__ import annotations

import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fastapi_pagination.bases import RawParams


# ===========================================================================
# apaginate tests
# ===========================================================================


@pytest.mark.asyncio
async def test_apaginate_with_total():
    raw_params = RawParams(limit=10, offset=0, include_total=True)
    params = MagicMock()
    items = [{"_id": "1"}, {"_id": "2"}]

    cursor_mock = MagicMock()
    cursor_mock.to_list = AsyncMock(return_value=items)

    collection_mock = MagicMock()
    collection_mock.count_documents = AsyncMock(return_value=2)
    collection_mock.find = MagicMock(return_value=cursor_mock)

    page = MagicMock()

    with (
        patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw_params)),
        patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.motor.create_page", return_value=page),
        warnings.catch_warnings(),
    ):
        warnings.simplefilter("ignore", DeprecationWarning)
        from fastapi_pagination.ext.motor import apaginate
        result = await apaginate(collection_mock)

    assert result is page


@pytest.mark.asyncio
async def test_apaginate_without_total():
    raw_params = RawParams(limit=5, offset=2, include_total=False)
    params = MagicMock()
    items = [{"_id": "1"}]

    cursor_mock = MagicMock()
    cursor_mock.to_list = AsyncMock(return_value=items)

    collection_mock = MagicMock()
    collection_mock.find = MagicMock(return_value=cursor_mock)

    page = MagicMock()

    with (
        patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw_params)),
        patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.motor.create_page", return_value=page),
        warnings.catch_warnings(),
    ):
        warnings.simplefilter("ignore", DeprecationWarning)
        from fastapi_pagination.ext.motor import apaginate
        result = await apaginate(collection_mock)

    assert result is page
    collection_mock.count_documents.assert_not_called()


@pytest.mark.asyncio
async def test_apaginate_with_sort_tuple():
    raw_params = RawParams(limit=10, offset=0, include_total=False)
    params = MagicMock()
    items = [{"_id": "1"}]

    sorted_cursor_mock = MagicMock()
    sorted_cursor_mock.to_list = AsyncMock(return_value=items)

    cursor_mock = MagicMock()
    cursor_mock.sort = MagicMock(return_value=sorted_cursor_mock)

    collection_mock = MagicMock()
    collection_mock.find = MagicMock(return_value=cursor_mock)

    page = MagicMock()

    with (
        patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw_params)),
        patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.motor.create_page", return_value=page),
        warnings.catch_warnings(),
    ):
        warnings.simplefilter("ignore", DeprecationWarning)
        from fastapi_pagination.ext.motor import apaginate
        result = await apaginate(collection_mock, sort=("name", 1))

    assert result is page
    cursor_mock.sort.assert_called_once_with("name", 1)


@pytest.mark.asyncio
async def test_apaginate_with_sort_non_tuple():
    raw_params = RawParams(limit=10, offset=0, include_total=False)
    params = MagicMock()
    items = [{"_id": "1"}]

    sorted_cursor_mock = MagicMock()
    sorted_cursor_mock.to_list = AsyncMock(return_value=items)

    cursor_mock = MagicMock()
    cursor_mock.sort = MagicMock(return_value=sorted_cursor_mock)

    collection_mock = MagicMock()
    collection_mock.find = MagicMock(return_value=cursor_mock)

    page = MagicMock()

    with (
        patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw_params)),
        patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.motor.create_page", return_value=page),
        warnings.catch_warnings(),
    ):
        warnings.simplefilter("ignore", DeprecationWarning)
        from fastapi_pagination.ext.motor import apaginate
        result = await apaginate(collection_mock, sort=[("name", 1)])

    assert result is page
    cursor_mock.sort.assert_called_once_with([("name", 1)])


@pytest.mark.asyncio
async def test_apaginate_with_query_filter():
    raw_params = RawParams(limit=10, offset=0, include_total=True)
    params = MagicMock()
    items = [{"_id": "1"}]
    query_filter = {"status": "active"}

    cursor_mock = MagicMock()
    cursor_mock.to_list = AsyncMock(return_value=items)

    collection_mock = MagicMock()
    collection_mock.count_documents = AsyncMock(return_value=1)
    collection_mock.find = MagicMock(return_value=cursor_mock)

    page = MagicMock()

    with (
        patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw_params)),
        patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.motor.create_page", return_value=page),
        warnings.catch_warnings(),
    ):
        warnings.simplefilter("ignore", DeprecationWarning)
        from fastapi_pagination.ext.motor import apaginate
        result = await apaginate(collection_mock, query_filter=query_filter)

    assert result is page
    collection_mock.count_documents.assert_called_once_with(query_filter)


# ===========================================================================
# apaginate_aggregate tests
# ===========================================================================


@pytest.mark.asyncio
async def test_apaginate_aggregate_basic():
    raw_params = RawParams(limit=10, offset=0, include_total=True)
    params = MagicMock()
    items = [{"_id": "1"}]
    data = {"data": items, "metadata": [{"total": 1}]}

    cursor_mock = MagicMock()
    cursor_mock.to_list = AsyncMock(return_value=[data])

    collection_mock = MagicMock()
    collection_mock.aggregate = MagicMock(return_value=cursor_mock)

    page = MagicMock()

    with (
        patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw_params)),
        patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.motor.create_page", return_value=page),
        warnings.catch_warnings(),
    ):
        warnings.simplefilter("ignore", DeprecationWarning)
        from fastapi_pagination.ext.motor import apaginate_aggregate
        result = await apaginate_aggregate(collection_mock)

    assert result is page


@pytest.mark.asyncio
async def test_apaginate_aggregate_empty_metadata():
    raw_params = RawParams(limit=10, offset=0, include_total=True)
    params = MagicMock()
    items = []
    data = {"data": items, "metadata": []}

    cursor_mock = MagicMock()
    cursor_mock.to_list = AsyncMock(return_value=[data])

    collection_mock = MagicMock()
    collection_mock.aggregate = MagicMock(return_value=cursor_mock)

    page = MagicMock()

    with (
        patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw_params)),
        patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.motor.create_page", return_value=page) as mock_create_page,
        warnings.catch_warnings(),
    ):
        warnings.simplefilter("ignore", DeprecationWarning)
        from fastapi_pagination.ext.motor import apaginate_aggregate
        result = await apaginate_aggregate(collection_mock)

    assert result is page
    mock_create_page.assert_called_once()
    call_kwargs = mock_create_page.call_args
    assert call_kwargs.kwargs.get("total", call_kwargs.args[1] if len(call_kwargs.args) > 1 else None) == 0 or \
           call_kwargs.kwargs.get("total") == 0


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_pipeline():
    raw_params = RawParams(limit=5, offset=2, include_total=True)
    params = MagicMock()
    items = [{"_id": "1"}]
    data = {"data": items, "metadata": [{"total": 10}]}

    cursor_mock = MagicMock()
    cursor_mock.to_list = AsyncMock(return_value=[data])

    collection_mock = MagicMock()
    collection_mock.aggregate = MagicMock(return_value=cursor_mock)

    page = MagicMock()
    pipeline_input = [{"$match": {"status": "active"}}]

    with (
        patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw_params)),
        patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.motor.create_page", return_value=page),
        warnings.catch_warnings(),
    ):
        warnings.simplefilter("ignore", DeprecationWarning)
        from fastapi_pagination.ext.motor import apaginate_aggregate
        result = await apaginate_aggregate(collection_mock, aggregate_pipeline=pipeline_input)

    assert result is page


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_filter_end_auto():
    raw_params = RawParams(limit=5, offset=2, include_total=True)
    params = MagicMock()
    items = [{"_id": "1"}]
    data = {"data": items, "metadata": [{"total": 10}]}

    cursor_mock = MagicMock()
    cursor_mock.to_list = AsyncMock(return_value=[data])

    collection_mock = MagicMock()
    collection_mock.aggregate = MagicMock(return_value=cursor_mock)

    page = MagicMock()
    pipeline_input = [{"$match": {"status": "active"}}, {"$group": {"_id": "$name"}}]

    with (
        patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw_params)),
        patch("fastapi_pagination.ext.motor.get_mongo_pipeline_filter_end", return_value=1),
        patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.motor.create_page", return_value=page),
        warnings.catch_warnings(),
    ):
        warnings.simplefilter("ignore", DeprecationWarning)
        from fastapi_pagination.ext.motor import apaginate_aggregate
        result = await apaginate_aggregate(
            collection_mock,
            aggregate_pipeline=pipeline_input,
            aggregation_filter_end="auto",
        )

    assert result is page


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_filter_end_int():
    raw_params = RawParams(limit=5, offset=2, include_total=True)
    params = MagicMock()
    items = [{"_id": "1"}]
    data = {"data": items, "metadata": [{"total": 10}]}

    cursor_mock = MagicMock()
    cursor_mock.to_list = AsyncMock(return_value=[data])

    collection_mock = MagicMock()
    collection_mock.aggregate = MagicMock(return_value=cursor_mock)

    page = MagicMock()
    pipeline_input = [{"$match": {"status": "active"}}, {"$group": {"_id": "$name"}}]

    with (
        patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw_params)),
        patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.motor.create_page", return_value=page),
        warnings.catch_warnings(),
    ):
        warnings.simplefilter("ignore", DeprecationWarning)
        from fastapi_pagination.ext.motor import apaginate_aggregate
        result = await apaginate_aggregate(
            collection_mock,
            aggregate_pipeline=pipeline_input,
            aggregation_filter_end=1,
        )

    assert result is page


@pytest.mark.asyncio
async def test_apaginate_aggregate_with_pipeline_transformer():
    raw_params = RawParams(limit=10, offset=0, include_total=True)
    params = MagicMock()
    items = [{"_id": "1"}]
    data = {"data": items, "metadata": [{"total": 1}]}

    cursor_mock = MagicMock()
    cursor_mock.to_list = AsyncMock(return_value=[data])

    collection_mock = MagicMock()
    collection_mock.aggregate = MagicMock(return_value=cursor_mock)

    page = MagicMock()
    transformed_pipeline = [{"$match": {}}, {"$facet": {"metadata": [], "data": []}}]
    pipeline_transformer = MagicMock(return_value=transformed_pipeline)

    with (
        patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw_params)),
        patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.motor.create_page", return_value=page),
        warnings.catch_warnings(),
    ):
        warnings.simplefilter("ignore", DeprecationWarning)
        from fastapi_pagination.ext.motor import apaginate_aggregate
        result = await apaginate_aggregate(
            collection_mock,
            aggregation_pipeline_transformer=pipeline_transformer,
        )

    assert result is page
    pipeline_transformer.assert_called_once()


@pytest.mark.asyncio
async def test_apaginate_aggregate_limit_none():
    raw_params = RawParams(limit=None, offset=None, include_total=True)
    params = MagicMock()
    items = []
    data = {"data": items, "metadata": []}

    cursor_mock = MagicMock()
    cursor_mock.to_list = AsyncMock(return_value=[data])

    collection_mock = MagicMock()
    collection_mock.aggregate = MagicMock(return_value=cursor_mock)

    page = MagicMock()

    with (
        patch("fastapi_pagination.ext.motor.verify_params", return_value=(params, raw_params)),
        patch("fastapi_pagination.ext.motor.apply_items_transformer", new=AsyncMock(return_value=items)),
        patch("fastapi_pagination.ext.motor.create_page", return_value=page),
        warnings.catch_warnings(),
    ):
        warnings.simplefilter("ignore", DeprecationWarning)
        from fastapi_pagination.ext.motor import apaginate_aggregate
        result = await apaginate_aggregate(collection_mock)

    assert result is page


# ===========================================================================
# paginate (deprecated wrapper) tests
# ===========================================================================


@pytest.mark.asyncio
async def test_paginate_delegates_to_apaginate():
    expected_result = MagicMock()
    collection_mock = MagicMock()

    with patch("fastapi_pagination.ext.motor.apaginate", new=AsyncMock(return_value=expected_result)) as mock_apaginate:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from fastapi_pagination.ext.motor import paginate
            result = await paginate(collection_mock)

    assert result is expected_result
    mock_apaginate.assert_called_once()


@pytest.mark.asyncio
async def test_paginate_passes_kwargs_to_apaginate():
    expected_result = MagicMock()
    collection_mock = MagicMock()
    query_filter = {"status": "active"}
    sort_val = ("name", 1)

    with patch("fastapi_pagination.ext.motor.apaginate", new=AsyncMock(return_value=expected_result)) as mock_apaginate:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from fastapi_pagination.ext.motor import paginate
            result = await paginate(collection_mock, query_filter=query_filter, sort=sort_val)

    assert result is expected_result
    call_kwargs = mock_apaginate.call_args
    assert call_kwargs is not None


# ===========================================================================
# paginate_aggregate (deprecated wrapper) tests
# ===========================================================================


@pytest.mark.asyncio
async def test_paginate_aggregate_delegates_to_apaginate_aggregate():
    expected_result = MagicMock()
    collection_mock = MagicMock()

    with patch(
        "fastapi_pagination.ext.motor.apaginate_aggregate", new=AsyncMock(return_value=expected_result)
    ) as mock_apaginate_aggregate:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from fastapi_pagination.ext.motor import paginate_aggregate
            result = await paginate_aggregate(collection_mock)

    assert result is expected_result
    mock_apaginate_aggregate.assert_called_once()


@pytest.mark.asyncio
async def test_paginate_aggregate_passes_args_to_apaginate_aggregate():
    expected_result = MagicMock()
    collection_mock = MagicMock()
    pipeline = [{"$match": {"status": "active"}}]

    with patch(
        "fastapi_pagination.ext.motor.apaginate_aggregate", new=AsyncMock(return_value=expected_result)
    ) as mock_apaginate_aggregate:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from fastapi_pagination.ext.motor import paginate_aggregate
            result = await paginate_aggregate(collection_mock, aggregate_pipeline=pipeline)

    assert result is expected_result
    call_kwargs = mock_apaginate_aggregate.call_args
    assert call_kwargs is not None
