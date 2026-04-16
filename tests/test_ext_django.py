from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch


def _setup_django_mocks():
    """Set up mock Django modules so fastapi_pagination.ext.django can be imported."""
    django_mock = ModuleType("django")
    django_db = ModuleType("django.db")
    django_db_models = ModuleType("django.db.models")
    django_db_models_base = ModuleType("django.db.models.base")

    # Create mock classes
    mock_model_base = type("ModelBase", (), {})
    mock_model = type("Model", (), {})
    mock_queryset = MagicMock()

    django_db_models.Model = mock_model
    django_db_models.QuerySet = mock_queryset
    django_db_models_base.ModelBase = mock_model_base

    django_mock.db = django_db
    django_db.models = django_db_models

    sys.modules.setdefault("django", django_mock)
    sys.modules.setdefault("django.db", django_db)
    sys.modules.setdefault("django.db.models", django_db_models)
    sys.modules.setdefault("django.db.models.base", django_db_models_base)

    return mock_model_base, mock_model, mock_queryset


_model_base_cls, _model_cls, _queryset_cls = _setup_django_mocks()

# Now safe to import the module under test
from fastapi_pagination.ext.django import paginate  # noqa: E402


def test_paginate_with_queryset_directly():
    """Test paginate when called with a QuerySet (not a ModelBase)."""
    mock_qs = MagicMock()
    mock_qs.__class__ = object  # not a ModelBase

    with patch("fastapi_pagination.ext.django.run_sync_flow") as mock_run, \
         patch("fastapi_pagination.ext.django.generic_flow") as mock_flow:
        mock_run.return_value = "page_result"
        mock_flow.return_value = "flow_obj"

        result = paginate(mock_qs)

        assert result == "page_result"
        mock_flow.assert_called_once()
        mock_run.assert_called_once_with("flow_obj")


def test_paginate_with_model_class_calls_all():
    """Test paginate when called with a ModelBase class - should call .objects.all()."""
    # Create a class that IS an instance of ModelBase (i.e., a class whose metaclass is ModelBase)
    mock_model_class = MagicMock(spec=_model_base_cls)
    mock_all_qs = MagicMock()
    mock_model_class.objects = MagicMock()
    mock_model_class.objects.all.return_value = mock_all_qs

    with patch("fastapi_pagination.ext.django.isinstance", side_effect=lambda obj, cls: cls is _model_base_cls), \
         patch("fastapi_pagination.ext.django.run_sync_flow") as mock_run, \
         patch("fastapi_pagination.ext.django.generic_flow") as mock_flow:
        mock_run.return_value = "page_result"
        mock_flow.return_value = "flow_obj"

        result = paginate(mock_model_class)

        assert result == "page_result"
        mock_model_class.objects.all.assert_called_once()


def test_paginate_passes_params_to_generic_flow():
    """Test that params are forwarded to generic_flow."""
    mock_qs = MagicMock()
    mock_params = MagicMock()

    with patch("fastapi_pagination.ext.django.run_sync_flow") as mock_run, \
         patch("fastapi_pagination.ext.django.generic_flow") as mock_flow:
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

    with patch("fastapi_pagination.ext.django.run_sync_flow") as mock_run, \
         patch("fastapi_pagination.ext.django.generic_flow") as mock_flow:
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

    with patch("fastapi_pagination.ext.django.run_sync_flow") as mock_run, \
         patch("fastapi_pagination.ext.django.generic_flow") as mock_flow:
        mock_run.return_value = "page_result"
        mock_flow.return_value = "flow_obj"

        paginate(mock_qs, config=mock_config)

        call_kwargs = mock_flow.call_args.kwargs
        assert call_kwargs["config"] is mock_config
