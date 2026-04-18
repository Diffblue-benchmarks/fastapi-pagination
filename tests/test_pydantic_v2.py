import pytest
from unittest.mock import patch


def test_is_pydantic_v2_model_returns_false_when_not_v2():
    with patch("fastapi_pagination.pydantic.v2.IS_PYDANTIC_V2", False):
        from fastapi_pagination.pydantic.v2 import is_pydantic_v2_model
        result = is_pydantic_v2_model(int)
    assert result is False


def test_is_pydantic_v2_model_returns_true_for_base_model_subclass():
    from fastapi_pagination.pydantic.consts import IS_PYDANTIC_V2
    if not IS_PYDANTIC_V2:
        pytest.skip("Requires pydantic v2")
    from pydantic import BaseModel
    from fastapi_pagination.pydantic.v2 import is_pydantic_v2_model

    class MyModel(BaseModel):
        pass

    assert is_pydantic_v2_model(MyModel) is True


def test_is_pydantic_v2_model_returns_false_for_non_model():
    from fastapi_pagination.pydantic.consts import IS_PYDANTIC_V2
    if not IS_PYDANTIC_V2:
        pytest.skip("Requires pydantic v2")
    from fastapi_pagination.pydantic.v2 import is_pydantic_v2_model

    assert is_pydantic_v2_model(int) is False
