"""Unit tests for fastapi_pagination.ext.bunnet.paginate."""

import sys
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Inject fake bunnet modules BEFORE importing the extension under test.
# bunnet is not installed in the test environment.
# ---------------------------------------------------------------------------

_bunnet_mock = MagicMock()
_bunnet_enums_mock = MagicMock()
_bunnet_interfaces_aggregate_mock = MagicMock()
_bunnet_queries_aggregation_mock = MagicMock()
_bunnet_queries_find_mock = MagicMock()

for _key, _mod in [
    ("bunnet", _bunnet_mock),
    ("bunnet.odm", MagicMock()),
    ("bunnet.odm.enums", _bunnet_enums_mock),
    ("bunnet.odm.interfaces", MagicMock()),
    ("bunnet.odm.interfaces.aggregate", _bunnet_interfaces_aggregate_mock),
    ("bunnet.odm.queries", MagicMock()),
    ("bunnet.odm.queries.aggregation", _bunnet_queries_aggregation_mock),
    ("bunnet.odm.queries.find", _bunnet_queries_find_mock),
]:
    sys.modules[_key] = _mod


class _FakeAggregationQuery:
    """Minimal stand-in for bunnet AggregationQuery."""

    def __class_getitem__(cls, item):
        return cls

    def __init__(self, pipeline=None, items=None, total=1):
        self.aggregation_pipeline = pipeline if pipeline is not None else []
        self._items = items if items is not None else [{"_id": 1}]
        self._total = total

    def clone(self):
        cloned = _FakeAggregationQuery(
            pipeline=list(self.aggregation_pipeline),
            items=self._items,
            total=self._total,
        )
        return cloned

    def to_list(self):
        if self._total > 0:
            return [{"data": self._items, "metadata": [{"total": self._total}]}]
        return [{"data": self._items, "metadata": []}]


# Bind our fake class so that `from bunnet.odm.queries.aggregation import AggregationQuery`
# resolves to _FakeAggregationQuery inside the extension module.
_bunnet_queries_aggregation_mock.AggregationQuery = _FakeAggregationQuery

# Remove any cached import of the extension so our mocks take effect.
sys.modules.pop("fastapi_pagination.ext.bunnet", None)

from fastapi_pagination.ext.bunnet import paginate  # noqa: E402  (must come after mocks)
from fastapi_pagination.bases import RawParams  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_raw_params(limit=10, offset=0, include_total=True):
    return RawParams(limit=limit, offset=offset, include_total=include_total)


def _mock_verify(raw_params):
    """Return a patcher that stubs verify_params with *raw_params*."""
    mock_params = MagicMock(name="params")
    return (
        patch(
            "fastapi_pagination.ext.bunnet.verify_params",
            return_value=(mock_params, raw_params),
        ),
        mock_params,
    )


@pytest.fixture()
def mock_create_page():
    page = MagicMock(name="page")
    with patch("fastapi_pagination.ext.bunnet.create_page", return_value=page) as p:
        yield p, page


@pytest.fixture()
def mock_apply_transformer():
    with patch(
        "fastapi_pagination.ext.bunnet.apply_items_transformer",
        side_effect=lambda items, _t: items,
    ) as p:
        yield p


# ---------------------------------------------------------------------------
# Tests – AggregationQuery branch (lines 41-75)
# ---------------------------------------------------------------------------


def test_paginate_aggregation_basic(mock_create_page, mock_apply_transformer):
    """AggregationQuery without aggregation_filter_end: basic $facet pipeline."""
    raw_params = _make_raw_params(limit=5, offset=2, include_total=True)
    patcher, mock_params = _mock_verify(raw_params)
    _, page = mock_create_page

    query = _FakeAggregationQuery(pipeline=[{"$match": {"active": True}}])

    with patcher:
        result = paginate(query)

    assert result is page


def test_paginate_aggregation_no_limit_no_offset(mock_create_page, mock_apply_transformer):
    """AggregationQuery with limit=None and offset=None."""
    raw_params = _make_raw_params(limit=None, offset=None, include_total=True)
    patcher, mock_params = _mock_verify(raw_params)
    _, page = mock_create_page

    query = _FakeAggregationQuery()

    with patcher:
        result = paginate(query)

    assert result is page


def test_paginate_aggregation_empty_metadata_gives_total_zero(mock_create_page, mock_apply_transformer):
    """AggregationQuery with empty metadata → total falls back to 0 (IndexError path)."""
    raw_params = _make_raw_params(limit=5, offset=0)
    patcher, mock_params = _mock_verify(raw_params)
    create_page_mock, _ = mock_create_page

    query = _FakeAggregationQuery(items=[], total=0)

    with patcher:
        paginate(query)

    _call_kwargs = create_page_mock.call_args
    assert _call_kwargs[1]["total"] == 0


def test_paginate_aggregation_filter_end_auto(mock_create_page, mock_apply_transformer):
    """aggregation_filter_end='auto' triggers get_mongo_pipeline_filter_end."""
    raw_params = _make_raw_params(limit=3, offset=1)
    patcher, mock_params = _mock_verify(raw_params)

    pipeline = [
        {"$match": {"x": 1}},
        {"$project": {"name": 1}},
    ]
    query = _FakeAggregationQuery(pipeline=pipeline)

    with patcher:
        with patch(
            "fastapi_pagination.ext.bunnet.get_mongo_pipeline_filter_end",
            return_value=1,
        ) as gm:
            result = paginate(query, aggregation_filter_end="auto")

    gm.assert_called_once()
    assert result is mock_create_page[1]


