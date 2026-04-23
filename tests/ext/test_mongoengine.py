import sys
from unittest.mock import MagicMock

import pytest

# Inject mock mongoengine module before importing extension so it works without mongoengine installed
if "mongoengine" not in sys.modules:

    class _TopLevelDocumentMetaclass(type):
        pass

    _mock_base_metaclasses = MagicMock()
    _mock_base_metaclasses.TopLevelDocumentMetaclass = _TopLevelDocumentMetaclass

    _mock_base = MagicMock()
    _mock_base.metaclasses = _mock_base_metaclasses

    _mock_mongoengine = MagicMock()
    _mock_mongoengine.QuerySet = MagicMock
    _mock_mongoengine.base = _mock_base

    sys.modules["mongoengine"] = _mock_mongoengine
    sys.modules["mongoengine.base"] = _mock_base
    sys.modules["mongoengine.base.metaclasses"] = _mock_base_metaclasses

from fastapi_pagination.bases import RawParams
from fastapi_pagination.default import Params
from fastapi_pagination.ext.mongoengine import _limit_offset_flow, paginate
from fastapi_pagination.flow import run_sync_flow


def _make_paginated_qs(items):
    paginated = MagicMock()
    paginated.__iter__ = MagicMock(return_value=iter(items))
    return paginated


def _make_full_qs(items, count):
    qs = MagicMock()
    qs.count.return_value = count
    qs.skip.return_value.limit.return_value = _make_paginated_qs(items)
    return qs


def test_limit_offset_flow_returns_to_mongo_list():
    item1 = MagicMock()
    item1.to_mongo.return_value = {"_id": 1, "name": "Alice"}
    item2 = MagicMock()
    item2.to_mongo.return_value = {"_id": 2, "name": "Bob"}

    qs = MagicMock()
    qs.skip.return_value.limit.return_value = _make_paginated_qs([item1, item2])

    raw_params = RawParams(limit=10, offset=0)
    result = run_sync_flow(_limit_offset_flow(qs, raw_params))

    assert result == [{"_id": 1, "name": "Alice"}, {"_id": 2, "name": "Bob"}]


def test_limit_offset_flow_applies_skip_and_limit():
    item = MagicMock()
    item.to_mongo.return_value = {"_id": 42}

    qs = MagicMock()
    qs.skip.return_value.limit.return_value = _make_paginated_qs([item])

    raw_params = RawParams(limit=5, offset=15)
    run_sync_flow(_limit_offset_flow(qs, raw_params))

    qs.skip.assert_called_once_with(15)
    qs.skip.return_value.limit.assert_called_once_with(5)


def test_limit_offset_flow_empty_result():
    qs = MagicMock()
    qs.skip.return_value.limit.return_value = _make_paginated_qs([])

    raw_params = RawParams(limit=10, offset=0)
    result = run_sync_flow(_limit_offset_flow(qs, raw_params))

    assert result == []


def test_paginate_with_queryset():
    item1 = MagicMock()
    item1.to_mongo.return_value = {"_id": 1}
    item2 = MagicMock()
    item2.to_mongo.return_value = {"_id": 2}

    qs = _make_full_qs([item1, item2], count=2)

    params = Params(page=1, size=10)
    result = paginate(qs, params=params)

    assert result.total == 2
    assert len(result.items) == 2


def test_paginate_with_document_class():
    from mongoengine.base.metaclasses import TopLevelDocumentMetaclass

    item = MagicMock()
    item.to_mongo.return_value = {"_id": 1, "value": "test"}

    inner_qs = _make_full_qs([item], count=1)

    class MockDocument(metaclass=TopLevelDocumentMetaclass):
        pass

    all_mock = MagicMock(return_value=inner_qs)
    objects_mock = MagicMock(return_value=MagicMock(all=all_mock))
    MockDocument.objects = objects_mock

    params = Params(page=1, size=10)
    result = paginate(MockDocument, params=params)

    objects_mock.assert_called_once()
    all_mock.assert_called_once()
    assert result.total == 1
    assert len(result.items) == 1
