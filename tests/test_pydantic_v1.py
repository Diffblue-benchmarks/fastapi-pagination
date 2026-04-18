from fastapi_pagination.pydantic.v1 import BaseModelV1, is_pydantic_v1_model


def test_is_pydantic_v1_model_with_v1_model():
    class MyModel(BaseModelV1):
        name: str

    assert is_pydantic_v1_model(MyModel) is True


def test_is_pydantic_v1_model_with_non_model():
    class NotAModel:
        pass

    assert is_pydantic_v1_model(NotAModel) is False


def test_is_pydantic_v1_model_with_plain_type():
    assert is_pydantic_v1_model(str) is False
