from typing import Annotated, Optional, Union

import pytest

from fastapi_pagination.typing_utils import create_annotated_tp, remove_optional_from_tp


def test_remove_optional_from_tp_simple_optional():
    result = remove_optional_from_tp(Optional[int])
    assert result is int


def test_remove_optional_from_tp_union_with_none():
    result = remove_optional_from_tp(Union[str, None])
    assert result is str


def test_remove_optional_from_tp_union_multiple_types():
    result = remove_optional_from_tp(Union[int, str, None])
    assert result == int | str


def test_remove_optional_from_tp_no_optional():
    result = remove_optional_from_tp(int)
    assert result is int


def test_remove_optional_from_tp_annotated_optional():
    tp = Annotated[Optional[int], "meta"]
    result = remove_optional_from_tp(tp)
    assert result == Annotated[int, "meta"]


def test_remove_optional_from_tp_annotated_no_optional():
    tp = Annotated[int, "meta"]
    result = remove_optional_from_tp(tp)
    assert result == Annotated[int, "meta"]


def test_remove_optional_from_tp_union_type_syntax():
    # Python 3.10 union type syntax: int | None
    result = remove_optional_from_tp(int | None)
    assert result is int


def test_remove_optional_from_tp_union_type_multiple():
    # Python 3.10 union type syntax: int | str | None
    result = remove_optional_from_tp(int | str | None)
    assert result == int | str


def test_create_annotated_tp_with_annotations():
    result = create_annotated_tp(int, "meta1", "meta2")
    assert result == Annotated[int, "meta1", "meta2"]


def test_create_annotated_tp_single_annotation():
    result = create_annotated_tp(str, "label")
    assert result == Annotated[str, "label"]


def test_create_annotated_tp_no_annotations():
    result = create_annotated_tp(int)
    assert result is int


def test_create_annotated_tp_no_annotations_str():
    result = create_annotated_tp(str)
    assert result is str
