import pytest
from unittest.mock import patch

from fastapi_pagination.pydantic.v2 import is_pydantic_v2_model


def test_is_pydantic_v2_model_returns_false_when_not_pydantic_v2():
    with patch("fastapi_pagination.pydantic.v2.IS_PYDANTIC_V2", False):
        result = is_pydantic_v2_model(int)
    assert result is False


def test_is_pydantic_v2_model_returns_true_for_basemodel_subclass():
    from pydantic import BaseModel

    class MyModel(BaseModel):
        name: str

    result = is_pydantic_v2_model(MyModel)
    assert result is True


def test_is_pydantic_v2_model_returns_false_for_non_model_class():
    class PlainClass:
        pass

    result = is_pydantic_v2_model(PlainClass)
    assert result is False
