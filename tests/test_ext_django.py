import pytest
from unittest.mock import MagicMock, patch


def test_paginate_with_queryset(mocker):
    """Test paginate when query is already a QuerySet (not a Model class)."""
    mock_queryset = MagicMock()
    mock_queryset.count.return_value = 3
    mock_queryset.__getitem__ = MagicMock(return_value=[1, 2, 3])

    mock_page = MagicMock()
    mock_run_sync_flow = mocker.patch("fastapi_pagination.ext.django.run_sync_flow", return_value=mock_page)
    mock_generic_flow = mocker.patch("fastapi_pagination.ext.django.generic_flow", return_value=MagicMock())

    from django.db.models.base import ModelBase
    assert not isinstance(mock_queryset, ModelBase)

    from fastapi_pagination.ext.django import paginate

    result = paginate(mock_queryset)

    assert result == mock_page
    mock_run_sync_flow.assert_called_once()
    mock_generic_flow.assert_called_once()


def test_paginate_with_model_class(mocker):
    """Test paginate when query is a Model class (ModelBase), so .objects.all() is called."""
    import django
    import django.conf

    if not django.conf.settings.configured:
        django.conf.settings.configure(
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                }
            },
            INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth"],
        )
        django.setup()

    from django.db import models

    class FakeModel(models.Model):
        name = models.CharField(max_length=100)

        class Meta:
            app_label = "test_app"

    mock_queryset = MagicMock()
    mock_queryset.count.return_value = 2
    mock_queryset.__getitem__ = MagicMock(return_value=[1, 2])

    mocker.patch.object(FakeModel, "objects", create=True)
    FakeModel.objects.all.return_value = mock_queryset

    mock_page = MagicMock()
    mock_run_sync_flow = mocker.patch("fastapi_pagination.ext.django.run_sync_flow", return_value=mock_page)
    mock_generic_flow = mocker.patch("fastapi_pagination.ext.django.generic_flow", return_value=MagicMock())

    from fastapi_pagination.ext.django import paginate

    result = paginate(FakeModel)

    assert result == mock_page
    FakeModel.objects.all.assert_called_once()
    mock_run_sync_flow.assert_called_once()
    mock_generic_flow.assert_called_once()


def test_paginate_passes_params_to_generic_flow(mocker):
    """Test that params, transformer, additional_data, config are forwarded."""
    mock_queryset = MagicMock()

    mock_page = MagicMock()
    mocker.patch("fastapi_pagination.ext.django.run_sync_flow", return_value=mock_page)
    mock_generic_flow = mocker.patch("fastapi_pagination.ext.django.generic_flow", return_value=MagicMock())

    mock_params = MagicMock()
    mock_transformer = MagicMock()
    mock_additional_data = MagicMock()
    mock_config = MagicMock()

    from fastapi_pagination.ext.django import paginate

    paginate(
        mock_queryset,
        params=mock_params,
        transformer=mock_transformer,
        additional_data=mock_additional_data,
        config=mock_config,
    )

    call_kwargs = mock_generic_flow.call_args.kwargs
    assert call_kwargs["params"] == mock_params
    assert call_kwargs["transformer"] == mock_transformer
    assert call_kwargs["additional_data"] == mock_additional_data
    assert call_kwargs["config"] == mock_config
