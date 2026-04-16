import pytest
from pydantic import BaseModel, Field
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

    assert isinstance(result, SampleModel)
    assert result.name == "Alice"
    assert result.age == 30


def test_create_pydantic_model_v2_defaults():
    result = create_pydantic_model(SampleModel, name="Bob")

    assert result.name == "Bob"
    assert result.age == 0


def test_get_model_fields_returns_dict():
    fields = get_model_fields(SampleModel)

    assert isinstance(fields, dict)
    assert "name" in fields
    assert "age" in fields


def test_get_model_fields_is_copy():
    fields1 = get_model_fields(SampleModel)
    fields2 = get_model_fields(SampleModel)

    assert fields1 is not fields2


def test_is_pydantic_field_with_field_info():
    field = FieldInfo(default=None)

    result = is_pydantic_field(field)

    if IS_PYDANTIC_V2:
        assert result is True
    else:
        assert isinstance(result, bool)


def test_is_pydantic_field_with_non_field():
    result = is_pydantic_field("not a field")

    assert result is False


def test_is_pydantic_v2_field_with_field_info():
    field = FieldInfo(default=None)

    result = is_pydantic_v2_field(field)

    if IS_PYDANTIC_V2:
        assert result is True
    else:
        assert result is False


def test_is_pydantic_v2_field_with_non_field():
    result = is_pydantic_v2_field("not a field")

    assert result is False


def test_is_pydantic_v1_field_with_non_field():
    result = is_pydantic_v1_field("not a field")

    assert result is False


def test_is_pydantic_v1_field_with_int():
    result = is_pydantic_v1_field(42)

    assert result is False


def test_get_field_tp_for_field_info():
    field = FieldInfo(annotation=str)

    result = get_field_tp(field)

    assert result is str


def test_get_field_tp_for_field_info_with_metadata():
    field = Field(..., ge=0)
    field_info = SampleModel.model_fields["age"] if IS_PYDANTIC_V2 else None

    if IS_PYDANTIC_V2 and field_info is not None:
        result = get_field_tp(field_info)
        assert result is not None
