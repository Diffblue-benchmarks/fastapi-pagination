from __future__ import annotations

from base64 import b64encode
from urllib.parse import quote

import pytest
from fastapi import HTTPException

from fastapi_pagination.cursor import (
    CursorPage,
    CursorParams,
    decode_cursor,
    default_encoder,
    encode_cursor,
)


def _b64(s: str) -> str:
    return b64encode(s.encode()).decode()


def _b64_quoted(s: str) -> str:
    return quote(b64encode(s.encode()).decode())


# --- decode_cursor ---

def test_decode_cursor_returns_none_for_none():
    assert decode_cursor(None) is None


def test_decode_cursor_returns_string_by_default():
    cursor = _b64_quoted("abc123")
    result = decode_cursor(cursor)
    assert result == "abc123"


def test_decode_cursor_returns_bytes_when_to_str_false():
    cursor = _b64_quoted("abc123")
    result = decode_cursor(cursor, to_str=False)
    assert result == b"abc123"


def test_decode_cursor_unquoted():
    cursor = _b64("hello")
    result = decode_cursor(cursor, quoted=False)
    assert result == "hello"


def test_decode_cursor_raises_on_invalid_base64():
    with pytest.raises(HTTPException) as exc_info:
        decode_cursor("!!!invalid!!!")
    assert exc_info.value.status_code == 400
    assert "Invalid cursor value" in exc_info.value.detail


# --- default_encoder ---

def test_default_encoder_returns_base64_string():
    data = b"test-data"
    result = default_encoder(data)
    assert result == b64encode(data).decode()


# --- encode_cursor ---

def test_encode_cursor_returns_none_for_none():
    assert encode_cursor(None) is None


def test_encode_cursor_string_cursor_quoted():
    result = encode_cursor("abc")
    expected = quote(b64encode(b"abc").decode())
    assert result == expected


def test_encode_cursor_bytes_cursor_quoted():
    result = encode_cursor(b"abc")
    expected = quote(b64encode(b"abc").decode())
    assert result == expected


def test_encode_cursor_not_quoted():
    result = encode_cursor("abc", quoted=False)
    expected = b64encode(b"abc").decode()
    assert result == expected


def test_encode_cursor_custom_encoder():
    result = encode_cursor("abc", quoted=False, encoder=lambda b: "custom")
    assert result == "custom"


# --- CursorParams ---

def test_cursor_params_to_raw_params_no_cursor():
    params = CursorParams(cursor=None, size=10)
    raw = params.to_raw_params()
    assert raw.cursor is None
    assert raw.size == 10


def test_cursor_params_to_raw_params_with_cursor():
    encoded = _b64_quoted("mycursor")
    params = CursorParams(cursor=encoded, size=20)
    raw = params.to_raw_params()
    assert raw.cursor == "mycursor"
    assert raw.size == 20


def test_cursor_params_encode_cursor():
    params = CursorParams()
    result = params.encode_cursor("hello")
    expected = quote(b64encode(b"hello").decode())
    assert result == expected


def test_cursor_params_encode_cursor_none():
    params = CursorParams()
    assert params.encode_cursor(None) is None


def test_cursor_params_decode_cursor():
    params = CursorParams()
    encoded = _b64_quoted("world")
    result = params.decode_cursor(encoded)
    assert result == "world"


def test_cursor_params_decode_cursor_none():
    params = CursorParams()
    assert params.decode_cursor(None) is None


# --- CursorPage ---

def test_cursor_page_create_raises_for_non_cursor_params():
    class FakeParams:
        pass

    with pytest.raises(TypeError, match="CursorPage should be used with CursorParams"):
        CursorPage.create([], FakeParams())


def test_cursor_page_create_with_cursor_params():
    params = CursorParams(size=10)
    page = CursorPage.create(
        items=["a", "b"],
        params=params,
        total=2,
        current="cur1",
        next_="nxt1",
    )
    assert page.items == ["a", "b"]
    assert page.next_page == params.encode_cursor("nxt1")
    assert page.current_page == params.encode_cursor("cur1")
    assert page.previous_page is None


def test_cursor_page_create_all_cursors():
    params = CursorParams(size=5)
    page = CursorPage.create(
        items=[1, 2],
        params=params,
        total=2,
        current="c",
        current_backwards="cb",
        next_="n",
        previous="p",
    )
    assert page.current_page == params.encode_cursor("c")
    assert page.current_page_backwards == params.encode_cursor("cb")
    assert page.next_page == params.encode_cursor("n")
    assert page.previous_page == params.encode_cursor("p")
