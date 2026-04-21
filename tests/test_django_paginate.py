import sys
from unittest.mock import MagicMock

import pytest

# ---- Django mock setup (Django is not installed; mock before importing module) ----

class _FakeModelBase(type):
    """Minimal metaclass simulating Django's ModelBase."""


_django_mock = MagicMock()
_django_db_mock = MagicMock()
_django_db_models_mock = MagicMock()
_django_db_models_base_mock = MagicMock()
_django_db_models_base_mock.ModelBase = _FakeModelBase

_module_mocks = {
    "django": _django_mock,
    "django.db": _django_db_mock,
    "django.db.models": _django_db_models_mock,
    "django.db.models.base": _django_db_models_base_mock,
}

for _mod_name, _mod_mock in _module_mocks.items():
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = _mod_mock

# Ensure fresh import with our mocks in place
sys.modules.pop("fastapi_pagination.ext.django", None)

from fastapi_pagination.ext.django import paginate  # noqa: E402


# ---- Helper: a class that looks like a Django Model class (instance of ModelBase) ----

class _FakeModel(metaclass=_FakeModelBase):
    objects = MagicMock()


# ---- Tests ----

def test_paginate_with_model_class_calls_objects_all(mocker):
    mock_run = mocker.patch("fastapi_pagination.ext.django.run_sync_flow", return_value="page_result")
    mocker.patch("fastapi_pagination.ext.django.generic_flow")
    mocker.patch("fastapi_pagination.ext.django.flow_expr")

    queryset = MagicMock()
    _FakeModel.objects.all.return_value = queryset

    result = paginate(_FakeModel)

    _FakeModel.objects.all.assert_called_once()
    mock_run.assert_called_once()
    assert result == "page_result"


def test_paginate_with_queryset_skips_objects_all(mocker):
    mock_run = mocker.patch("fastapi_pagination.ext.django.run_sync_flow", return_value="page_result")
    mocker.patch("fastapi_pagination.ext.django.generic_flow")
    mocker.patch("fastapi_pagination.ext.django.flow_expr")

    queryset = MagicMock()

    result = paginate(queryset)

    mock_run.assert_called_once()
    assert result == "page_result"


def test_paginate_returns_run_sync_flow_result(mocker):
    expected = {"items": [1, 2, 3], "total": 3}
    mocker.patch("fastapi_pagination.ext.django.run_sync_flow", return_value=expected)
    mocker.patch("fastapi_pagination.ext.django.generic_flow")
    mocker.patch("fastapi_pagination.ext.django.flow_expr")

    result = paginate(MagicMock())

    assert result == expected


def test_paginate_passes_params_to_generic_flow(mocker):
    mocker.patch("fastapi_pagination.ext.django.run_sync_flow")
    mock_gf = mocker.patch("fastapi_pagination.ext.django.generic_flow")
    mocker.patch("fastapi_pagination.ext.django.flow_expr")

    params = MagicMock()
    paginate(MagicMock(), params)

    mock_gf.assert_called_once()
    assert mock_gf.call_args.kwargs["params"] == params


def test_paginate_passes_transformer_to_generic_flow(mocker):
    mocker.patch("fastapi_pagination.ext.django.run_sync_flow")
    mock_gf = mocker.patch("fastapi_pagination.ext.django.generic_flow")
    mocker.patch("fastapi_pagination.ext.django.flow_expr")

    transformer = MagicMock()
    paginate(MagicMock(), transformer=transformer)

    mock_gf.assert_called_once()
    assert mock_gf.call_args.kwargs["transformer"] == transformer


def test_paginate_passes_additional_data_to_generic_flow(mocker):
    mocker.patch("fastapi_pagination.ext.django.run_sync_flow")
    mock_gf = mocker.patch("fastapi_pagination.ext.django.generic_flow")
    mocker.patch("fastapi_pagination.ext.django.flow_expr")

    additional_data = {"key": "value"}
    paginate(MagicMock(), additional_data=additional_data)

    mock_gf.assert_called_once()
    assert mock_gf.call_args.kwargs["additional_data"] == additional_data


def test_paginate_passes_config_to_generic_flow(mocker):
    mocker.patch("fastapi_pagination.ext.django.run_sync_flow")
    mock_gf = mocker.patch("fastapi_pagination.ext.django.generic_flow")
    mocker.patch("fastapi_pagination.ext.django.flow_expr")

    config = MagicMock()
    paginate(MagicMock(), config=config)

    mock_gf.assert_called_once()
    assert mock_gf.call_args.kwargs["config"] == config
