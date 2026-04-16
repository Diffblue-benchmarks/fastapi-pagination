from typing import Annotated, Optional, Union

import pytest

from fastapi_pagination.typing_utils import create_annotated_tp, remove_optional_from_tp


def test_remove_optional_from_tp_simple_optional():
    result = remove_optional_from_tp(Optional[int])
    assert result is int


def test_remove_optional_from_tp_union_without_none():
    result = remove_optional_from_tp(Union[int, str])
    assert result == int | str


def test_remove_optional_from_tp_union_multiple_non_none():
    result = remove_optional_from_tp(Union[int, str, float])
    assert result == int | str | float


def test_remove_optional_from_tp_non_union():
    result = remove_optional_from_tp(int)
    assert result is int


def test_remove_optional_from_tp_annotated_optional():
    tp = Annotated[Optional[int], "meta"]
    result = remove_optional_from_tp(tp)
    assert result == Annotated[int, "meta"]


def test_remove_optional_from_tp_annotated_non_optional():
    tp = Annotated[int, "meta"]
    result = remove_optional_from_tp(tp)
    assert result == Annotated[int, "meta"]


def test_remove_optional_from_tp_pipe_syntax_optional():
    result = remove_optional_from_tp(int | None)
    assert result is int


def test_remove_optional_from_tp_pipe_syntax_union():
    result = remove_optional_from_tp(int | str | None)
    assert result == int | str


def test_create_annotated_tp_with_annotations():
    result = create_annotated_tp(int, "meta")
    assert result == Annotated[int, "meta"]


def test_create_annotated_tp_multiple_annotations():
    result = create_annotated_tp(int, "meta1", "meta2")
    assert result == Annotated[int, "meta1", "meta2"]


def test_create_annotated_tp_no_annotations():
    result = create_annotated_tp(int)
    assert result is int
