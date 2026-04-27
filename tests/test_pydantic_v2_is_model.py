import pytest
from unittest.mock import patch

from fastapi_pagination.pydantic.v2 import is_pydantic_v2_model
from fastapi_pagination.pydantic.consts import IS_PYDANTIC_V2


class NotAModel:
    pass


def test_is_pydantic_v2_model_returns_false_for_non_model():
    assert is_pydantic_v2_model(NotAModel) is False


def test_is_pydantic_v2_model_when_pydantic_v2_not_available():
    with patch("fastapi_pagination.pydantic.v2.IS_PYDANTIC_V2", False):
        result = is_pydantic_v2_model(NotAModel)
        assert result is False


@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="Requires pydantic v2")
def test_is_pydantic_v2_model_returns_true_for_pydantic_model():
    from pydantic import BaseModel

    class MyModel(BaseModel):
        x: int

    assert is_pydantic_v2_model(MyModel) is True


@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="Requires pydantic v2")
def test_is_pydantic_v2_model_returns_false_for_non_pydantic_class():
    assert is_pydantic_v2_model(int) is False
