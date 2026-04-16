from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

from fastapi_pagination.bases import RawParams


def _setup_mongoengine_mocks():
    """Set up mock mongoengine modules so fastapi_pagination.ext.mongoengine can be imported."""
    mongoengine_mock = ModuleType("mongoengine")
    mongoengine_base = ModuleType("mongoengine.base")
    mongoengine_base_metaclasses = ModuleType("mongoengine.base.metaclasses")

    mock_queryset = MagicMock()
    mock_top_level_metaclass = type("TopLevelDocumentMetaclass", (), {})

    mongoengine_mock.QuerySet = mock_queryset
    mongoengine_base_metaclasses.TopLevelDocumentMetaclass = mock_top_level_metaclass

    sys.modules.setdefault("mongoengine", mongoengine_mock)
    sys.modules.setdefault("mongoengine.base", mongoengine_base)
    sys.modules.setdefault("mongoengine.base.metaclasses", mongoengine_base_metaclasses)

    return mock_top_level_metaclass, mock_queryset


_top_level_metaclass_cls, _queryset_cls = _setup_mongoengine_mocks()

# Now safe to import the module under test
from fastapi_pagination.ext.mongoengine import _limit_offset_flow, paginate  # noqa: E402
from fastapi_pagination.flow import run_sync_flow  # noqa: E402


def test_limit_offset_flow_calls_skip_and_limit():
    """Test that _limit_offset_flow calls skip and limit on the query."""
    mock_item = MagicMock()
    mock_item.to_mongo.return_value = {"_id": 1}

    mock_cursor = [mock_item]
    mock_limited = MagicMock()
    mock_limited.__iter__ = MagicMock(return_value=iter(mock_cursor))

    mock_skipped = MagicMock()
    mock_skipped.limit.return_value = mock_limited

    mock_query = MagicMock()
    mock_query.skip.return_value = mock_skipped

    raw_params = RawParams(limit=10, offset=5, include_total=False)

    result = run_sync_flow(_limit_offset_flow(mock_query, raw_params))

    mock_query.skip.assert_called_once_with(5)
    mock_skipped.limit.assert_called_once_with(10)
    assert result == [{"_id": 1}]


def test_limit_offset_flow_returns_to_mongo_for_each_item():
    """Test that _limit_offset_flow converts each item via to_mongo()."""
    items = [MagicMock(), MagicMock(), MagicMock()]
    for i, item in enumerate(items):
        item.to_mongo.return_value = {"val": i}

    mock_limited = MagicMock()
    mock_limited.__iter__ = MagicMock(return_value=iter(items))

    mock_skipped = MagicMock()
    mock_skipped.limit.return_value = mock_limited

    mock_query = MagicMock()
    mock_query.skip.return_value = mock_skipped

    raw_params = RawParams(limit=3, offset=0, include_total=False)

    result = run_sync_flow(_limit_offset_flow(mock_query, raw_params))

    assert result == [{"val": 0}, {"val": 1}, {"val": 2}]
    for item in items:
        item.to_mongo.assert_called_once()


def test_limit_offset_flow_empty_result():
    """Test that _limit_offset_flow handles empty result set."""
    mock_limited = MagicMock()
    mock_limited.__iter__ = MagicMock(return_value=iter([]))

    mock_skipped = MagicMock()
    mock_skipped.limit.return_value = mock_limited

    mock_query = MagicMock()
    mock_query.skip.return_value = mock_skipped

    raw_params = RawParams(limit=10, offset=0, include_total=False)

    result = run_sync_flow(_limit_offset_flow(mock_query, raw_params))

    assert result == []


def test_paginate_with_queryset_directly():
    """Test paginate when called with a QuerySet (not a TopLevelDocumentMetaclass)."""
    mock_qs = MagicMock()
    mock_qs.__class__ = object  # not a TopLevelDocumentMetaclass

    with patch("fastapi_pagination.ext.mongoengine.run_sync_flow") as mock_run, \
         patch("fastapi_pagination.ext.mongoengine.generic_flow") as mock_flow:
        mock_run.return_value = "page_result"
        mock_flow.return_value = "flow_obj"

        result = paginate(mock_qs)

        assert result == "page_result"
        mock_flow.assert_called_once()
        mock_run.assert_called_once_with("flow_obj")


def test_paginate_with_model_class_calls_objects_all():
    """Test paginate when called with a TopLevelDocumentMetaclass instance (a Document class)."""
    mock_model_class = MagicMock()
    mock_all_qs = MagicMock()
    mock_model_class.objects.return_value.all.return_value = mock_all_qs

    with patch("fastapi_pagination.ext.mongoengine.isinstance", side_effect=lambda obj, cls: cls is _top_level_metaclass_cls), \
         patch("fastapi_pagination.ext.mongoengine.run_sync_flow") as mock_run, \
         patch("fastapi_pagination.ext.mongoengine.generic_flow") as mock_flow:
        mock_run.return_value = "page_result"
        mock_flow.return_value = "flow_obj"

        result = paginate(mock_model_class)

        assert result == "page_result"
        mock_model_class.objects.assert_called_once()
        mock_model_class.objects.return_value.all.assert_called_once()


def test_paginate_passes_params_to_generic_flow():
    """Test that params are forwarded to generic_flow."""
    mock_qs = MagicMock()
    mock_params = MagicMock()

    with patch("fastapi_pagination.ext.mongoengine.run_sync_flow") as mock_run, \
         patch("fastapi_pagination.ext.mongoengine.generic_flow") as mock_flow:
        mock_run.return_value = "page_result"
        mock_flow.return_value = "flow_obj"

        paginate(mock_qs, mock_params)

        call_kwargs = mock_flow.call_args.kwargs
        assert call_kwargs["params"] is mock_params


def test_paginate_passes_transformer_and_additional_data():
    """Test that transformer and additional_data are forwarded to generic_flow."""
    mock_qs = MagicMock()
    mock_transformer = MagicMock()
    mock_additional_data = {"key": "value"}

    with patch("fastapi_pagination.ext.mongoengine.run_sync_flow") as mock_run, \
         patch("fastapi_pagination.ext.mongoengine.generic_flow") as mock_flow:
        mock_run.return_value = "page_result"
        mock_flow.return_value = "flow_obj"

        paginate(mock_qs, transformer=mock_transformer, additional_data=mock_additional_data)

        call_kwargs = mock_flow.call_args.kwargs
        assert call_kwargs["transformer"] is mock_transformer
        assert call_kwargs["additional_data"] is mock_additional_data


def test_paginate_passes_config():
    """Test that config is forwarded to generic_flow."""
    mock_qs = MagicMock()
    mock_config = MagicMock()

    with patch("fastapi_pagination.ext.mongoengine.run_sync_flow") as mock_run, \
         patch("fastapi_pagination.ext.mongoengine.generic_flow") as mock_flow:
        mock_run.return_value = "page_result"
        mock_flow.return_value = "flow_obj"

        paginate(mock_qs, config=mock_config)

        call_kwargs = mock_flow.call_args.kwargs
        assert call_kwargs["config"] is mock_config
