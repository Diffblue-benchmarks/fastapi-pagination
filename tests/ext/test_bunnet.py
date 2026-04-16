"""Unit tests for fastapi_pagination.ext.bunnet.paginate"""
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


def _setup_bunnet_mocks():
    """Install mock bunnet modules into sys.modules before the paginate module is loaded."""
    if "bunnet" in sys.modules:
        return

    bunnet_mod = types.ModuleType("bunnet")
    bunnet_odm = types.ModuleType("bunnet.odm")
    bunnet_odm_enums = types.ModuleType("bunnet.odm.enums")
    bunnet_odm_interfaces = types.ModuleType("bunnet.odm.interfaces")
    bunnet_odm_interfaces_aggregate = types.ModuleType("bunnet.odm.interfaces.aggregate")
    bunnet_odm_queries = types.ModuleType("bunnet.odm.queries")
    bunnet_odm_queries_aggregation = types.ModuleType("bunnet.odm.queries.aggregation")
    bunnet_odm_queries_find = types.ModuleType("bunnet.odm.queries.find")

    class _Document:
        pass

    class _SortDirection:
        ASCENDING = 1
        DESCENDING = -1

    class _AggregationQuery:
        def __class_getitem__(cls, item):
            return cls

    class _FindMany:
        def __class_getitem__(cls, item):
            return cls

    class _ClientSession:
        pass

    bunnet_mod.Document = _Document
    bunnet_odm_enums.SortDirection = _SortDirection
    bunnet_odm_interfaces_aggregate.ClientSession = _ClientSession
    bunnet_odm_interfaces_aggregate.DocumentProjectionType = object
    bunnet_odm_queries_aggregation.AggregationQuery = _AggregationQuery
    bunnet_odm_queries_find.FindMany = _FindMany

    sys.modules["bunnet"] = bunnet_mod
    sys.modules["bunnet.odm"] = bunnet_odm
    sys.modules["bunnet.odm.enums"] = bunnet_odm_enums
    sys.modules["bunnet.odm.interfaces"] = bunnet_odm_interfaces
    sys.modules["bunnet.odm.interfaces.aggregate"] = bunnet_odm_interfaces_aggregate
    sys.modules["bunnet.odm.queries"] = bunnet_odm_queries
    sys.modules["bunnet.odm.queries.aggregation"] = bunnet_odm_queries_aggregation
    sys.modules["bunnet.odm.queries.find"] = bunnet_odm_queries_find


_setup_bunnet_mocks()

# Now safe to import
from fastapi_pagination.bases import RawParams  # noqa: E402
from fastapi_pagination.ext.bunnet import paginate  # noqa: E402


def _make_raw_params(limit=10, offset=0, include_total=True):
    return RawParams(limit=limit, offset=offset, include_total=include_total)


def _make_mock_params(raw_params):
    mock_params = MagicMock()
    mock_params.to_raw_params.return_value = raw_params
    return mock_params


@pytest.fixture()
def mock_page():
    return MagicMock(name="page")


def _paginate_patches():
    """Return a context manager tuple that patches the helpers inside ext.bunnet."""
    return (
        patch("fastapi_pagination.ext.bunnet.verify_params"),
        patch("fastapi_pagination.ext.bunnet.apply_items_transformer"),
        patch("fastapi_pagination.ext.bunnet.create_page"),
    )


# ---------------------------------------------------------------------------
# AggregationQuery path
# ---------------------------------------------------------------------------


