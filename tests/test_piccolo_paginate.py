import asyncio
import sys
import warnings
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock piccolo modules before fastapi_pagination.ext.piccolo is imported,
# since piccolo is an optional dependency.


class _MockSelect:
    """Concrete class used in place of piccolo.query.Select for isinstance() checks."""

    __slots__ = ("table", "columns_delegate", "order_by_delegate")

    def __class_getitem__(cls, item):
        return cls

    def __init__(self, table):
        self.table = table
        cd = SimpleNamespace()
        cd.selected_columns = []
        od = SimpleNamespace()
        od._order_by = SimpleNamespace()
        od._order_by.order_by_items = []
        self.columns_delegate = cd
        self.order_by_delegate = od

    def columns(self, *args):
        m = MagicMock()
        m.first = AsyncMock(return_value={"count": 3})
        return m

    def limit(self, n):
        return self

    def offset(self, n):
        return self


class _MockCount:
    pass


class _MockTable:
    @classmethod
    def select(cls):
        return _MockSelect(cls)


_piccolo_query_mod = MagicMock()
_piccolo_query_mod.Select = _MockSelect
_piccolo_query_methods_select_mod = MagicMock()
_piccolo_query_methods_select_mod.Count = _MockCount
_piccolo_table_mod = MagicMock()
_piccolo_table_mod.Table = _MockTable

for _mod, _mock in [
    ("piccolo", MagicMock()),
    ("piccolo.query", _piccolo_query_mod),
    ("piccolo.query.methods", MagicMock()),
    ("piccolo.query.methods.select", _piccolo_query_methods_select_mod),
    ("piccolo.table", _piccolo_table_mod),
]:
    sys.modules.setdefault(_mod, _mock)

from fastapi_pagination.ext.piccolo import _copy_query, _total_flow, apaginate, paginate  # noqa: E402


# ─── _copy_query tests ────────────────────────────────────────────────────────


def test_copy_query_returns_same_type():
    query = _MockSelect(table="my_table")
    result = _copy_query(query)
    assert type(result) is _MockSelect


def test_copy_query_copies_table_attribute():
    query = _MockSelect(table="my_table")
    result = _copy_query(query)
    assert result.table == "my_table"


def test_copy_query_deep_copies_columns_delegate():
    query = _MockSelect(table="my_table")
    query.columns_delegate.selected_columns = ["id", "name"]
    result = _copy_query(query)
    assert result.columns_delegate.selected_columns == ["id", "name"]
    assert result.columns_delegate is not query.columns_delegate


def test_copy_query_produces_independent_copy():
    query = _MockSelect(table="my_table")
    query.columns_delegate.selected_columns = ["id"]
    result = _copy_query(query)
    result.columns_delegate.selected_columns = []
    assert query.columns_delegate.selected_columns == ["id"]


# ─── _total_flow tests ────────────────────────────────────────────────────────


def test_total_flow_returns_count_when_row_present():
    query = _MockSelect(table="my_table")
    gen = _total_flow(query)
    gen.send(None)  # start generator, runs until first yield
    try:
        gen.send({"count": 42})
        pytest.fail("Expected StopIteration")
    except StopIteration as exc:
        assert exc.value == 42


def test_total_flow_returns_none_when_no_row():
    query = _MockSelect(table="my_table")
    gen = _total_flow(query)
    gen.send(None)  # start generator, runs until first yield
    try:
        gen.send(None)  # row is None (falsy) → return None
        pytest.fail("Expected StopIteration")
    except StopIteration as exc:
        assert exc.value is None


def test_total_flow_resets_original_query_delegates():
    """_total_flow copies the query before modifying delegates; original is unchanged."""
    query = _MockSelect(table="my_table")
    query.columns_delegate.selected_columns = ["id", "name"]
    query.order_by_delegate._order_by.order_by_items = [("id", "asc")]
    gen = _total_flow(query)
    gen.send(None)
    try:
        gen.send({"count": 1})
    except StopIteration:
        pass
    # Original query should not be modified by _total_flow
    assert query.columns_delegate.selected_columns == ["id", "name"]
    assert query.order_by_delegate._order_by.order_by_items == [("id", "asc")]


# ─── apaginate tests ──────────────────────────────────────────────────────────


def test_apaginate_with_select_instance():
    query = _MockSelect(table="my_table")
    expected = [{"id": 1}]

    with patch(
        "fastapi_pagination.ext.piccolo.run_async_flow",
        new_callable=AsyncMock,
        return_value=expected,
    ) as mock_run:
        result = asyncio.run(apaginate(query))

    assert result == expected
    mock_run.assert_called_once()


def test_apaginate_with_table_class_calls_select():
    class MyTable(_MockTable):
        pass

    expected = [{"id": 2}]

    with patch(
        "fastapi_pagination.ext.piccolo.run_async_flow",
        new_callable=AsyncMock,
        return_value=expected,
    ) as mock_run:
        result = asyncio.run(apaginate(MyTable))

    assert result == expected
    mock_run.assert_called_once()


def test_apaginate_passes_params_and_config_to_generic_flow():
    query = _MockSelect(table="my_table")
    params = MagicMock()
    config = MagicMock()

    with patch(
        "fastapi_pagination.ext.piccolo.run_async_flow",
        new_callable=AsyncMock,
        return_value=None,
    ):
        with patch("fastapi_pagination.ext.piccolo.generic_flow") as mock_gf:
            mock_gf.return_value = iter([])
            asyncio.run(apaginate(query, params=params, config=config))

    call_kwargs = mock_gf.call_args.kwargs
    assert call_kwargs["params"] is params
    assert call_kwargs["config"] is config
    assert call_kwargs["async_"] is True


def test_apaginate_passes_additional_data_to_generic_flow():
    query = _MockSelect(table="my_table")
    additional_data = {"extra": "value"}

    with patch(
        "fastapi_pagination.ext.piccolo.run_async_flow",
        new_callable=AsyncMock,
        return_value=None,
    ):
        with patch("fastapi_pagination.ext.piccolo.generic_flow") as mock_gf:
            mock_gf.return_value = iter([])
            asyncio.run(apaginate(query, additional_data=additional_data))

    call_kwargs = mock_gf.call_args.kwargs
    assert call_kwargs["additional_data"] is additional_data


# ─── paginate (deprecated) tests ─────────────────────────────────────────────


def test_paginate_delegates_to_apaginate():
    query = _MockSelect(table="my_table")
    expected = [{"id": 1}]

    with patch(
        "fastapi_pagination.ext.piccolo.apaginate",
        new_callable=AsyncMock,
        return_value=expected,
    ) as mock_ap:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = asyncio.run(paginate(query))

    assert result == expected
    mock_ap.assert_called_once_with(
        query,
        params=None,
        transformer=None,
        additional_data=None,
        config=None,
    )


def test_paginate_passes_all_args_to_apaginate():
    query = _MockSelect(table="my_table")
    params = MagicMock()
    transformer = MagicMock()
    additional_data = {"key": "val"}
    config = MagicMock()

    with patch(
        "fastapi_pagination.ext.piccolo.apaginate",
        new_callable=AsyncMock,
        return_value=None,
    ) as mock_ap:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            asyncio.run(
                paginate(
                    query,
                    params=params,
                    transformer=transformer,
                    additional_data=additional_data,
                    config=config,
                )
            )

    mock_ap.assert_called_once_with(
        query,
        params=params,
        transformer=transformer,
        additional_data=additional_data,
        config=config,
    )
