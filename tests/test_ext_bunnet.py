import warnings
from unittest.mock import MagicMock, patch

import pytest

from fastapi_pagination import Page, Params
from fastapi_pagination.api import set_page, set_params
from fastapi_pagination.ext.bunnet import paginate


def make_mock_find_many_query(items, total=None):
    mock_query = MagicMock()
    mock_find_many_result = MagicMock()
    mock_find_many_result.to_list.return_value = items
    mock_query.find_many.return_value = mock_find_many_result
    if total is not None:
        mock_query.find.return_value.count.return_value = total
    return mock_query


def make_mock_aggregation_query(items, metadata_total=None):
    from bunnet.odm.queries.aggregation import AggregationQuery

    mock_agg = MagicMock(spec=AggregationQuery)
    mock_agg.aggregation_pipeline = []

    cloned = MagicMock(spec=AggregationQuery)
    cloned.aggregation_pipeline = []

    if metadata_total is not None:
        cloned.to_list.return_value = [{"data": items, "metadata": [{"total": metadata_total}]}]
    else:
        cloned.to_list.return_value = [{"data": items, "metadata": []}]

    mock_agg.clone.return_value = cloned
    return mock_agg, cloned


@pytest.fixture(autouse=True)
def suppress_deprecation():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        yield


def test_paginate_find_many_basic():
    items = [{"id": 1}, {"id": 2}]
    query = make_mock_find_many_query(items, total=2)

    with set_page(Page):
        with set_params(Params(page=1, size=10)):
            result = paginate(query)

    assert result.items == items
    assert result.total == 2


def test_paginate_find_many_calls_find_many_with_params():
    items = [{"id": 1}]
    query = make_mock_find_many_query(items, total=1)

    with set_page(Page):
        with set_params(Params(page=1, size=5)):
            paginate(query)

    query.find_many.assert_called_once_with(
        limit=5,
        skip=0,
        projection_model=None,
        sort=None,
        session=None,
        ignore_cache=False,
        fetch_links=False,
        lazy_parse=False,
    )


def test_paginate_find_many_include_total_false():
    items = [{"id": 1}, {"id": 2}]
    query = make_mock_find_many_query(items)

    with set_page(Page):
        with set_params(Params(page=1, size=10)):
            with patch("fastapi_pagination.ext.bunnet.verify_params") as mock_verify:
                from fastapi_pagination.bases import RawParams
                mock_params = MagicMock()
                mock_raw = RawParams(limit=10, offset=0, include_total=False)
                mock_verify.return_value = (mock_params, mock_raw)

                with patch("fastapi_pagination.ext.bunnet.apply_items_transformer", return_value=items):
                    with patch("fastapi_pagination.ext.bunnet.create_page") as mock_create_page:
                        mock_create_page.return_value = MagicMock()
                        paginate(query)

                mock_create_page.assert_called_once()
                call_kwargs = mock_create_page.call_args[1]
                assert call_kwargs["total"] is None


def test_paginate_find_many_with_transformer():
    items = [{"id": 1}, {"id": 2}]
    query = make_mock_find_many_query(items, total=2)
    transformer = lambda x: [{"transformed": True}]  # noqa: E731

    with set_page(Page):
        with set_params(Params(page=1, size=10)):
            result = paginate(query, transformer=transformer)

    assert result.items == [{"transformed": True}]


def test_paginate_aggregation_basic():
    items = [{"name": "foo"}, {"name": "bar"}]
    mock_agg, cloned = make_mock_aggregation_query(items, metadata_total=5)

    with set_page(Page):
        with set_params(Params(page=1, size=10)):
            result = paginate(mock_agg)

    assert result.items == items
    assert result.total == 5


def test_paginate_aggregation_empty_metadata_total_zero():
    items = []
    mock_agg, cloned = make_mock_aggregation_query(items, metadata_total=None)

    with set_page(Page):
        with set_params(Params(page=1, size=10)):
            result = paginate(mock_agg)

    assert result.items == []
    assert result.total == 0


