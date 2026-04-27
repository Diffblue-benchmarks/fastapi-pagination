from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from fastapi_pagination.ext.django import paginate


@pytest.fixture
def mock_queryset():
    qs = MagicMock()
    qs.count.return_value = 3
    qs.__getitem__ = MagicMock(return_value=[MagicMock(), MagicMock(), MagicMock()])
    return qs


@pytest.fixture
def mock_model_class(mock_queryset):
    from django.db.models.base import ModelBase

    model = MagicMock(spec=ModelBase)
    model.objects = MagicMock()
    model.objects.all.return_value = mock_queryset
    # Make isinstance(model, ModelBase) return True
    model.__class__ = ModelBase
    return model


def test_paginate_with_queryset(mock_queryset):
    with patch("fastapi_pagination.ext.django.run_sync_flow") as mock_run, \
         patch("fastapi_pagination.ext.django.generic_flow") as mock_flow:
        mock_run.return_value = "page_result"
        mock_flow.return_value = "flow_result"

        result = paginate(mock_queryset)

        assert result == "page_result"
        mock_run.assert_called_once_with("flow_result")
        mock_flow.assert_called_once()


def test_paginate_with_model_class(mock_queryset):
    from django.db.models.base import ModelBase

    # Create a mock that passes isinstance(mock_model, ModelBase) by setting __class__
    mock_model = MagicMock()
    mock_model.__class__ = ModelBase
    mock_model.objects = MagicMock()
    mock_model.objects.all.return_value = mock_queryset

    with patch("fastapi_pagination.ext.django.run_sync_flow") as mock_run, \
         patch("fastapi_pagination.ext.django.generic_flow") as mock_flow:
        mock_run.return_value = "model_page_result"
        mock_flow.return_value = "model_flow_result"

        result = paginate(mock_model)

        assert result == "model_page_result"
        mock_model.objects.all.assert_called_once()


def test_paginate_passes_params(mock_queryset):
    from fastapi_pagination.default import Params

    params = Params(page=1, size=5)

    with patch("fastapi_pagination.ext.django.run_sync_flow") as mock_run, \
         patch("fastapi_pagination.ext.django.generic_flow") as mock_flow:
        mock_run.return_value = "paged"
        mock_flow.return_value = "flow"

        paginate(mock_queryset, params=params)

        call_kwargs = mock_flow.call_args.kwargs
        assert call_kwargs["params"] == params


def test_paginate_passes_transformer(mock_queryset):
    transformer = MagicMock()

    with patch("fastapi_pagination.ext.django.run_sync_flow") as mock_run, \
         patch("fastapi_pagination.ext.django.generic_flow") as mock_flow:
        mock_run.return_value = "paged"
        mock_flow.return_value = "flow"

        paginate(mock_queryset, transformer=transformer)

        call_kwargs = mock_flow.call_args.kwargs
        assert call_kwargs["transformer"] == transformer


def test_paginate_passes_additional_data(mock_queryset):
    additional_data = {"key": "value"}

    with patch("fastapi_pagination.ext.django.run_sync_flow") as mock_run, \
         patch("fastapi_pagination.ext.django.generic_flow") as mock_flow:
        mock_run.return_value = "paged"
        mock_flow.return_value = "flow"

        paginate(mock_queryset, additional_data=additional_data)

        call_kwargs = mock_flow.call_args.kwargs
        assert call_kwargs["additional_data"] == additional_data


def test_paginate_passes_config(mock_queryset):
    from fastapi_pagination.config import Config

    config = Config()

    with patch("fastapi_pagination.ext.django.run_sync_flow") as mock_run, \
         patch("fastapi_pagination.ext.django.generic_flow") as mock_flow:
        mock_run.return_value = "paged"
        mock_flow.return_value = "flow"

        paginate(mock_queryset, config=config)

        call_kwargs = mock_flow.call_args.kwargs
        assert call_kwargs["config"] == config
