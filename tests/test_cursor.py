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


def test_decode_cursor_none():
    assert decode_cursor(None) is None


def test_decode_cursor_returns_string():
    import base64

    encoded = base64.b64encode(b"my_cursor_value").decode()
    from urllib.parse import quote

    quoted = quote(encoded)
    result = decode_cursor(quoted)
    assert result == "my_cursor_value"


def test_decode_cursor_not_quoted():
    import base64

    encoded = base64.b64encode(b"hello").decode()
    result = decode_cursor(encoded, quoted=False)
    assert result == "hello"


def test_decode_cursor_to_bytes():
    import base64
    from urllib.parse import quote

    encoded = base64.b64encode(b"raw_bytes").decode()
    quoted = quote(encoded)
    result = decode_cursor(quoted, to_str=False)
    assert result == b"raw_bytes"


def test_decode_cursor_invalid_raises_http_exception():
    with pytest.raises(HTTPException) as exc_info:
        decode_cursor("!!!invalid_base64!!!", quoted=False)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid cursor value"


def test_decode_cursor_empty_string_returns_none():
    assert decode_cursor("") is None


def test_default_encoder():
    import base64

    data = b"test_data"
    result = default_encoder(data)
    assert result == base64.b64encode(data).decode()


def test_encode_cursor_none():
    assert encode_cursor(None) is None


def test_encode_cursor_string_quoted():
    import base64
    from urllib.parse import quote

    result = encode_cursor("my_cursor")
    expected = quote(base64.b64encode(b"my_cursor").decode())
    assert result == expected


def test_encode_cursor_string_not_quoted():
    import base64

    result = encode_cursor("my_cursor", quoted=False)
    expected = base64.b64encode(b"my_cursor").decode()
    assert result == expected


def test_encode_cursor_bytes():
    import base64
    from urllib.parse import quote

    result = encode_cursor(b"my_bytes")
    expected = quote(base64.b64encode(b"my_bytes").decode())
    assert result == expected


def test_encode_cursor_custom_encoder():
    result = encode_cursor("hello", quoted=False, encoder=lambda b: "custom_" + b.decode())
    assert result == "custom_hello"


def test_encode_decode_roundtrip():
    original = "some_cursor_value"
    encoded = encode_cursor(original)
    decoded = decode_cursor(encoded)
    assert decoded == original


def test_cursor_params_to_raw_params_none_cursor():
    params = CursorParams()
    raw = params.to_raw_params()
    assert raw.cursor is None
    assert raw.size == 50


def test_cursor_params_to_raw_params_with_cursor():
    import base64
    from urllib.parse import quote

    encoded = quote(base64.b64encode(b"page2").decode())
    params = CursorParams(cursor=encoded)
    raw = params.to_raw_params()
    assert raw.cursor == "page2"
    assert raw.size == 50


def test_cursor_params_encode_cursor_none():
    params = CursorParams()
    assert params.encode_cursor(None) is None


def test_cursor_params_encode_cursor_value():
    import base64
    from urllib.parse import quote

    params = CursorParams()
    result = params.encode_cursor("page3")
    expected = quote(base64.b64encode(b"page3").decode())
    assert result == expected


def test_cursor_params_decode_cursor_none():
    params = CursorParams()
    assert params.decode_cursor(None) is None


def test_cursor_params_decode_cursor_value():
    import base64
    from urllib.parse import quote

    params = CursorParams()
    encoded = quote(base64.b64encode(b"page4").decode())
    result = params.decode_cursor(encoded)
    assert result == "page4"


def test_cursor_page_create_raises_type_error_for_non_cursor_params():
    from fastapi_pagination.default import Params

    params = Params()
    with pytest.raises(TypeError, match="CursorPage should be used with CursorParams"):
        CursorPage.create(items=[], params=params, total=0)


def test_cursor_page_create_success():
    params = CursorParams()
    page = CursorPage.create(items=[1, 2, 3], params=params, next_="cursor_next", total=3)
    assert page.items == [1, 2, 3]
    assert page.next_page is not None
    assert page.current_page is None
    assert page.previous_page is None


def test_cursor_page_create_with_all_cursors():
    params = CursorParams()
    page = CursorPage.create(
        items=["a", "b"],
        params=params,
        current="cur",
        current_backwards="cur_back",
        next_="nxt",
        previous="prev",
        total=2,
    )
    assert page.current_page is not None
    assert page.current_page_backwards is not None
    assert page.next_page is not None
    assert page.previous_page is not None
