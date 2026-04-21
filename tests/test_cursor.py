from __future__ import annotations

from base64 import b64encode
from urllib.parse import quote

import pytest
from fastapi import HTTPException

from fastapi_pagination.bases import CursorRawParams
from fastapi_pagination.cursor import (
    CursorPage,
    CursorParams,
    decode_cursor,
    default_encoder,
    encode_cursor,
)


def test_decode_cursor_none_returns_none():
    result = decode_cursor(None)
    assert result is None


def test_decode_cursor_valid_str_unquoted():
    original = "hello"
    encoded = b64encode(original.encode()).decode()
    result = decode_cursor(encoded, quoted=False)
    assert result == original


def test_decode_cursor_valid_str_quoted():
    original = "hello"
    encoded = b64encode(original.encode()).decode()
    quoted_encoded = quote(encoded)
    result = decode_cursor(quoted_encoded, quoted=True)
    assert result == original


def test_decode_cursor_to_bytes():
    original = b"hello"
    encoded = b64encode(original).decode()
    result = decode_cursor(encoded, to_str=False, quoted=False)
    assert result == original


def test_decode_cursor_invalid_raises_http_exception():
    # b'\xff\xfe' is not valid UTF-8, so decoding as str raises UnicodeDecodeError
    invalid_utf8 = b"\xff\xfe"
    encoded = b64encode(invalid_utf8).decode()
    with pytest.raises(HTTPException) as exc_info:
        decode_cursor(encoded, to_str=True, quoted=False)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid cursor value"


def test_default_encoder_returns_base64_string():
    data = b"hello world"
    result = default_encoder(data)
    assert result == b64encode(data).decode()


def test_encode_cursor_none_returns_none():
    result = encode_cursor(None)
    assert result is None


def test_encode_cursor_str_quoted():
    cursor = "my_cursor"
    result = encode_cursor(cursor, quoted=True)
    encoded = b64encode(cursor.encode()).decode()
    expected = quote(encoded)
    assert result == expected


def test_encode_cursor_bytes_quoted():
    cursor = b"my_cursor"
    result = encode_cursor(cursor, quoted=True)
    encoded = b64encode(cursor).decode()
    expected = quote(encoded)
    assert result == expected


def test_encode_cursor_not_quoted():
    cursor = "my_cursor"
    result = encode_cursor(cursor, quoted=False)
    expected = b64encode(cursor.encode()).decode()
    assert result == expected


def test_encode_cursor_custom_encoder():
    cursor = b"test"
    custom_encoder = lambda data: "custom_" + data.decode()
    result = encode_cursor(cursor, quoted=False, encoder=custom_encoder)
    assert result == "custom_test"


def test_cursor_params_to_raw_params_no_cursor():
    params = CursorParams(cursor=None, size=10)
    raw = params.to_raw_params()
    assert isinstance(raw, CursorRawParams)
    assert raw.cursor is None
    assert raw.size == 10


def test_cursor_params_to_raw_params_with_cursor():
    original = "some_cursor"
    encoded = b64encode(original.encode()).decode()
    quoted_encoded = quote(encoded)
    params = CursorParams(cursor=quoted_encoded, size=20)
    raw = params.to_raw_params()
    assert raw.cursor == original
    assert raw.size == 20


def test_cursor_params_encode_cursor_none():
    params = CursorParams(cursor=None, size=10)
    result = params.encode_cursor(None)
    assert result is None


def test_cursor_params_encode_cursor_value():
    params = CursorParams(cursor=None, size=10)
    cursor = "test_cursor"
    result = params.encode_cursor(cursor)
    expected = encode_cursor(cursor, quoted=params.quoted_cursor)
    assert result == expected


def test_cursor_params_decode_cursor_none():
    params = CursorParams(cursor=None, size=10)
    result = params.decode_cursor(None)
    assert result is None


def test_cursor_params_decode_cursor_value():
    params = CursorParams(cursor=None, size=10)
    original = "cursor_value"
    encoded = b64encode(original.encode()).decode()
    quoted_encoded = quote(encoded)
    result = params.decode_cursor(quoted_encoded)
    assert result == original


def test_cursor_page_create_wrong_params_raises_type_error():
    from fastapi_pagination.bases import AbstractParams, RawParams

    class FakeParams(AbstractParams):
        def to_raw_params(self):
            return RawParams(limit=10, offset=0)

    with pytest.raises(TypeError, match="CursorPage should be used with CursorParams"):
        CursorPage.create(items=[], params=FakeParams())


def test_cursor_page_create_no_cursors():
    params = CursorParams(cursor=None, size=10)
    page = CursorPage.create(items=[], params=params, total=0)
    assert list(page.items) == []
    assert page.current_page is None
    assert page.next_page is None
    assert page.previous_page is None
    assert page.current_page_backwards is None


def test_cursor_page_create_with_cursors():
    params = CursorParams(cursor=None, size=10)
    items = ["a", "b", "c"]
    page = CursorPage.create(
        items=items,
        params=params,
        total=3,
        current="cur_current",
        next_="cur_next",
        previous="cur_prev",
        current_backwards="cur_back",
    )
    assert list(page.items) == items
    assert page.current_page is not None
    assert page.next_page is not None
    assert page.previous_page is not None
    assert page.current_page_backwards is not None
