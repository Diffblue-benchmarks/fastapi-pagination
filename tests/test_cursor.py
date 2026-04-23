from __future__ import annotations

import pytest
from base64 import b64encode
from urllib.parse import quote

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
    original = "hello"
    encoded = b64encode(original.encode()).decode()
    quoted = quote(encoded)
    result = decode_cursor(quoted)
    assert result == original


def test_decode_cursor_valid_bytes():
    original = b"hello"
    encoded = b64encode(original).decode()
    quoted = quote(encoded)
    result = decode_cursor(quoted, to_str=False)
    assert result == original


def test_decode_cursor_not_quoted():
    original = "world"
    encoded = b64encode(original.encode()).decode()
    result = decode_cursor(encoded, quoted=False)
    assert result == original


def test_decode_cursor_invalid_base64_raises_http_exception():
    with pytest.raises(HTTPException) as exc_info:
        decode_cursor("!!!not-valid-base64!!!", quoted=False)
    assert exc_info.value.status_code == 400
    assert "Invalid cursor value" in exc_info.value.detail


def test_decode_cursor_invalid_utf8_raises_http_exception():
    # Encode raw bytes that are not valid UTF-8
    raw_bytes = b"\xff\xfe"
    encoded = b64encode(raw_bytes).decode()
    with pytest.raises(HTTPException) as exc_info:
        decode_cursor(encoded, quoted=False, to_str=True)
    assert exc_info.value.status_code == 400


# --- default_encoder ---

def test_default_encoder_roundtrip():
    data = b"test-data"
    result = default_encoder(data)
    assert result == b64encode(data).decode()


def test_default_encoder_returns_str():
    result = default_encoder(b"abc")
    assert isinstance(result, str)


# --- encode_cursor ---

def test_encode_cursor_none_returns_none():
    assert encode_cursor(None) is None


def test_encode_cursor_str():
    result = encode_cursor("hello")
    assert result is not None
    decoded = decode_cursor(result)
    assert decoded == "hello"


def test_encode_cursor_bytes():
    data = b"hello"
    result = encode_cursor(data)
    assert result is not None
    decoded = decode_cursor(result, to_str=False)
    assert decoded == data


def test_encode_cursor_not_quoted():
    result = encode_cursor("hello", quoted=False)
    assert result is not None
    decoded = decode_cursor(result, quoted=False)
    assert decoded == "hello"


def test_encode_cursor_custom_encoder():
    called_with = []

    def custom_encoder(data: bytes) -> str:
        called_with.append(data)
        return b64encode(data).decode()

    encode_cursor("test", encoder=custom_encoder)
    assert len(called_with) == 1
    assert called_with[0] == b"test"


def test_encode_cursor_quoted_by_default():
    result = encode_cursor("hello")
    assert result is not None
    # quote() is idempotent on already-quoted strings for simple values
    decoded = decode_cursor(result, quoted=True)
    assert decoded == "hello"


# --- CursorParams ---

def test_cursor_params_to_raw_params_no_cursor():
    params = CursorParams()
    raw = params.to_raw_params()
    assert raw.cursor is None
    assert raw.size == 50


def test_cursor_params_to_raw_params_with_cursor():
    cursor_val = "my-cursor"
    encoded = encode_cursor(cursor_val)
    params = CursorParams(cursor=encoded)
    raw = params.to_raw_params()
    assert raw.cursor == cursor_val


def test_cursor_params_encode_cursor_none():
    params = CursorParams()
    assert params.encode_cursor(None) is None


def test_cursor_params_encode_cursor_value():
    params = CursorParams()
    result = params.encode_cursor("abc")
    assert result is not None
    assert params.decode_cursor(result) == "abc"


def test_cursor_params_decode_cursor_none():
    params = CursorParams()
    assert params.decode_cursor(None) is None


def test_cursor_params_decode_cursor_value():
    params = CursorParams()
    encoded = params.encode_cursor("xyz")
    assert params.decode_cursor(encoded) == "xyz"


# --- CursorPage ---

def test_cursor_page_create_wrong_params_type():
    class FakeParams:
        pass

    with pytest.raises(TypeError, match="CursorPage should be used with CursorParams"):
        CursorPage.create(items=[], params=FakeParams())


def test_cursor_page_create_basic():
    params = CursorParams()
    page = CursorPage.create(items=["a", "b"], params=params, total=2)
    assert page.items == ["a", "b"]
    assert page.current_page is None
    assert page.next_page is None
    assert page.previous_page is None


def test_cursor_page_create_with_cursors():
    params = CursorParams()
    page = CursorPage.create(
        items=["x"],
        params=params,
        total=1,
        current="cur1",
        next_="nxt1",
        previous="prv1",
        current_backwards="cur_back",
    )
    assert page.current_page == params.encode_cursor("cur1")
    assert page.next_page == params.encode_cursor("nxt1")
    assert page.previous_page == params.encode_cursor("prv1")
    assert page.current_page_backwards == params.encode_cursor("cur_back")
