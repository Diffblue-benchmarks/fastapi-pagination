from typing import Annotated, Optional, Union

import pytest

from fastapi_pagination.typing_utils import create_annotated_tp, remove_optional_from_tp


def test_remove_optional_single_non_none():
    result = remove_optional_from_tp(Optional[int])
    assert result is int


def test_remove_optional_multiple_non_none():
    result = remove_optional_from_tp(Optional[Union[int, str]])
    assert result == int | str


def test_remove_optional_union_type_syntax():
    result = remove_optional_from_tp(int | None)
    assert result is int


def test_remove_optional_multi_union_type_syntax():
    result = remove_optional_from_tp(int | str | None)
    assert result == int | str


def test_remove_optional_annotated_with_none():
    result = remove_optional_from_tp(Annotated[Optional[int], "meta"])
    assert result == Annotated[int, "meta"]


def test_remove_optional_plain_type():
    result = remove_optional_from_tp(int)
    assert result is int


def test_remove_optional_annotated_no_none():
    result = remove_optional_from_tp(Annotated[int, "meta"])
    assert result == Annotated[int, "meta"]


def test_create_annotated_with_annotations():
    result = create_annotated_tp(int, "meta1", "meta2")
    assert result == Annotated[int, "meta1", "meta2"]


def test_create_annotated_no_annotations():
    result = create_annotated_tp(int)
    assert result is int


def test_create_annotated_single_annotation():
    result = create_annotated_tp(str, "label")
    assert result == Annotated[str, "label"]
