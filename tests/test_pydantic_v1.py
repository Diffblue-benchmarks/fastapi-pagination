import pytest

from fastapi_pagination.pydantic.v1 import BaseModelV1, is_pydantic_v1_model


class MyV1Model(BaseModelV1):
    name: str


def test_is_pydantic_v1_model_with_v1_model():
    assert is_pydantic_v1_model(MyV1Model) is True


def test_is_pydantic_v1_model_with_base_v1_model():
    assert is_pydantic_v1_model(BaseModelV1) is True


def test_is_pydantic_v1_model_with_plain_class():
    class PlainClass:
        pass

    assert is_pydantic_v1_model(PlainClass) is False


def test_is_pydantic_v1_model_with_non_class():
    assert is_pydantic_v1_model(42) is False  # type: ignore[arg-type]
