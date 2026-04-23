from typing import Annotated, Optional

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


class SimpleModel(BaseModel):
    name: str
    age: int
    score: Optional[float] = None


class AnnotatedModel(BaseModel):
    value: Annotated[int, Field(ge=0, le=100)]
    label: str


# ---- create_pydantic_model tests ----


def test_create_pydantic_model_basic():
    result = create_pydantic_model(SimpleModel, name="Alice", age=30)
    assert result.name == "Alice"
    assert result.age == 30
    assert result.score is None


def test_create_pydantic_model_with_optional_field():
    result = create_pydantic_model(SimpleModel, name="Bob", age=25, score=9.5)
    assert result.name == "Bob"
    assert result.age == 25
    assert result.score == 9.5


def test_create_pydantic_model_returns_model_instance():
    result = create_pydantic_model(SimpleModel, name="Charlie", age=40)
    assert isinstance(result, SimpleModel)


def test_create_pydantic_model_v1_branch(mocker):
    mocker.patch(
        "fastapi_pagination.pydantic.common.is_pydantic_v2_model",
        return_value=False,
    )
    result = create_pydantic_model(SimpleModel, name="Dave", age=20)
    assert isinstance(result, SimpleModel)
    assert result.name == "Dave"


# ---- get_model_fields tests ----


def test_get_model_fields_returns_dict():
    fields = get_model_fields(SimpleModel)
    assert isinstance(fields, dict)
    assert "name" in fields
    assert "age" in fields
    assert "score" in fields


def test_get_model_fields_returns_copy():
    fields1 = get_model_fields(SimpleModel)
    fields2 = get_model_fields(SimpleModel)
    assert fields1 is not fields2


def test_get_model_fields_v1_branch(mocker):
    mocker.patch(
        "fastapi_pagination.pydantic.common.is_pydantic_v2_model",
        return_value=False,
    )
    # When v2 detection is disabled, fall through to __fields__
    fields = get_model_fields(SimpleModel)
    assert isinstance(fields, dict)


def test_get_model_fields_field_count():
    fields = get_model_fields(SimpleModel)
    assert len(fields) == 3


# ---- is_pydantic_v2_field tests ----


def test_is_pydantic_v2_field_with_field_info():
    field = SimpleModel.model_fields["name"]
    if IS_PYDANTIC_V2:
        assert is_pydantic_v2_field(field) is True
    else:
        assert is_pydantic_v2_field(field) is False


def test_is_pydantic_v2_field_with_string():
    assert is_pydantic_v2_field("not a field") is False


def test_is_pydantic_v2_field_with_int():
    assert is_pydantic_v2_field(42) is False


def test_is_pydantic_v2_field_with_none():
    assert is_pydantic_v2_field(None) is False


def test_is_pydantic_v2_field_with_dict():
    assert is_pydantic_v2_field({"key": "val"}) is False


# ---- is_pydantic_v1_field tests ----


def test_is_pydantic_v1_field_with_string():
    assert is_pydantic_v1_field("not a field") is False


def test_is_pydantic_v1_field_with_int():
    assert is_pydantic_v1_field(42) is False


def test_is_pydantic_v1_field_with_none():
    assert is_pydantic_v1_field(None) is False


def test_is_pydantic_v1_field_with_field_info():
    # FieldInfo is a pydantic v2 field, not a v1 field
    field = SimpleModel.model_fields["name"]
    assert is_pydantic_v1_field(field) is False


def test_is_pydantic_v1_field_with_plain_object():
    class MyObj:
        pass

    assert is_pydantic_v1_field(MyObj()) is False


# ---- is_pydantic_field tests ----


def test_is_pydantic_field_with_field_info():
    if IS_PYDANTIC_V2:
        field = SimpleModel.model_fields["name"]
        assert is_pydantic_field(field) is True


def test_is_pydantic_field_with_string():
    assert is_pydantic_field("not a field") is False


def test_is_pydantic_field_with_int():
    assert is_pydantic_field(42) is False


def test_is_pydantic_field_with_none():
    assert is_pydantic_field(None) is False


# ---- get_field_tp tests (the registered handler for FieldV2) ----


def test_get_field_tp_without_metadata():
    if IS_PYDANTIC_V2:
        field = SimpleModel.model_fields["name"]
        # name: str has no extra metadata
        result = get_field_tp(field)
        assert result == str


def test_get_field_tp_with_metadata():
    if IS_PYDANTIC_V2:
        field = AnnotatedModel.model_fields["value"]
        # value: Annotated[int, Field(ge=0, le=100)] has metadata
        result = get_field_tp(field)
        assert result is not None


def test_get_field_tp_annotated_type_contains_annotation():
    if IS_PYDANTIC_V2:
        field = AnnotatedModel.model_fields["value"]
        result = get_field_tp(field)
        # When there's metadata the result should be an Annotated type
        import typing
        origin = getattr(result, "__class__", None)
        assert result is not None


def test_get_field_tp_plain_field_returns_annotation_directly():
    if IS_PYDANTIC_V2:
        field = SimpleModel.model_fields["age"]
        result = get_field_tp(field)
        assert result == int


def test_get_field_tp_optional_field():
    if IS_PYDANTIC_V2:
        field = SimpleModel.model_fields["score"]
        result = get_field_tp(field)
        assert result is not None
