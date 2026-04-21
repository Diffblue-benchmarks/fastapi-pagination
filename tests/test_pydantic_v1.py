from fastapi_pagination.pydantic.v1 import BaseModelV1, is_pydantic_v1_model


class MyV1Model(BaseModelV1):
    name: str


class NotAModel:
    pass


def test_is_pydantic_v1_model_with_v1_model():
    assert is_pydantic_v1_model(MyV1Model) is True


def test_is_pydantic_v1_model_with_non_model():
    assert is_pydantic_v1_model(NotAModel) is False


def test_is_pydantic_v1_model_with_base_model_v1():
    assert is_pydantic_v1_model(BaseModelV1) is True
