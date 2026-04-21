from __future__ import annotations

import binascii
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
from fastapi_pagination.bases import AbstractParams


def _b64(value: str) -> str:
    return b64encode(value.encode()).decode()


def _b64_quoted(value: str) -> str:
    return quote(_b64(value))


# --- decode_cursor ---

def test_decode_cursor_returns_none_for_none():
    assert decode_cursor(None) is None


def test_decode_cursor_returns_string_for_valid_cursor():
    encoded = _b64_quoted("hello")
    result = decode_cursor(encoded)
    assert result == "hello"


def test_decode_cursor_returns_string_unquoted():
    encoded = _b64("hello")
    result = decode_cursor(encoded, quoted=False)
    assert result == "hello"


def test_decode_cursor_returns_bytes_when_to_str_false():
    encoded = _b64_quoted("hello")
    result = decode_cursor(encoded, to_str=False)
    assert result == b"hello"


def test_decode_cursor_raises_http_exception_on_invalid_base64():
    with pytest.raises(HTTPException) as exc_info:
        decode_cursor("not-valid-base64!!!", quoted=False)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid cursor value"


def test_decode_cursor_raises_http_exception_on_invalid_unicode():
    # bytes that are valid base64 but not valid UTF-8
    import base64
    invalid_utf8 = base64.b64encode(b"\xff\xfe").decode()
    with pytest.raises(HTTPException) as exc_info:
        decode_cursor(invalid_utf8, to_str=True, quoted=False)
    assert exc_info.value.status_code == 400


# --- default_encoder ---

def test_default_encoder_encodes_bytes_to_base64_string():
    result = default_encoder(b"hello")
    assert result == _b64("hello")


def test_default_encoder_returns_string():
    result = default_encoder(b"test")
    assert isinstance(result, str)


# --- encode_cursor ---

def test_encode_cursor_returns_none_for_none():
    assert encode_cursor(None) is None


def test_encode_cursor_encodes_str_cursor_quoted():
    result = encode_cursor("hello")
    assert result == _b64_quoted("hello")


def test_encode_cursor_encodes_str_cursor_unquoted():
    result = encode_cursor("hello", quoted=False)
    assert result == _b64("hello")


def test_encode_cursor_encodes_bytes_cursor():
    result = encode_cursor(b"hello", quoted=False)
    assert result == _b64("hello")


def test_encode_cursor_uses_custom_encoder():
    def my_encoder(data: bytes) -> str:
        return "custom:" + data.decode()

    result = encode_cursor("hello", quoted=False, encoder=my_encoder)
    assert result == "custom:hello"


def test_encode_cursor_quoted_applies_url_encoding():
    # '+' in base64 should be percent-encoded when quoted=True
    result = encode_cursor("hello", quoted=True)
    assert result is not None
    # result should be URL-safe (no unquoted '+' or '/')
    assert "+" not in result or "%2B" in result or result == quote(_b64("hello"))


# --- CursorParams ---

def test_cursor_params_to_raw_params_none_cursor():
    params = CursorParams(cursor=None, size=10)
    raw = params.to_raw_params()
    assert raw.cursor is None
    assert raw.size == 10


def test_cursor_params_to_raw_params_with_cursor():
    encoded = _b64_quoted("my-cursor")
    params = CursorParams(cursor=encoded, size=20)
    raw = params.to_raw_params()
    assert raw.cursor == "my-cursor"
    assert raw.size == 20


def test_cursor_params_encode_cursor_none():
    params = CursorParams()
    assert params.encode_cursor(None) is None


def test_cursor_params_encode_cursor_string():
    params = CursorParams()
    result = params.encode_cursor("my-cursor")
    assert result == _b64_quoted("my-cursor")


def test_cursor_params_decode_cursor_none():
    params = CursorParams()
    assert params.decode_cursor(None) is None


def test_cursor_params_decode_cursor_valid():
    params = CursorParams()
    encoded = _b64_quoted("my-cursor")
    result = params.decode_cursor(encoded)
    assert result == "my-cursor"


# --- CursorPage ---

def test_cursor_page_create_raises_type_error_for_non_cursor_params():
    class FakeParams(AbstractParams):
        def to_raw_params(self):
            from fastapi_pagination.bases import RawParams
            return RawParams()

    with pytest.raises(TypeError, match="CursorPage should be used with CursorParams"):
        CursorPage.create([], FakeParams())


def test_cursor_page_create_with_cursor_params():
    params = CursorParams(cursor=None, size=10)
    page = CursorPage[str].create(
        items=["a", "b", "c"],
        params=params,
        total=3,
        current="first",
        next_="second",
    )
    assert list(page.items) == ["a", "b", "c"]
    assert page.total == 3
    assert page.current_page is not None
    assert page.next_page is not None
    assert page.previous_page is None


def test_cursor_page_create_none_cursors():
    params = CursorParams(cursor=None, size=5)
    page = CursorPage[int].create(
        items=[1, 2],
        params=params,
        total=2,
    )
    assert page.current_page is None
    assert page.next_page is None
    assert page.previous_page is None
    assert page.current_page_backwards is None
