from unittest.mock import patch

import pytest
from pydantic import BaseModel

from fastapi_pagination.pydantic.v2 import is_pydantic_v2_model


class _MyPydanticModel(BaseModel):
    pass


class _NotAModel:
    pass


def test_is_pydantic_v2_model_returns_true_for_base_model_subclass():
    result = is_pydantic_v2_model(_MyPydanticModel)
    assert result is True


def test_is_pydantic_v2_model_returns_false_for_non_model():
    result = is_pydantic_v2_model(_NotAModel)
    assert result is False


def test_is_pydantic_v2_model_returns_false_when_not_pydantic_v2():
    with patch("fastapi_pagination.pydantic.v2.IS_PYDANTIC_V2", False):
        result = is_pydantic_v2_model(_MyPydanticModel)
        assert result is False
