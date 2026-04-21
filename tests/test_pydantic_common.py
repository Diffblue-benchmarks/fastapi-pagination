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
from fastapi_pagination.pydantic.consts import IS_PYDANTIC_V2


class SampleModel(BaseModel):
    name: str
    age: int = 0


# --- create_pydantic_model ---

def test_create_pydantic_model_v2():
    instance = create_pydantic_model(SampleModel, name="Alice", age=30)
    assert isinstance(instance, SampleModel)
    assert instance.name == "Alice"
    assert instance.age == 30


def test_create_pydantic_model_v2_defaults():
    instance = create_pydantic_model(SampleModel, name="Bob")
    assert instance.name == "Bob"
    assert instance.age == 0


# --- get_model_fields ---

def test_get_model_fields_v2_returns_dict():
    fields = get_model_fields(SampleModel)
    assert isinstance(fields, dict)
    assert "name" in fields
    assert "age" in fields


def test_get_model_fields_v2_is_copy():
    fields1 = get_model_fields(SampleModel)
    fields2 = get_model_fields(SampleModel)
    assert fields1 is not fields2


# --- is_pydantic_field ---

def test_is_pydantic_field_with_field_info():
    field = FieldInfo(default=None)
    assert is_pydantic_field(field) is True


def test_is_pydantic_field_with_non_field():
    assert is_pydantic_field("not_a_field") is False
    assert is_pydantic_field(42) is False
    assert is_pydantic_field(None) is False


# --- is_pydantic_v2_field ---

def test_is_pydantic_v2_field_with_field_info():
    if not IS_PYDANTIC_V2:
        pytest.skip("Pydantic v2 not installed")
    field = FieldInfo(default=None)
    assert is_pydantic_v2_field(field) is True


def test_is_pydantic_v2_field_with_non_field():
    assert is_pydantic_v2_field("string") is False
    assert is_pydantic_v2_field(123) is False


# --- is_pydantic_v1_field ---

def test_is_pydantic_v1_field_with_field_info_returns_false():
    field = FieldInfo(default=None)
    # FieldInfo is a v2 type, not a v1 ModelField
    assert is_pydantic_v1_field(field) is False


def test_is_pydantic_v1_field_with_plain_object():
    assert is_pydantic_v1_field("string") is False
    assert is_pydantic_v1_field(42) is False


def test_is_pydantic_v1_field_with_pydantic_v1_compat():
    # When IS_PYDANTIC_V2, names only includes pydantic.v1.fields.ModelField
    # A plain object won't match those names
    assert is_pydantic_v1_field(object()) is False


# --- get_field_tp (singledispatch registered for FieldV2) ---

def test_get_field_tp_v2_no_metadata():
    if not IS_PYDANTIC_V2:
        pytest.skip("Pydantic v2 not installed")
    field = FieldInfo(default=None)
    field.annotation = str
    result = get_field_tp(field)
    assert result is str


def test_get_field_tp_v2_with_metadata():
    if not IS_PYDANTIC_V2:
        pytest.skip("Pydantic v2 not installed")
    from annotated_types import Gt
    field = FieldInfo.from_annotation(Annotated[int, Gt(0)])
    result = get_field_tp(field)
    assert result == Annotated[int, Gt(0)]
