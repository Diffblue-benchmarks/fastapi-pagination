import pytest

from fastapi_pagination.pydantic.v1 import BaseModelV1, is_pydantic_v1_model


class MyV1Model(BaseModelV1):
    name: str


class NotAModel:
    pass


def test_is_pydantic_v1_model_returns_true_for_v1_model():
    assert is_pydantic_v1_model(MyV1Model) is True


def test_is_pydantic_v1_model_returns_false_for_non_model():
    assert is_pydantic_v1_model(NotAModel) is False


def test_is_pydantic_v1_model_returns_false_for_base_class():
    assert is_pydantic_v1_model(int) is False
