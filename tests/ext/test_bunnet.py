"""
Tests for fastapi_pagination.ext.bunnet.paginate

bunnet is not installed in this environment, so we mock all bunnet modules
at the sys.modules level before importing the extension.
"""
import sys
from unittest.mock import MagicMock


def _install_bunnet_mocks():
    """Install mock bunnet modules into sys.modules so the extension can be imported."""

    class _AggregationQuery:
        def __class_getitem__(cls, item):
            return cls

    class _FindMany:
        def __class_getitem__(cls, item):
            return cls

    bunnet_mod = MagicMock()
    bunnet_mod.Document = MagicMock()

    enums_mod = MagicMock()
    interfaces_aggregate_mod = MagicMock()
    interfaces_aggregate_mod.ClientSession = MagicMock()
    interfaces_aggregate_mod.DocumentProjectionType = MagicMock()

    queries_aggregation_mod = MagicMock()
    queries_aggregation_mod.AggregationQuery = _AggregationQuery

    queries_find_mod = MagicMock()
    queries_find_mod.FindMany = _FindMany

    mocks = {
        "bunnet": bunnet_mod,
        "bunnet.odm": MagicMock(),
        "bunnet.odm.enums": enums_mod,
        "bunnet.odm.interfaces": MagicMock(),
        "bunnet.odm.interfaces.aggregate": interfaces_aggregate_mod,
        "bunnet.odm.queries": MagicMock(),
        "bunnet.odm.queries.aggregation": queries_aggregation_mod,
        "bunnet.odm.queries.find": queries_find_mod,
    }
    sys.modules.update(mocks)
    return _AggregationQuery


# Install mocks before importing the module under test
AggregationQuery = _install_bunnet_mocks()

from fastapi_pagination.ext.bunnet import paginate  # noqa: E402
from fastapi_pagination.bases import RawParams  # noqa: E402

import pytest  # noqa: E402
from unittest.mock import patch  # noqa: E402


def make_params_and_raw(limit=10, offset=0, include_total=True):
    params = MagicMock()
    raw_params = RawParams(limit=limit, offset=offset, include_total=include_total)
    return params, raw_params


def make_aggr_query(pipeline=None):
    clone = MagicMock()
    clone.aggregation_pipeline = list(pipeline) if pipeline is not None else []
    q = MagicMock()
    q.aggregation_pipeline = pipeline if pipeline is not None else []
    q.clone.return_value = clone
    # Make isinstance(q, AggregationQuery) return True
    q.__class__ = AggregationQuery
    return q


@pytest.fixture
def mock_create_page():
    with patch.object(
        sys.modules["fastapi_pagination.ext.bunnet"],
        "create_page",
    ) as m:
        m.return_value = MagicMock(name="page_result")
        yield m


@pytest.fixture
def mock_apply_transformer():
    with patch.object(
        sys.modules["fastapi_pagination.ext.bunnet"],
        "apply_items_transformer",
        side_effect=lambda items, transformer: items,
    ) as m:
        yield m


