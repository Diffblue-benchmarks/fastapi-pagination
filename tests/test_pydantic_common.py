"""Tests for fastapi_pagination/pydantic/common.py"""
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


class SimpleModel(BaseModel):
    name: str
    age: int


class ModelWithOptional(BaseModel):
    name: str
    value: int = 0


# ---- create_pydantic_model ----

def test_create_pydantic_model_v2():
    result = create_pydantic_model(SimpleModel, name="Alice", age=30)
    assert isinstance(result, SimpleModel)
    assert result.name == "Alice"
    assert result.age == 30


def test_create_pydantic_model_v2_with_defaults():
    result = create_pydantic_model(ModelWithOptional, name="Bob")
    assert isinstance(result, ModelWithOptional)
    assert result.name == "Bob"
    assert result.value == 0


# ---- get_model_fields ----

def test_get_model_fields_returns_dict():
    fields = get_model_fields(SimpleModel)
    assert isinstance(fields, dict)
    assert "name" in fields
    assert "age" in fields


def test_get_model_fields_is_copy():
    fields1 = get_model_fields(SimpleModel)
    fields2 = get_model_fields(SimpleModel)
    assert fields1 is not fields2


# ---- is_pydantic_v2_field ----

def test_is_pydantic_v2_field_with_fieldinfo():
    if not IS_PYDANTIC_V2:
        pytest.skip("Only valid in pydantic v2")
    field = FieldInfo(default=None)
    assert is_pydantic_v2_field(field) is True


def test_is_pydantic_v2_field_with_non_field():
    assert is_pydantic_v2_field("not a field") is False
    assert is_pydantic_v2_field(42) is False
    assert is_pydantic_v2_field(None) is False


# ---- is_pydantic_v1_field ----

def test_is_pydantic_v1_field_with_v1_model_field():
    try:
        from pydantic.v1 import BaseModel as V1Model
        v1_model = V1Model.__fields__
        # Create a simple v1 model to get a ModelField
        class SampleV1(V1Model):
            x: int

        v1_field = SampleV1.__fields__["x"]
        assert is_pydantic_v1_field(v1_field) is True
    except (ImportError, AttributeError):
        pytest.skip("pydantic.v1 not available")


def test_is_pydantic_v1_field_with_non_field():
    assert is_pydantic_v1_field("not a field") is False
    assert is_pydantic_v1_field(42) is False
    assert is_pydantic_v1_field(None) is False


def test_is_pydantic_v1_field_with_v2_fieldinfo():
    if not IS_PYDANTIC_V2:
        pytest.skip("Only valid in pydantic v2")
    field = FieldInfo(default=None)
    assert is_pydantic_v1_field(field) is False


# ---- is_pydantic_field ----

def test_is_pydantic_field_with_fieldinfo():
    if not IS_PYDANTIC_V2:
        pytest.skip("Only valid in pydantic v2")
    field = FieldInfo(default=None)
    assert is_pydantic_field(field) is True


def test_is_pydantic_field_with_non_field():
    assert is_pydantic_field("not a field") is False
    assert is_pydantic_field(42) is False
    assert is_pydantic_field(None) is False


def test_is_pydantic_field_with_v1_field():
    try:
        from pydantic.v1 import BaseModel as V1Model

        class SampleV1(V1Model):
            x: int

        v1_field = SampleV1.__fields__["x"]
        assert is_pydantic_field(v1_field) is True
    except (ImportError, AttributeError):
        pytest.skip("pydantic.v1 not available")


# ---- get_field_tp (registered for FieldV2) ----

def test_get_field_tp_no_metadata():
    if not IS_PYDANTIC_V2:
        pytest.skip("Only valid in pydantic v2")
    field = FieldInfo(default=None)
    field.annotation = int
    result = get_field_tp(field)
    assert result is int


def test_get_field_tp_with_metadata():
    if not IS_PYDANTIC_V2:
        pytest.skip("Only valid in pydantic v2")
    from annotated_types import Gt
    field = FieldInfo(default=None)
    field.annotation = int
    field.metadata = [Gt(0)]
    result = get_field_tp(field)
    # Should be annotated type
    import typing
    assert hasattr(result, "__metadata__") or typing.get_args(result)


def test_get_field_tp_from_model_field():
    if not IS_PYDANTIC_V2:
        pytest.skip("Only valid in pydantic v2")
    fields = get_model_fields(SimpleModel)
    name_field = fields["name"]
    result = get_field_tp(name_field)
    assert result is str