def test_paginate_aggregation_builds_pipeline_with_limit_offset():
    items = [{"id": 1}]
    mock_agg, cloned = make_mock_aggregation_query(items, metadata_total=1)
    cloned.aggregation_pipeline = []

    with set_page(Page):
        with set_params(Params(page=1, size=5)):
            paginate(mock_agg)

    pipeline = cloned.aggregation_pipeline
    assert any("$facet" in stage for stage in pipeline)
    facet_stage = next(s for s in pipeline if "$facet" in s)
    assert "metadata" in facet_stage["$facet"]
    assert "data" in facet_stage["$facet"]


def test_paginate_aggregation_with_filter_end_int():
    from bunnet.odm.queries.aggregation import AggregationQuery

    items = [{"id": 1}]
    mock_agg = MagicMock(spec=AggregationQuery)
    mock_agg.aggregation_pipeline = [{"$match": {"active": True}}, {"$project": {"name": 1}}]

    cloned = MagicMock(spec=AggregationQuery)
    cloned.aggregation_pipeline = [{"$match": {"active": True}}, {"$project": {"name": 1}}]
    cloned.to_list.return_value = [{"data": items, "metadata": [{"total": 1}]}]
    mock_agg.clone.return_value = cloned

    with set_page(Page):
        with set_params(Params(page=1, size=10)):
            result = paginate(mock_agg, aggregation_filter_end=1)

    assert result.items == items
    assert result.total == 1


def test_paginate_aggregation_with_filter_end_auto():
    from bunnet.odm.queries.aggregation import AggregationQuery

    items = [{"id": 2}]
    mock_agg = MagicMock(spec=AggregationQuery)
    mock_agg.aggregation_pipeline = [{"$match": {"x": 1}}, {"$project": {"name": 1}}]

    cloned = MagicMock(spec=AggregationQuery)
    cloned.aggregation_pipeline = [{"$match": {"x": 1}}, {"$project": {"name": 1}}]
    cloned.to_list.return_value = [{"data": items, "metadata": [{"total": 3}]}]
    mock_agg.clone.return_value = cloned

    with set_page(Page):
        with set_params(Params(page=1, size=10)):
            result = paginate(mock_agg, aggregation_filter_end="auto")

    assert result.items == items
    assert result.total == 3


def test_paginate_aggregation_with_pipeline_transformer():
    from bunnet.odm.queries.aggregation import AggregationQuery

    items = [{"id": 1}]
    mock_agg = MagicMock(spec=AggregationQuery)
    mock_agg.aggregation_pipeline = []

    cloned = MagicMock(spec=AggregationQuery)
    cloned.aggregation_pipeline = []
    cloned.to_list.return_value = [{"data": items, "metadata": [{"total": 1}]}]
    mock_agg.clone.return_value = cloned

    transformed_pipeline = [{"$match": {}}, {"$facet": {"metadata": [], "data": []}}]
    pipeline_transformer = MagicMock(return_value=transformed_pipeline)

    with set_page(Page):
        with set_params(Params(page=1, size=10)):
            paginate(mock_agg, aggregation_pipeline_transformer=pipeline_transformer)

    pipeline_transformer.assert_called_once()


def test_paginate_aggregation_with_additional_data():
    items = [{"id": 1}]
    mock_agg, cloned = make_mock_aggregation_query(items, metadata_total=1)

    with set_page(Page):
        with set_params(Params(page=1, size=10)):
            result = paginate(mock_agg, additional_data={})

    assert result.items == items


def test_paginate_find_many_second_page():
    items = [{"id": 11}]
    query = make_mock_find_many_query(items, total=15)

    with set_page(Page):
        with set_params(Params(page=2, size=10)):
            result = paginate(query)

    assert result.items == items
    assert result.total == 15
    query.find_many.assert_called_once_with(
        limit=10,
        skip=10,
        projection_model=None,
        sort=None,
        session=None,
        ignore_cache=False,
        fetch_links=False,
        lazy_parse=False,
    )
