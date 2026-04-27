from typing import Annotated, Optional, Union, get_args, get_origin

import pytest

from fastapi_pagination.typing_utils import create_annotated_tp, remove_optional_from_tp


def test_remove_optional_single_type():
    result = remove_optional_from_tp(Optional[int])
    assert result is int


def test_remove_optional_union_with_none():
    result = remove_optional_from_tp(Union[int, None])
    assert result is int


def test_remove_optional_union_multiple_types_with_none():
    result = remove_optional_from_tp(Union[int, str, None])
    assert result == (int | str)


def test_remove_optional_union_no_none():
    result = remove_optional_from_tp(Union[int, str])
    assert result == (int | str)


def test_remove_optional_annotated_optional():
    tp = Annotated[Optional[int], "meta"]
    result = remove_optional_from_tp(tp)
    assert get_origin(result) is Annotated
    args = get_args(result)
    assert args[0] is int
    assert args[1] == "meta"


def test_remove_optional_plain_type():
    result = remove_optional_from_tp(int)
    assert result is int


def test_remove_optional_annotated_non_optional():
    tp = Annotated[int, "meta"]
    result = remove_optional_from_tp(tp)
    assert get_origin(result) is Annotated
    args = get_args(result)
    assert args[0] is int
    assert args[1] == "meta"


def test_create_annotated_tp_with_annotations():
    result = create_annotated_tp(int, "meta1", "meta2")
    assert get_origin(result) is Annotated
    args = get_args(result)
    assert args[0] is int
    assert args[1] == "meta1"
    assert args[2] == "meta2"


def test_create_annotated_tp_without_annotations():
    result = create_annotated_tp(int)
    assert result is int


def test_create_annotated_tp_single_annotation():
    result = create_annotated_tp(str, 42)
    assert get_origin(result) is Annotated
    args = get_args(result)
    assert args[0] is str
    assert args[1] == 42
