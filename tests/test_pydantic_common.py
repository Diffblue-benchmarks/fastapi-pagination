from typing import Annotated, Optional

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


class SampleModel(BaseModel):
    name: str
    age: int = 0


class OptionalModel(BaseModel):
    value: Optional[int] = None


def test_create_pydantic_model_v2():
    result = create_pydantic_model(SampleModel, name="Alice", age=30)
    assert result.name == "Alice"
    assert result.age == 30


def test_create_pydantic_model_v2_default():
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


def test_is_pydantic_v2_field_with_fieldinfo():
    field = FieldInfo(annotation=str)
    assert is_pydantic_v2_field(field) is True


def test_is_pydantic_v2_field_with_non_field():
    assert is_pydantic_v2_field("not a field") is False
    assert is_pydantic_v2_field(42) is False
    assert is_pydantic_v2_field(None) is False


def test_is_pydantic_v1_field_returns_false_for_v2_field():
    field = FieldInfo(annotation=str)
    assert is_pydantic_v1_field(field) is False


def test_is_pydantic_v1_field_returns_false_for_non_field():
    assert is_pydantic_v1_field("not a field") is False
    assert is_pydantic_v1_field(42) is False


def test_is_pydantic_field_true_for_v2_field():
    field = FieldInfo(annotation=str)
    assert is_pydantic_field(field) is True


def test_is_pydantic_field_false_for_non_field():
    assert is_pydantic_field("not a field") is False
    assert is_pydantic_field(None) is False


def test_get_field_tp_without_metadata():
    field = FieldInfo(annotation=str)
    result = get_field_tp(field)
    assert result is str


def test_get_field_tp_with_metadata():
    from annotated_types import Gt

    class ModelWithMeta(BaseModel):
        value: Annotated[int, Gt(0)]

    field = ModelWithMeta.model_fields["value"]
    assert field.metadata  # sanity check that metadata is populated
    result = get_field_tp(field)
    assert result == Annotated[int, Gt(0)]
