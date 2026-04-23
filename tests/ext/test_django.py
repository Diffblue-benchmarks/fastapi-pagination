from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest


# ──────────────────────────────────────────────────────────────────────────────
# Django is an optional dependency and is not installed in this environment.
# Inject minimal mock modules into sys.modules BEFORE importing the extension so
# that the top-level "from django…" imports in ext/django.py succeed.
# ──────────────────────────────────────────────────────────────────────────────


class _FakeModelBase(type):
    """Stand-in for django.db.models.base.ModelBase (a metaclass).

    Any class declared with ``metaclass=_FakeModelBase`` will pass
    ``isinstance(cls, _FakeModelBase)`` just like a real Django Model class
    passes ``isinstance(MyModel, ModelBase)``.
    """


_fake_models_base_module = MagicMock(name="django.db.models.base")
_fake_models_base_module.ModelBase = _FakeModelBase

sys.modules.setdefault("django", MagicMock(name="django"))
sys.modules.setdefault("django.db", MagicMock(name="django.db"))
sys.modules.setdefault("django.db.models", MagicMock(name="django.db.models"))
sys.modules.setdefault("django.db.models.base", _fake_models_base_module)

# Safe to import the extension now that Django mocks are in place.
from fastapi_pagination.ext.django import paginate  # noqa: E402


# ──────────────────────────────────────────────────────────────────────────────
# Helper: a class whose *type* is _FakeModelBase, mimicking a Django Model class
# ──────────────────────────────────────────────────────────────────────────────


class _FakeModel(metaclass=_FakeModelBase):
    """Fake Django Model class: isinstance(_FakeModel, _FakeModelBase) is True."""

    objects: MagicMock = MagicMock()


# ──────────────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────────────


def test_paginate_with_queryset_does_not_call_objects_all(mocker):
    """When query is a plain QuerySet (not a ModelBase), objects.all() is skipped."""
    mock_qs = MagicMock()
    mock_result = MagicMock()
    mock_run_sync = mocker.patch(
        "fastapi_pagination.ext.django.run_sync_flow", return_value=mock_result
    )

    result = paginate(mock_qs)

    assert result is mock_result
    mock_run_sync.assert_called_once()


def test_paginate_with_model_class_calls_objects_all(mocker):
    """When query is a ModelBase *class*, paginate converts it via .objects.all()."""
    mock_qs = MagicMock()
    _FakeModel.objects = MagicMock()
    _FakeModel.objects.all.return_value = mock_qs

    mock_result = MagicMock()
    mock_run_sync = mocker.patch(
        "fastapi_pagination.ext.django.run_sync_flow", return_value=mock_result
    )

    result = paginate(_FakeModel)

    assert result is mock_result
    _FakeModel.objects.all.assert_called_once()
    mock_run_sync.assert_called_once()


def test_paginate_returns_value_from_run_sync_flow(mocker):
    """The return value of paginate is exactly what run_sync_flow returns."""
    mock_qs = MagicMock()
    expected = {"items": [1, 2, 3], "total": 3}
    mocker.patch("fastapi_pagination.ext.django.run_sync_flow", return_value=expected)

    result = paginate(mock_qs)

    assert result == expected


def test_paginate_forwards_optional_args_to_generic_flow(mocker):
    """transformer, additional_data and config are forwarded to generic_flow."""
    mock_qs = MagicMock()
    mock_generic = mocker.patch(
        "fastapi_pagination.ext.django.generic_flow", return_value=MagicMock()
    )
    mocker.patch("fastapi_pagination.ext.django.run_sync_flow", return_value=MagicMock())

    transformer = MagicMock()
    additional_data = {"key": "value"}
    config = MagicMock()

    paginate(mock_qs, transformer=transformer, additional_data=additional_data, config=config)

    _, kwargs = mock_generic.call_args
    assert kwargs["transformer"] is transformer
    assert kwargs["additional_data"] is additional_data
    assert kwargs["config"] is config
