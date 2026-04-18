from typing import Optional

import pytest
from pydantic import BaseModel
from pydantic.fields import FieldInfo

from fastapi_pagination.pydantic.common import (
    create_pydantic_model,
    get_field_tp,
    get_model_fields,
    is_pydantic_field,
    is_pydantic_v1_field,
    is_pydantic_v2_field,
)
from fastapi_pagination.pydantic.consts import IS_PYDANTIC_V2


class SampleModel(BaseModel):
    name: str
    age: int = 0


def test_create_pydantic_model_v2():
    result = create_pydantic_model(SampleModel, name="Alice", age=30)
    assert result.name == "Alice"
    assert result.age == 30


def test_create_pydantic_model_v2_defaults():
    result = create_pydantic_model(SampleModel, name="Bob")
    assert result.name == "Bob"
    assert result.age == 0


def test_get_model_fields_v2():
    fields = get_model_fields(SampleModel)
    assert "name" in fields
    assert "age" in fields


def test_get_model_fields_returns_copy():
    fields1 = get_model_fields(SampleModel)
    fields2 = get_model_fields(SampleModel)
    assert fields1 is not fields2


def test_is_pydantic_field_with_field_info():
    field = FieldInfo(default=None)
    if IS_PYDANTIC_V2:
        assert is_pydantic_field(field) is True
    else:
        assert is_pydantic_field(field) is False


def test_is_pydantic_field_with_non_field():
    assert is_pydantic_field("not a field") is False
    assert is_pydantic_field(42) is False
    assert is_pydantic_field(None) is False


def test_is_pydantic_v2_field_with_field_info():
    field = FieldInfo(default=None)
    if IS_PYDANTIC_V2:
        assert is_pydantic_v2_field(field) is True
    else:
        assert is_pydantic_v2_field(field) is False


def test_is_pydantic_v2_field_with_non_field():
    assert is_pydantic_v2_field("not a field") is False
    assert is_pydantic_v2_field(42) is False


def test_is_pydantic_v1_field_with_non_field():
    assert is_pydantic_v1_field("not a field") is False
    assert is_pydantic_v1_field(42) is False
    assert is_pydantic_v1_field(None) is False


def test_is_pydantic_v1_field_with_field_info():
    # FieldInfo is a v2 field, not v1
    field = FieldInfo(default=None)
    assert is_pydantic_v1_field(field) is False


def test_get_field_tp_without_metadata():
    field = SampleModel.model_fields["name"]
    result = get_field_tp(field)
    assert result is str


def test_get_field_tp_with_metadata():
    from typing import Annotated
    from pydantic import Field

    class AnnotatedModel(BaseModel):
        value: Annotated[int, Field(ge=0)]

    field = AnnotatedModel.model_fields["value"]
    result = get_field_tp(field)
    # With metadata, returns Annotated type
    assert result is not None