def test_paginate_aggregation_filter_end_integer(mock_create_page, mock_apply_transformer):
    """aggregation_filter_end as integer splits the pipeline at that position."""
    raw_params = _make_raw_params(limit=4, offset=0)
    patcher, mock_params = _mock_verify(raw_params)

    pipeline = [
        {"$match": {"y": 2}},
        {"$sort": {"name": 1}},
        {"$project": {"name": 1}},
    ]
    query = _FakeAggregationQuery(pipeline=pipeline)

    with patcher:
        result = paginate(query, aggregation_filter_end=1)

    assert result is mock_create_page[1]


def test_paginate_aggregation_with_pipeline_transformer(mock_create_page, mock_apply_transformer):
    """aggregation_pipeline_transformer is applied to the pipeline."""
    raw_params = _make_raw_params(limit=2, offset=0)
    patcher, mock_params = _mock_verify(raw_params)

    transformed_pipeline = [{"$match": {}}, {"$addFields": {"extra": 1}}]
    transformer = MagicMock(return_value=transformed_pipeline)

    query = _FakeAggregationQuery()

    with patcher:
        result = paginate(query, aggregation_pipeline_transformer=transformer)

    transformer.assert_called_once()
    assert result is mock_create_page[1]


# ---------------------------------------------------------------------------
# Tests – FindMany / Document branch (lines 77-98)
# ---------------------------------------------------------------------------


def _make_find_many_query(items, total=None):
    """Build a mock object that satisfies the non-aggregation query interface."""
    query = MagicMock()
    find_many_result = MagicMock()
    find_many_result.to_list.return_value = items
    query.find_many.return_value = find_many_result

    find_result = MagicMock()
    find_result.count.return_value = total if total is not None else len(items)
    query.find.return_value = find_result

    return query


def test_paginate_find_many_with_total(mock_create_page, mock_apply_transformer):
    """Non-aggregation query with include_total=True."""
    raw_params = _make_raw_params(limit=10, offset=0, include_total=True)
    patcher, mock_params = _mock_verify(raw_params)

    items = [{"name": "alice"}, {"name": "bob"}]
    query = _make_find_many_query(items, total=2)

    create_page_mock, page = mock_create_page

    with patcher:
        result = paginate(query)

    assert result is page
    create_page_mock.assert_called_once()
    call_kwargs = create_page_mock.call_args
    assert call_kwargs[1]["total"] == 2


def test_paginate_find_many_without_total(mock_create_page, mock_apply_transformer):
    """Non-aggregation query with include_total=False → total=None."""
    raw_params = _make_raw_params(limit=5, offset=0, include_total=False)
    patcher, mock_params = _mock_verify(raw_params)

    items = [{"name": "carol"}]
    query = _make_find_many_query(items)

    create_page_mock, page = mock_create_page

    with patcher:
        result = paginate(query)

    assert result is page
    call_kwargs = create_page_mock.call_args
    assert call_kwargs[1]["total"] is None


def test_paginate_find_many_extra_kwargs(mock_create_page, mock_apply_transformer):
    """Extra pymongo_kwargs are forwarded to find_many and find."""
    raw_params = _make_raw_params(limit=5, offset=0, include_total=True)
    patcher, mock_params = _mock_verify(raw_params)

    items = [{"x": 1}]
    query = _make_find_many_query(items, total=1)

    with patcher:
        paginate(query, session=None, ignore_cache=True)

    query.find_many.assert_called_once()
    call_kwargs = query.find_many.call_args[1]
    assert call_kwargs["ignore_cache"] is True


# ---------------------------------------------------------------------------
# Tests – shared post-branch paths (lines 100, 102)
# ---------------------------------------------------------------------------


def test_paginate_items_transformer_applied(mock_create_page):
    """apply_items_transformer is always called and its result passed to create_page."""
    raw_params = _make_raw_params(limit=5, offset=0)
    patcher, mock_params = _mock_verify(raw_params)

    transformed = [{"transformed": True}]
    create_page_mock, page = mock_create_page

    items = [{"original": True}]
    query = _make_find_many_query(items, total=1)
    user_transformer = MagicMock(return_value=transformed)

    with patcher:
        with patch(
            "fastapi_pagination.ext.bunnet.apply_items_transformer",
            return_value=transformed,
        ) as at_mock:
            result = paginate(query, transformer=user_transformer)

    at_mock.assert_called_once_with(items, user_transformer)
    first_arg = create_page_mock.call_args[0][0]
    assert first_arg is transformed


def test_paginate_additional_data_forwarded(mock_create_page, mock_apply_transformer):
    """additional_data dict is unpacked into create_page kwargs."""
    raw_params = _make_raw_params(limit=5, offset=0)
    patcher, mock_params = _mock_verify(raw_params)

    create_page_mock, _ = mock_create_page
    items = [{"k": "v"}]
    query = _make_find_many_query(items, total=1)

    with patcher:
        paginate(query, additional_data={"custom_field": "hello"})

    call_kwargs = create_page_mock.call_args[1]
    assert call_kwargs.get("custom_field") == "hello"
