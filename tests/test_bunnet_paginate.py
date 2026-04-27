"""Tests for fastapi_pagination.ext.bunnet.paginate."""
import sys
from dataclasses import dataclass, field
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Mock bunnet (not installed) before importing the extension module.
# We need real classes so that isinstance() checks work correctly.
# ---------------------------------------------------------------------------


class _MockAggregationQuery:
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, pipeline=None):
        self.aggregation_pipeline = list(pipeline) if pipeline else []

    def clone(self):
        new_q = _MockAggregationQuery(list(self.aggregation_pipeline))
        # Copy any instance-level to_list override so mocks propagate to clones.
        if "to_list" in self.__dict__:
            new_q.to_list = self.__dict__["to_list"]
        return new_q

    def to_list(self):  # default – tests override per instance
        return [{"data": [], "metadata": []}]


_agg_module = MagicMock()
_agg_module.AggregationQuery = _MockAggregationQuery

_bunnet_mocks = {
    "bunnet": MagicMock(),
    "bunnet.odm": MagicMock(),
    "bunnet.odm.enums": MagicMock(),
    "bunnet.odm.interfaces": MagicMock(),
    "bunnet.odm.interfaces.aggregate": MagicMock(),
    "bunnet.odm.queries": MagicMock(),
    "bunnet.odm.queries.aggregation": _agg_module,
    "bunnet.odm.queries.find": MagicMock(),
}
for _name, _mod in _bunnet_mocks.items():
    sys.modules[_name] = _mod

# Remove cached module so the fresh import picks up our mocks.
sys.modules.pop("fastapi_pagination.ext.bunnet", None)

from fastapi_pagination.ext.bunnet import paginate  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class _RawParams:
    limit: int | None = 10
    offset: int | None = 0
    include_total: bool = True
    type: str = "limit-offset"


def _make_params(limit=10, offset=0, include_total=True):
    params = MagicMock()
    raw = _RawParams(limit=limit, offset=offset, include_total=include_total)
    return params, raw


# ---------------------------------------------------------------------------
# Tests – AggregationQuery branch
# ---------------------------------------------------------------------------


class TestPaginateAggregation:
    """Cover the isinstance(query, AggregationQuery) == True branch."""

    def test_basic_no_filter_end(self):
        """AggregationQuery path, no aggregation_filter_end (extends pipeline with $facet)."""
        params, raw = _make_params(limit=5, offset=2)
        items = [{"_id": 1}, {"_id": 2}]

        query = _MockAggregationQuery()
        query.to_list = MagicMock(return_value=[{"data": items, "metadata": [{"total": 2}]}])

        with (
            patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.bunnet.apply_items_transformer", return_value=items) as mock_apply,
            patch("fastapi_pagination.ext.bunnet.create_page") as mock_create,
        ):
            paginate(query)

            mock_apply.assert_called_once_with(items, None)
            mock_create.assert_called_once_with(items, total=2, params=params)

    def test_empty_metadata_total_zero(self):
        """When metadata list is empty, IndexError is caught and total becomes 0."""
        params, raw = _make_params(limit=5, offset=0)

        query = _MockAggregationQuery()
        query.to_list = MagicMock(return_value=[{"data": [], "metadata": []}])

        with (
            patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.bunnet.apply_items_transformer", return_value=[]),
            patch("fastapi_pagination.ext.bunnet.create_page") as mock_create,
        ):
            paginate(query)

            mock_create.assert_called_once_with([], total=0, params=params)

    def test_filter_end_integer(self):
        """aggregation_filter_end as explicit integer splits the pipeline."""
        params, raw = _make_params(limit=5, offset=1)
        pipeline = [{"$match": {"active": True}}, {"$project": {"name": 1}}]
        items = [{"name": "x"}]

        query = _MockAggregationQuery(pipeline=pipeline)
        query.to_list = MagicMock(return_value=[{"data": items, "metadata": [{"total": 1}]}])

        with (
            patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.bunnet.apply_items_transformer", return_value=items),
            patch("fastapi_pagination.ext.bunnet.create_page") as mock_create,
        ):
            paginate(query, aggregation_filter_end=1)

            mock_create.assert_called_once_with(items, total=1, params=params)

    def test_filter_end_auto(self):
        """aggregation_filter_end='auto' delegates to get_mongo_pipeline_filter_end."""
        params, raw = _make_params(limit=5, offset=0)
        pipeline = [{"$match": {}}, {"$project": {"name": 1}}]
        items = [{"name": "y"}]

        query = _MockAggregationQuery(pipeline=pipeline)
        query.to_list = MagicMock(return_value=[{"data": items, "metadata": [{"total": 1}]}])

        with (
            patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw)),
            patch(
                "fastapi_pagination.ext.bunnet.get_mongo_pipeline_filter_end",
                return_value=1,
            ) as mock_filter,
            patch("fastapi_pagination.ext.bunnet.apply_items_transformer", return_value=items),
            patch("fastapi_pagination.ext.bunnet.create_page") as mock_create,
        ):
            paginate(query, aggregation_filter_end="auto")

            mock_filter.assert_called_once()
            mock_create.assert_called_once_with(items, total=1, params=params)

    def test_pipeline_transformer(self):
        """aggregation_pipeline_transformer replaces the pipeline before execution."""
        params, raw = _make_params(limit=5, offset=0)
        transformed = [{"$customStage": True}]
        items = [{"_id": 99}]

        query = _MockAggregationQuery()
        query.to_list = MagicMock(return_value=[{"data": items, "metadata": [{"total": 1}]}])
        transformer = MagicMock(return_value=transformed)

        with (
            patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.bunnet.apply_items_transformer", return_value=items),
            patch("fastapi_pagination.ext.bunnet.create_page") as mock_create,
        ):
            paginate(query, aggregation_pipeline_transformer=transformer)

            transformer.assert_called_once()
            mock_create.assert_called_once_with(items, total=1, params=params)

    def test_no_limit(self):
        """When raw_params.limit is None, no $limit stage is added."""
        params, raw = _make_params(limit=None, offset=0)

        query = _MockAggregationQuery()
        query.to_list = MagicMock(return_value=[{"data": [], "metadata": [{"total": 0}]}])

        with (
            patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.bunnet.apply_items_transformer", return_value=[]),
            patch("fastapi_pagination.ext.bunnet.create_page") as mock_create,
        ):
            paginate(query)

            mock_create.assert_called_once_with([], total=0, params=params)

    def test_no_offset(self):
        """When raw_params.offset is None, no $skip stage is added."""
        params, raw = _make_params(limit=5, offset=None)

        query = _MockAggregationQuery()
        query.to_list = MagicMock(return_value=[{"data": [], "metadata": []}])

        with (
            patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.bunnet.apply_items_transformer", return_value=[]),
            patch("fastapi_pagination.ext.bunnet.create_page") as mock_create,
        ):
            paginate(query)

            mock_create.assert_called_once_with([], total=0, params=params)