class TestPaginateAggregationQuery:
    def _make_aggregation_query(self, pipeline=None):
        AggregationQuery = sys.modules["bunnet.odm.queries.aggregation"].AggregationQuery

        instance = MagicMock()
        instance.__class__ = AggregationQuery
        instance.aggregation_pipeline = pipeline if pipeline is not None else []

        cloned = MagicMock()
        cloned.aggregation_pipeline = list(instance.aggregation_pipeline)
        cloned.to_list.return_value = [{"data": [{"id": 1}], "metadata": [{"total": 5}]}]
        instance.clone.return_value = cloned
        return instance, cloned

    def test_aggregation_basic_with_limit_and_offset(self):
        raw_params = _make_raw_params(limit=5, offset=2, include_total=True)
        mock_params = _make_mock_params(raw_params)
        query, cloned = self._make_aggregation_query()

        with patch("fastapi_pagination.ext.bunnet.verify_params") as vp, \
             patch("fastapi_pagination.ext.bunnet.apply_items_transformer") as ait, \
             patch("fastapi_pagination.ext.bunnet.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = [{"id": 1}]
            cp.return_value = MagicMock(name="page")

            result = paginate(query)

        vp.assert_called_once_with(None, "limit-offset")
        assert ait.called
        assert cp.called
        # Pipeline should have $facet appended
        pipeline = cloned.aggregation_pipeline
        facet_stage = pipeline[-1]
        assert "$facet" in facet_stage

    def test_aggregation_limit_none(self):
        raw_params = _make_raw_params(limit=None, offset=3, include_total=True)
        mock_params = _make_mock_params(raw_params)
        query, cloned = self._make_aggregation_query()

        with patch("fastapi_pagination.ext.bunnet.verify_params") as vp, \
             patch("fastapi_pagination.ext.bunnet.apply_items_transformer") as ait, \
             patch("fastapi_pagination.ext.bunnet.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = []
            cp.return_value = MagicMock()

            paginate(query)

        pipeline = cloned.aggregation_pipeline
        facet_stage = pipeline[-1]
        # No $limit stage — $skip only
        data_stages = facet_stage["$facet"]["data"]
        stage_keys = [list(s.keys())[0] for s in data_stages]
        assert "$limit" not in stage_keys
        assert "$skip" in stage_keys

    def test_aggregation_offset_none(self):
        raw_params = _make_raw_params(limit=5, offset=None, include_total=True)
        mock_params = _make_mock_params(raw_params)
        query, cloned = self._make_aggregation_query()

        with patch("fastapi_pagination.ext.bunnet.verify_params") as vp, \
             patch("fastapi_pagination.ext.bunnet.apply_items_transformer") as ait, \
             patch("fastapi_pagination.ext.bunnet.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = []
            cp.return_value = MagicMock()

            paginate(query)

        pipeline = cloned.aggregation_pipeline
        facet_stage = pipeline[-1]
        data_stages = facet_stage["$facet"]["data"]
        stage_keys = [list(s.keys())[0] for s in data_stages]
        assert "$skip" not in stage_keys

    def test_aggregation_empty_metadata_total_zero(self):
        raw_params = _make_raw_params(limit=5, offset=0, include_total=True)
        mock_params = _make_mock_params(raw_params)
        query, cloned = self._make_aggregation_query()
        # metadata is empty -> IndexError -> total = 0
        cloned.to_list.return_value = [{"data": [], "metadata": []}]

        with patch("fastapi_pagination.ext.bunnet.verify_params") as vp, \
             patch("fastapi_pagination.ext.bunnet.apply_items_transformer") as ait, \
             patch("fastapi_pagination.ext.bunnet.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = []
            cp.return_value = MagicMock()

            paginate(query)

        cp.assert_called_once()
        call_kwargs = cp.call_args[1]
        assert call_kwargs["total"] == 0

    def test_aggregation_filter_end_int(self):
        raw_params = _make_raw_params(limit=5, offset=2, include_total=True)
        mock_params = _make_mock_params(raw_params)
        pipeline = [{"$match": {"active": True}}, {"$project": {"name": 1}}, {"$sort": {"name": 1}}]
        query, cloned = self._make_aggregation_query(pipeline=list(pipeline))
        cloned.to_list.return_value = [{"data": [{"id": 1}], "metadata": [{"total": 3}]}]

        with patch("fastapi_pagination.ext.bunnet.verify_params") as vp, \
             patch("fastapi_pagination.ext.bunnet.apply_items_transformer") as ait, \
             patch("fastapi_pagination.ext.bunnet.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = [{"id": 1}]
            cp.return_value = MagicMock()

            paginate(query, aggregation_filter_end=2)

        # After split, pipeline should have $facet with transform_part included
        result_pipeline = cloned.aggregation_pipeline
        facet_stage = result_pipeline[-1]
        assert "$facet" in facet_stage

    def test_aggregation_filter_end_auto(self):
        raw_params = _make_raw_params(limit=5, offset=2, include_total=True)
        mock_params = _make_mock_params(raw_params)
        pipeline = [{"$match": {"active": True}}, {"$project": {"name": 1}}]
        query, cloned = self._make_aggregation_query(pipeline=list(pipeline))
        cloned.to_list.return_value = [{"data": [{"id": 1}], "metadata": [{"total": 2}]}]

        with patch("fastapi_pagination.ext.bunnet.verify_params") as vp, \
             patch("fastapi_pagination.ext.bunnet.apply_items_transformer") as ait, \
             patch("fastapi_pagination.ext.bunnet.create_page") as cp, \
             patch("fastapi_pagination.ext.bunnet.get_mongo_pipeline_filter_end", return_value=1) as gmpfe:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = [{"id": 1}]
            cp.return_value = MagicMock()

            paginate(query, aggregation_filter_end="auto")

        gmpfe.assert_called_once()
        result_pipeline = cloned.aggregation_pipeline
        facet_stage = result_pipeline[-1]
        assert "$facet" in facet_stage

    def test_aggregation_pipeline_transformer(self):
        raw_params = _make_raw_params(limit=5, offset=0, include_total=True)
        mock_params = _make_mock_params(raw_params)
        query, cloned = self._make_aggregation_query()
        cloned.to_list.return_value = [{"data": [{"id": 1}], "metadata": [{"total": 1}]}]

        transformed_pipeline = [{"$match": {}}, {"$limit": 10}]
        transformer = MagicMock(return_value=transformed_pipeline)

        with patch("fastapi_pagination.ext.bunnet.verify_params") as vp, \
             patch("fastapi_pagination.ext.bunnet.apply_items_transformer") as ait, \
             patch("fastapi_pagination.ext.bunnet.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = [{"id": 1}]
            cp.return_value = MagicMock()

            paginate(query, aggregation_pipeline_transformer=transformer)

        transformer.assert_called_once()
        assert cloned.aggregation_pipeline == transformed_pipeline


# ---------------------------------------------------------------------------
# FindMany / Document path
# ---------------------------------------------------------------------------


class TestPaginateFindMany:
    def _make_find_query(self):
        find_many_mock = MagicMock()
        find_many_mock.to_list.return_value = [{"id": 1}, {"id": 2}]

        query = MagicMock()
        query.find_many.return_value = find_many_mock
        query.find.return_value = MagicMock(count=MagicMock(return_value=10))
        return query

    def test_find_many_with_total(self):
        raw_params = _make_raw_params(limit=10, offset=0, include_total=True)
        mock_params = _make_mock_params(raw_params)
        query = self._make_find_query()

        with patch("fastapi_pagination.ext.bunnet.verify_params") as vp, \
             patch("fastapi_pagination.ext.bunnet.apply_items_transformer") as ait, \
             patch("fastapi_pagination.ext.bunnet.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = [{"id": 1}]
            cp.return_value = MagicMock(name="page")

            result = paginate(query)

        query.find_many.assert_called_once()
        query.find.assert_called_once()
        call_kwargs = cp.call_args[1]
        assert call_kwargs["total"] == 10

    def test_find_many_without_total(self):
        raw_params = _make_raw_params(limit=10, offset=0, include_total=False)
        mock_params = _make_mock_params(raw_params)
        query = self._make_find_query()

        with patch("fastapi_pagination.ext.bunnet.verify_params") as vp, \
             patch("fastapi_pagination.ext.bunnet.apply_items_transformer") as ait, \
             patch("fastapi_pagination.ext.bunnet.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = [{"id": 1}]
            cp.return_value = MagicMock(name="page")

            result = paginate(query)

        query.find.assert_not_called()
        call_kwargs = cp.call_args[1]
        assert call_kwargs["total"] is None

    def test_find_many_passes_kwargs_to_find_many(self):
        raw_params = _make_raw_params(limit=5, offset=3, include_total=True)
        mock_params = _make_mock_params(raw_params)
        query = self._make_find_query()

        with patch("fastapi_pagination.ext.bunnet.verify_params") as vp, \
             patch("fastapi_pagination.ext.bunnet.apply_items_transformer") as ait, \
             patch("fastapi_pagination.ext.bunnet.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = []
            cp.return_value = MagicMock()

            paginate(query, custom_kwarg="value")

        call_kwargs = query.find_many.call_args[1]
        assert call_kwargs["limit"] == 5
        assert call_kwargs["skip"] == 3
        assert call_kwargs["custom_kwarg"] == "value"

    def test_find_many_with_transformer(self):
        raw_params = _make_raw_params(limit=10, offset=0, include_total=True)
        mock_params = _make_mock_params(raw_params)
        query = self._make_find_query()
        transformer = MagicMock(return_value=["transformed"])

        with patch("fastapi_pagination.ext.bunnet.verify_params") as vp, \
             patch("fastapi_pagination.ext.bunnet.apply_items_transformer") as ait, \
             patch("fastapi_pagination.ext.bunnet.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = ["transformed"]
            cp.return_value = MagicMock()

            paginate(query, transformer=transformer)

        ait.assert_called_once_with([{"id": 1}, {"id": 2}], transformer)

    def test_find_many_with_additional_data(self):
        raw_params = _make_raw_params(limit=10, offset=0, include_total=True)
        mock_params = _make_mock_params(raw_params)
        query = self._make_find_query()

        with patch("fastapi_pagination.ext.bunnet.verify_params") as vp, \
             patch("fastapi_pagination.ext.bunnet.apply_items_transformer") as ait, \
             patch("fastapi_pagination.ext.bunnet.create_page") as cp:
            vp.return_value = (mock_params, raw_params)
            ait.return_value = []
            cp.return_value = MagicMock()

            paginate(query, additional_data={"extra": "value"})

        call_kwargs = cp.call_args[1]
        assert call_kwargs.get("extra") == "value"