class TestPaginateFindMany:
    def test_find_many_with_total(self, mock_create_page, mock_apply_transformer, mocker):
        params, raw_params = make_params_and_raw(limit=5, offset=2, include_total=True)
        mocker.patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw_params))

        find_many_result = MagicMock()
        find_many_result.to_list.return_value = ["item1", "item2"]

        query = MagicMock()
        query.find_many.return_value = find_many_result
        query.find.return_value.count.return_value = 10

        result = paginate(query, params)

        query.find_many.assert_called_once_with(
            limit=5,
            skip=2,
            projection_model=None,
            sort=None,
            session=None,
            ignore_cache=False,
            fetch_links=False,
            lazy_parse=False,
        )
        query.find.assert_called_once()
        mock_apply_transformer.assert_called_once_with(["item1", "item2"], None)
        mock_create_page.assert_called_once_with(["item1", "item2"], total=10, params=params)
        assert result == mock_create_page.return_value

    def test_find_many_without_total(self, mock_create_page, mock_apply_transformer, mocker):
        params, raw_params = make_params_and_raw(limit=5, offset=0, include_total=False)
        mocker.patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw_params))

        find_many_result = MagicMock()
        find_many_result.to_list.return_value = ["item1"]

        query = MagicMock()
        query.find_many.return_value = find_many_result

        result = paginate(query, params)

        query.find.assert_not_called()
        mock_create_page.assert_called_once_with(["item1"], total=None, params=params)
        assert result == mock_create_page.return_value

    def test_find_many_extra_kwargs_forwarded(self, mock_create_page, mock_apply_transformer, mocker):
        params, raw_params = make_params_and_raw(limit=3, offset=1, include_total=True)
        mocker.patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw_params))

        find_many_result = MagicMock()
        find_many_result.to_list.return_value = []

        query = MagicMock()
        query.find_many.return_value = find_many_result
        query.find.return_value.count.return_value = 0

        paginate(query, params, session="my_session", ignore_cache=True)

        query.find_many.assert_called_once_with(
            limit=3,
            skip=1,
            projection_model=None,
            sort=None,
            session="my_session",
            ignore_cache=True,
            fetch_links=False,
            lazy_parse=False,
        )

    def test_find_many_projection_and_sort(self, mock_create_page, mock_apply_transformer, mocker):
        params, raw_params = make_params_and_raw(limit=10, offset=0, include_total=True)
        mocker.patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw_params))

        find_many_result = MagicMock()
        find_many_result.to_list.return_value = []

        query = MagicMock()
        query.find_many.return_value = find_many_result
        query.find.return_value.count.return_value = 0

        proj = MagicMock()
        paginate(query, params, projection_model=proj, sort="name")

        query.find_many.assert_called_once_with(
            limit=10,
            skip=0,
            projection_model=proj,
            sort="name",
            session=None,
            ignore_cache=False,
            fetch_links=False,
            lazy_parse=False,
        )

    def test_find_many_items_transformer_applied(self, mock_create_page, mocker):
        params, raw_params = make_params_and_raw(limit=5, offset=0, include_total=True)
        mocker.patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw_params))

        find_many_result = MagicMock()
        find_many_result.to_list.return_value = ["a", "b"]

        query = MagicMock()
        query.find_many.return_value = find_many_result
        query.find.return_value.count.return_value = 2

        transformer = MagicMock(return_value=["A", "B"])

        with patch.object(
            sys.modules["fastapi_pagination.ext.bunnet"],
            "apply_items_transformer",
            side_effect=lambda items, t: t(items) if t else items,
        ) as mock_t:
            paginate(query, params, transformer=transformer)
            mock_t.assert_called_once_with(["a", "b"], transformer)

        mock_create_page.assert_called_once_with(["A", "B"], total=2, params=params)

    def test_find_many_additional_data(self, mock_create_page, mock_apply_transformer, mocker):
        params, raw_params = make_params_and_raw(limit=5, offset=0, include_total=True)
        mocker.patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw_params))

        find_many_result = MagicMock()
        find_many_result.to_list.return_value = []

        query = MagicMock()
        query.find_many.return_value = find_many_result
        query.find.return_value.count.return_value = 0

        paginate(query, params, additional_data={"meta": "data"})

        mock_create_page.assert_called_once_with([], total=0, params=params, meta="data")


