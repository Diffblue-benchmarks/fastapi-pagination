from __future__ import annotations

import pytest

from fastapi_pagination.pydantic.v2 import is_pydantic_v2_model
from fastapi_pagination.pydantic.consts import IS_PYDANTIC_V2


# --- is_pydantic_v2_model ---


@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="Requires pydantic v2")
def test_is_pydantic_v2_model_with_base_model_subclass():
    from pydantic import BaseModel

    class MyModel(BaseModel):
        name: str

    assert is_pydantic_v2_model(MyModel) is True


@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="Requires pydantic v2")
def test_is_pydantic_v2_model_with_non_model_class():
    class PlainClass:
        pass

    assert is_pydantic_v2_model(PlainClass) is False


@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="Requires pydantic v2")
def test_is_pydantic_v2_model_with_base_model_itself():
    from pydantic import BaseModel

    assert is_pydantic_v2_model(BaseModel) is True


@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="Requires pydantic v2")
def test_is_pydantic_v2_model_with_builtin_type():
    assert is_pydantic_v2_model(int) is False


def test_is_pydantic_v2_model_returns_false_when_not_pydantic_v2(mocker):
    mocker.patch("fastapi_pagination.pydantic.v2.IS_PYDANTIC_V2", False)
    result = is_pydantic_v2_model(object)
    assert result is False
