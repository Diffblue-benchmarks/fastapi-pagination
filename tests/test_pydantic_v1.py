from __future__ import annotations

import pytest

from fastapi_pagination.pydantic.v1 import BaseModelV1, is_pydantic_v1_model


class _SampleV1Model(BaseModelV1):
    name: str


def test_is_pydantic_v1_model_returns_true_for_v1_model():
    assert is_pydantic_v1_model(_SampleV1Model) is True


def test_is_pydantic_v1_model_returns_false_for_plain_class():
    class PlainClass:
        pass

    assert is_pydantic_v1_model(PlainClass) is False


def test_is_pydantic_v1_model_returns_false_for_non_class():
    assert is_pydantic_v1_model(42) is False  # type: ignore[arg-type]


def test_is_pydantic_v1_model_returns_true_for_base_model_v1_itself():
    assert is_pydantic_v1_model(BaseModelV1) is True