# ---------------------------------------------------------------------------
# Tests – FindMany / Document branch
# ---------------------------------------------------------------------------


class TestPaginateFindMany:
    """Cover the else branch (non-AggregationQuery)."""

    def _make_query(self, items, total=5):
        find_many_result = MagicMock()
        find_many_result.to_list = MagicMock(return_value=items)

        count_result = MagicMock()
        count_result.count = MagicMock(return_value=total)

        query = MagicMock(spec=[])  # spec=[] prevents isinstance matching AggregationQuery
        query.find_many = MagicMock(return_value=find_many_result)
        query.find = MagicMock(return_value=count_result)
        return query

    def test_include_total_true(self):
        """FindMany path with include_total=True calls find().count()."""
        params, raw = _make_params(limit=5, offset=0, include_total=True)
        items = [MagicMock(), MagicMock()]
        query = self._make_query(items, total=10)

        with (
            patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.bunnet.apply_items_transformer", return_value=items),
            patch("fastapi_pagination.ext.bunnet.create_page") as mock_create,
        ):
            paginate(query)

            query.find_many.assert_called_once()
            query.find.assert_called_once()
            mock_create.assert_called_once_with(items, total=10, params=params)

    def test_include_total_false(self):
        """FindMany path with include_total=False sets total=None, skips count."""
        params, raw = _make_params(limit=5, offset=0, include_total=False)
        items = [MagicMock()]
        query = self._make_query(items)

        with (
            patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.bunnet.apply_items_transformer", return_value=items),
            patch("fastapi_pagination.ext.bunnet.create_page") as mock_create,
        ):
            paginate(query)

            query.find_many.assert_called_once()
            query.find.assert_not_called()
            mock_create.assert_called_once_with(items, total=None, params=params)

    def test_with_transformer(self):
        """FindMany path passes transformer to apply_items_transformer."""
        params, raw = _make_params(limit=3, offset=0, include_total=True)
        items = [MagicMock()]
        transformed = [{"id": 1}]
        query = self._make_query(items, total=1)
        transformer = MagicMock(return_value=transformed)

        with (
            patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw)),
            patch(
                "fastapi_pagination.ext.bunnet.apply_items_transformer",
                return_value=transformed,
            ) as mock_apply,
            patch("fastapi_pagination.ext.bunnet.create_page") as mock_create,
        ):
            paginate(query, transformer=transformer)

            mock_apply.assert_called_once_with(items, transformer)
            mock_create.assert_called_once_with(transformed, total=1, params=params)

    def test_with_additional_data(self):
        """FindMany path spreads additional_data into create_page kwargs."""
        params, raw = _make_params(limit=5, offset=0, include_total=True)
        items = [MagicMock()]
        query = self._make_query(items, total=1)

        with (
            patch("fastapi_pagination.ext.bunnet.verify_params", return_value=(params, raw)),
            patch("fastapi_pagination.ext.bunnet.apply_items_transformer", return_value=items),
            patch("fastapi_pagination.ext.bunnet.create_page") as mock_create,
        ):
            paginate(query, additional_data={"extra_key": "extra_val"})

            mock_create.assert_called_once_with(
                items, total=1, params=params, extra_key="extra_val"
            )