class TestPaginateAggregation:
    def test_aggregation_no_filter_end(self, mock_create_page, mock_apply_transformer, mocker):
        params, raw_params = make_params_and_raw(limit=5, offset=2, include_total=True)
        mocker.patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw_params))

        q = make_aggr_query()
        clone = q.clone.return_value
        clone.to_list.return_value = [{"data": ["item1", "item2"], "metadata": [{"total": 10}]}]

        result = paginate(q, params)

        facet_stage = clone.aggregation_pipeline[-1]
        assert "$facet" in facet_stage
        assert {"$limit": 7} in facet_stage["$facet"]["data"]
        assert {"$skip": 2} in facet_stage["$facet"]["data"]
        mock_create_page.assert_called_once_with(["item1", "item2"], total=10, params=params)
        assert result == mock_create_page.return_value

    def test_aggregation_no_limit(self, mock_create_page, mock_apply_transformer, mocker):
        params, raw_params = make_params_and_raw(limit=None, offset=3, include_total=True)
        mocker.patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw_params))

        q = make_aggr_query()
        clone = q.clone.return_value
        clone.to_list.return_value = [{"data": ["x"], "metadata": [{"total": 1}]}]

        paginate(q, params)

        facet_stage = clone.aggregation_pipeline[-1]
        data_pipeline = facet_stage["$facet"]["data"]
        assert not any("$limit" in s for s in data_pipeline)
        assert {"$skip": 3} in data_pipeline

    def test_aggregation_no_offset(self, mock_create_page, mock_apply_transformer, mocker):
        params, raw_params = make_params_and_raw(limit=5, offset=None, include_total=True)
        mocker.patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw_params))

        q = make_aggr_query()
        clone = q.clone.return_value
        clone.to_list.return_value = [{"data": [], "metadata": [{"total": 0}]}]

        paginate(q, params)

        facet_stage = clone.aggregation_pipeline[-1]
        data_pipeline = facet_stage["$facet"]["data"]
        assert {"$limit": 5} in data_pipeline
        assert not any("$skip" in s for s in data_pipeline)

    def test_aggregation_empty_metadata_total_zero(self, mock_create_page, mock_apply_transformer, mocker):
        params, raw_params = make_params_and_raw(limit=5, offset=0, include_total=True)
        mocker.patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw_params))

        q = make_aggr_query()
        clone = q.clone.return_value
        clone.to_list.return_value = [{"data": [], "metadata": []}]

        paginate(q, params)

        mock_create_page.assert_called_once_with([], total=0, params=params)

    def test_aggregation_numeric_filter_end(self, mock_create_page, mock_apply_transformer, mocker):
        params, raw_params = make_params_and_raw(limit=5, offset=1, include_total=True)
        mocker.patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw_params))

        initial_pipeline = [{"$match": {"a": 1}}, {"$project": {"b": 1}}]
        q = make_aggr_query(pipeline=initial_pipeline)
        clone = q.clone.return_value
        clone.aggregation_pipeline = list(initial_pipeline)
        clone.to_list.return_value = [{"data": ["item"], "metadata": [{"total": 5}]}]

        paginate(q, params, aggregation_filter_end=1)

        pipeline = clone.aggregation_pipeline
        assert pipeline[0] == {"$match": {"a": 1}}
        facet_stage = pipeline[1]
        assert "$facet" in facet_stage
        # transform_part (pipeline[1:]) is included in facet data
        assert {"$project": {"b": 1}} in facet_stage["$facet"]["data"]

    def test_aggregation_auto_filter_end(self, mock_create_page, mock_apply_transformer, mocker):
        params, raw_params = make_params_and_raw(limit=5, offset=0, include_total=True)
        mocker.patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw_params))
        mocker.patch(
            "fastapi_pagination.ext.bunnet.get_mongo_pipeline_filter_end",
            return_value=1,
        )

        initial_pipeline = [{"$match": {"x": 1}}, {"$project": {"y": 1}}]
        q = make_aggr_query(pipeline=initial_pipeline)
        clone = q.clone.return_value
        clone.aggregation_pipeline = list(initial_pipeline)
        clone.to_list.return_value = [{"data": [], "metadata": []}]

        paginate(q, params, aggregation_filter_end="auto")

        pipeline = clone.aggregation_pipeline
        assert any("$facet" in stage for stage in pipeline)

    def test_aggregation_pipeline_transformer_applied(self, mock_create_page, mock_apply_transformer, mocker):
        params, raw_params = make_params_and_raw(limit=5, offset=0, include_total=True)
        mocker.patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw_params))

        q = make_aggr_query()
        clone = q.clone.return_value
        clone.to_list.return_value = [{"data": ["x"], "metadata": [{"total": 1}]}]

        transformed = [{"$custom": True}]
        pipeline_transformer = MagicMock(return_value=transformed)

        paginate(q, params, aggregation_pipeline_transformer=pipeline_transformer)

        pipeline_transformer.assert_called_once()
        assert clone.aggregation_pipeline == transformed

    def test_aggregation_no_pipeline_transformer(self, mock_create_page, mock_apply_transformer, mocker):
        params, raw_params = make_params_and_raw(limit=5, offset=0, include_total=True)
        mocker.patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw_params))

        q = make_aggr_query()
        clone = q.clone.return_value
        clone.to_list.return_value = [{"data": [], "metadata": [{"total": 0}]}]

        # No transformer should not raise
        paginate(q, params, aggregation_pipeline_transformer=None)

        mock_create_page.assert_called_once()

    def test_aggregation_additional_data(self, mock_create_page, mock_apply_transformer, mocker):
        params, raw_params = make_params_and_raw(limit=5, offset=0, include_total=True)
        mocker.patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw_params))

        q = make_aggr_query()
        clone = q.clone.return_value
        clone.to_list.return_value = [{"data": [], "metadata": [{"total": 0}]}]

        paginate(q, params, additional_data={"extra": "value"})

        mock_create_page.assert_called_once_with([], total=0, params=params, extra="value")
