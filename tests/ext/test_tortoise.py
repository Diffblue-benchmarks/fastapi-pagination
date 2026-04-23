from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Mock external dependencies that may not be installed in this environment.
# These mocks must be inserted into sys.modules BEFORE any imports from
# fastapi_pagination.ext.tortoise so that the module can be loaded.
# ---------------------------------------------------------------------------

# We define a real class so isinstance() checks work correctly.
class _MockQuerySet:
    def __class_getitem__(cls, item):
        return cls


class _MockModel:
    pass


if "tortoise" not in sys.modules:
    sys.modules["tortoise"] = MagicMock()

if "tortoise.models" not in sys.modules:
    _mock_models = MagicMock()
    _mock_models.Model = _MockModel
    sys.modules["tortoise.models"] = _mock_models

if "tortoise.query_utils" not in sys.modules:
    sys.modules["tortoise.query_utils"] = MagicMock()

if "tortoise.queryset" not in sys.modules:
    _mock_queryset_mod = MagicMock()
    _mock_queryset_mod.QuerySet = _MockQuerySet
    sys.modules["tortoise.queryset"] = _mock_queryset_mod

# ---------------------------------------------------------------------------
# Now it is safe to import the module under test.
# ---------------------------------------------------------------------------
from fastapi_pagination.api import set_params
from fastapi_pagination.default import Page, Params
from fastapi_pagination.ext.tortoise import _generate_query, apaginate, paginate

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_queryset(total: int = 0, items: list | None = None) -> _MockQuerySet:
    """Build a mock QuerySet that satisfies the tortoise interface."""
    if items is None:
        items = []

    qs = _MockQuerySet()
    qs.count = AsyncMock(return_value=total)  # type: ignore[attr-defined]
    # limit / offset / prefetch_related return `self` for chaining
    qs.limit = MagicMock(return_value=qs)  # type: ignore[attr-defined]
    qs.offset = MagicMock(return_value=qs)  # type: ignore[attr-defined]
    qs.prefetch_related = MagicMock(return_value=qs)  # type: ignore[attr-defined]
    # .all() is awaitable and returns the item list
    qs.all = AsyncMock(return_value=items)  # type: ignore[attr-defined]
    # model meta for prefetch_related=True path
    qs.model = MagicMock()  # type: ignore[attr-defined]
    qs.model._meta.fetch_fields = ["rel_a", "rel_b"]
    return qs


# ---------------------------------------------------------------------------
# Tests for _generate_query
# ---------------------------------------------------------------------------

class TestGenerateQuery:
    def test_prefetch_related_false_returns_query_unchanged(self):
        qs = _make_queryset()

        result = _generate_query(qs, False)

        assert result is qs
        qs.prefetch_related.assert_not_called()

    def test_prefetch_related_empty_list_returns_query_unchanged(self):
        qs = _make_queryset()

        result = _generate_query(qs, [])

        assert result is qs
        qs.prefetch_related.assert_not_called()

    def test_prefetch_related_true_uses_model_fetch_fields(self):
        qs = _make_queryset()
        qs.model._meta.fetch_fields = ["owner", "tags"]
        expected_qs = _make_queryset()
        qs.prefetch_related.return_value = expected_qs

        result = _generate_query(qs, True)

        qs.prefetch_related.assert_called_once_with("owner", "tags")
        assert result is expected_qs

    def test_prefetch_related_list_calls_prefetch_related_with_list(self):
        qs = _make_queryset()
        fields = ["author", "category"]
        expected_qs = _make_queryset()
        qs.prefetch_related.return_value = expected_qs

        result = _generate_query(qs, fields)

        qs.prefetch_related.assert_called_once_with("author", "category")
        assert result is expected_qs

    def test_prefetch_related_single_string_in_list(self):
        qs = _make_queryset()
        qs.prefetch_related.return_value = qs

        result = _generate_query(qs, ["single_field"])

        qs.prefetch_related.assert_called_once_with("single_field")
        assert result is qs


# ---------------------------------------------------------------------------
# Tests for apaginate
# ---------------------------------------------------------------------------

class TestApaginate:
    async def test_queryset_passed_directly(self):
        items = [{"id": 1}, {"id": 2}]
        qs = _make_queryset(total=2, items=items)
        params = Params(page=1, size=10)

        with set_params(params):
            result = await apaginate(qs)

        assert result.total == 2
        assert len(result.items) == 2

    async def test_model_class_calls_all(self):
        items = [{"id": 42}]
        inner_qs = _make_queryset(total=1, items=items)

        model_cls = MagicMock()
        model_cls.all.return_value = inner_qs

        params = Params(page=1, size=10)

        with set_params(params):
            result = await apaginate(model_cls)

        model_cls.all.assert_called_once()
        assert result.total == 1

    async def test_explicit_params_argument(self):
        qs = _make_queryset(total=0, items=[])
        params = Params(page=1, size=5)

        result = await apaginate(qs, params=params)

        assert result.total == 0
        assert result.items == []

    async def test_explicit_total_skips_count(self):
        qs = _make_queryset(total=999, items=["a", "b"])
        params = Params(page=1, size=10)

        with set_params(params):
            result = await apaginate(qs, total=7)

        assert result.total == 7
        qs.count.assert_not_called()

    async def test_prefetch_related_true_forwarded(self):
        qs = _make_queryset(total=1, items=["x"])
        qs.model._meta.fetch_fields = ["related"]
        params = Params(page=1, size=10)

        with set_params(params):
            result = await apaginate(qs, prefetch_related=True)

        qs.prefetch_related.assert_called()
        assert result.total == 1

    async def test_prefetch_related_list_forwarded(self):
        qs = _make_queryset(total=1, items=["y"])
        params = Params(page=1, size=10)

        with set_params(params):
            result = await apaginate(qs, prefetch_related=["author"])

        qs.prefetch_related.assert_called_once_with("author")
        assert result.total == 1


# ---------------------------------------------------------------------------
# Tests for paginate (deprecated wrapper)
# ---------------------------------------------------------------------------

class TestPaginate:
    async def test_delegates_to_apaginate(self):
        items = [{"id": 10}]
        qs = _make_queryset(total=1, items=items)
        params = Params(page=1, size=5)

        with set_params(params):
            result = await paginate(qs)

        assert result.total == 1
        assert len(result.items) == 1

    async def test_delegates_with_explicit_total(self):
        qs = _make_queryset(total=999, items=["z"])
        params = Params(page=1, size=10)

        with set_params(params):
            result = await paginate(qs, total=3)

        assert result.total == 3
        qs.count.assert_not_called()

    async def test_delegates_with_model_class(self):
        items = [{"id": 7}]
        inner_qs = _make_queryset(total=1, items=items)

        model_cls = MagicMock()
        model_cls.all.return_value = inner_qs

        params = Params(page=1, size=10)

        with set_params(params):
            result = await paginate(model_cls)

        model_cls.all.assert_called_once()
        assert result.total == 1
