from __future__ import annotations

import pytest
from fastapi import HTTPException

from fastapi_pagination.cursor import (
    CursorPage,
    CursorParams,
    decode_cursor,
    default_encoder,
    encode_cursor,
)


# --- decode_cursor ---

def test_decode_cursor_none_returns_none():
    assert decode_cursor(None) is None


def test_decode_cursor_empty_string_returns_none():
    assert decode_cursor("") is None


def test_decode_cursor_valid_str():
    from base64 import b64encode
    from urllib.parse import quote

    original = "some-cursor-value"
    encoded = quote(b64encode(original.encode()).decode())
    result = decode_cursor(encoded)
    assert result == original


def test_decode_cursor_valid_bytes():
    from base64 import b64encode
    from urllib.parse import quote

    original = b"binary-cursor"
    encoded = quote(b64encode(original).decode())
    result = decode_cursor(encoded, to_str=False)
    assert result == original


def test_decode_cursor_not_quoted():
    from base64 import b64encode

    original = "cursor-value"
    encoded = b64encode(original.encode()).decode()
    result = decode_cursor(encoded, quoted=False)
    assert result == original


def test_decode_cursor_invalid_raises_http_exception():
    with pytest.raises(HTTPException) as exc_info:
        decode_cursor("not-valid-base64!!!", quoted=False)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid cursor value"


# --- default_encoder ---

def test_default_encoder_roundtrip():
    data = b"hello world"
    encoded = default_encoder(data)
    from base64 import b64decode
    assert b64decode(encoded.encode()) == data


# --- encode_cursor ---

def test_encode_cursor_none_returns_none():
    assert encode_cursor(None) is None


def test_encode_cursor_str_quoted():
    from base64 import b64encode
    from urllib.parse import quote

    cursor = "abc123"
    result = encode_cursor(cursor)
    expected = quote(b64encode(cursor.encode()).decode())
    assert result == expected


def test_encode_cursor_bytes_quoted():
    from base64 import b64encode
    from urllib.parse import quote

    cursor = b"abc123"
    result = encode_cursor(cursor)
    expected = quote(b64encode(cursor).decode())
    assert result == expected


def test_encode_cursor_not_quoted():
    from base64 import b64encode

    cursor = "abc"
    result = encode_cursor(cursor, quoted=False)
    expected = b64encode(cursor.encode()).decode()
    assert result == expected


def test_encode_cursor_custom_encoder():
    cursor = "test"
    result = encode_cursor(cursor, encoder=lambda b: "custom")
    assert result == "custom"


# --- CursorParams ---

def test_cursor_params_to_raw_params_default():
    params = CursorParams()
    raw = params.to_raw_params()
    assert raw.cursor is None
    assert raw.size == 50


def test_cursor_params_to_raw_params_with_cursor():
    from base64 import b64encode
    from urllib.parse import quote

    original = "my-cursor"
    encoded = quote(b64encode(original.encode()).decode())
    params = CursorParams(cursor=encoded, size=10)
    raw = params.to_raw_params()
    assert raw.cursor == original
    assert raw.size == 10


def test_cursor_params_encode_cursor_none():
    params = CursorParams()
    assert params.encode_cursor(None) is None


def test_cursor_params_encode_cursor_value():
    params = CursorParams()
    result = params.encode_cursor("hello")
    assert result is not None
    decoded = params.decode_cursor(result)
    assert decoded == "hello"


def test_cursor_params_decode_cursor_none():
    params = CursorParams()
    assert params.decode_cursor(None) is None


def test_cursor_params_decode_cursor_value():
    from base64 import b64encode
    from urllib.parse import quote

    original = "cursor-abc"
    encoded = quote(b64encode(original.encode()).decode())
    params = CursorParams()
    assert params.decode_cursor(encoded) == original


# --- CursorPage ---

def test_cursor_page_create_with_wrong_params():
    from fastapi_pagination.bases import RawParams

    class FakeParams:
        def to_raw_params(self):
            return RawParams()

    with pytest.raises(TypeError, match="CursorPage should be used with CursorParams"):
        CursorPage.create([], FakeParams())


def test_cursor_page_create_basic():
    params = CursorParams()
    page = CursorPage.create(
        items=["a", "b"],
        params=params,
        next_="next-cursor",
        previous="prev-cursor",
        total=2,
    )
    assert page.items == ["a", "b"]
    assert page.next_page is not None
    assert page.previous_page is not None
    assert page.current_page is None
    assert page.current_page_backwards is None


def test_cursor_page_create_all_cursors():
    params = CursorParams()
    page = CursorPage.create(
        items=[1, 2, 3],
        params=params,
        current="cur",
        current_backwards="cur-back",
        next_="nxt",
        previous="prv",
        total=3,
    )
    assert page.current_page is not None
    assert page.current_page_backwards is not None
    assert page.next_page is not None
    assert page.previous_page is not None
