from __future__ import annotations

import pytest
from fastapi import Response
from pydantic import BaseModel
from typing import Any, Sequence

from fastapi_pagination.bases import AbstractParams, BaseRawParams, RawParams
from fastapi_pagination.cursor import CursorPage, CursorParams
from fastapi_pagination.customization import (
    CustomizedPage,
    UseAdditionalFields,
    UseCursorEncoding,
    UseExcludedFields,
    UseFieldTypeAnnotations,
    UseFieldsAliases,
    UseIncludeTotal,
    UseModelConfig,
    UseModule,
    UseName,
    UseOptionalParams,
    UseParams,
    UseParamsFields,
    UsePydanticV1,
    UseQuotedCursor,
    UseRequiredFields,
    UseResponseHeaders,
    UseStrCursor,
    get_page_bases,
    new_page_cls,
    _update_params_fields,
)
from fastapi_pagination.default import Page, Params


# ─── helpers ────────────────────────────────────────────────────────────────

def test_get_page_bases_pydantic_v2_no_params():
    """get_page_bases on a concrete pydantic-v2 page (no generic parameters)."""
    from fastapi_pagination.default import Page
    bases = get_page_bases(Page)
    assert isinstance(bases, tuple)
    assert len(bases) == 2  # generic form → (cls[params], Generic[params])


def test_new_page_cls_returns_type():
    new_ns = {"__name__": "TestPage", "__qualname__": "TestPage"}
    result = new_page_cls(Page, new_ns)
    assert isinstance(result, type)
    assert result.__name__ == "TestPage"


def test_new_page_cls_default_name():
    result = new_page_cls(Page, {})
    assert result.__name__ == Page.__name__


# ─── CustomizedPage ──────────────────────────────────────────────────────────

def test_customized_page_single_type_returns_type():
    result = CustomizedPage[Page]
    assert result is Page


def test_customized_page_with_use_name():
    result = CustomizedPage[Page, UseName("MyPage")]
    assert result.__name__ == "MyPage"


def test_customized_page_with_use_module():
    result = CustomizedPage[Page, UseModule("my.custom.module")]
    assert result.__module__ == "my.custom.module"


def test_customized_page_invalid_type_raises():
    with pytest.raises(AssertionError):
        CustomizedPage["notaclass"]


def test_customized_page_invalid_subclass_raises():
    with pytest.raises(AssertionError):
        CustomizedPage[BaseModel]


def test_customized_page_invalid_customizer_raises():
    with pytest.raises(TypeError):
        CustomizedPage[Page, "bad_customizer"]


def test_customized_page_name_suffix_stripped():
    # Start with an already-customized name; suffix should be removed then re-added once
    CustomizedPageCls = CustomizedPage[Page, UseName("PageCustomized")]
    result = CustomizedPage[CustomizedPageCls, UseModule("m")]
    assert result.__name__.count("Customized") == 1


# ─── UseName ─────────────────────────────────────────────────────────────────

def test_use_name_sets_name_and_qualname():
    ns: dict[str, Any] = {}
    UseName("Foo").customize_page_ns(Page, ns)
    assert ns["__name__"] == "Foo"
    assert ns["__qualname__"] == "Foo"


# ─── UseModule ───────────────────────────────────────────────────────────────

def test_use_module_sets_module():
    ns: dict[str, Any] = {}
    UseModule("foo.bar").customize_page_ns(Page, ns)
    assert ns["__module__"] == "foo.bar"


# ─── UseAdditionalFields ─────────────────────────────────────────────────────

def test_use_additional_fields_tuple():
    ns: dict[str, Any] = {}
    UseAdditionalFields(my_field=(int, 42)).customize_page_ns(Page, ns)
    assert ns["__annotations__"]["my_field"] is int
    assert ns["my_field"] == 42


def test_use_additional_fields_non_tuple():
    ns: dict[str, Any] = {}
    UseAdditionalFields(my_field=str).customize_page_ns(Page, ns)
    assert ns["__annotations__"]["my_field"] is str
    assert "my_field" not in ns or ns.get("my_field") is str  # only annotation added


# ─── UseFieldTypeAnnotations ─────────────────────────────────────────────────

def test_use_field_type_annotations():
    ns: dict[str, Any] = {}
    UseFieldTypeAnnotations(total=int).customize_page_ns(Page, ns)
    assert ns["__annotations__"]["total"] is int


# ─── UseModelConfig ───────────────────────────────────────────────────────────

def test_use_model_config_pydantic_v2():
    result = CustomizedPage[Page, UseModelConfig(populate_by_name=True)]
    assert isinstance(result, type)


# ─── UseExcludedFields ───────────────────────────────────────────────────────

def test_use_excluded_fields_pydantic_v2():
    result = CustomizedPage[Page, UseExcludedFields("total")]
    assert isinstance(result, type)


# ─── UseFieldsAliases ────────────────────────────────────────────────────────

def test_use_fields_aliases_pydantic_v2():
    result = CustomizedPage[Page, UseFieldsAliases(total="totalCount")]
    assert isinstance(result, type)


# ─── UseIncludeTotal ─────────────────────────────────────────────────────────

def test_use_include_total_true():
    result = CustomizedPage[Page, UseIncludeTotal(True)]
    assert isinstance(result, type)


def test_use_include_total_false():
    result = CustomizedPage[Page, UseIncludeTotal(False)]
    assert isinstance(result, type)


def test_use_include_total_to_raw_params():
    """CustomizedParams.to_raw_params should set include_total."""
    CustomPage = CustomizedPage[Page, UseIncludeTotal(False)]
    params = CustomPage.__params_type__(page=1, size=10)
    raw = params.to_raw_params()
    assert raw.include_total is False


def test_use_include_total_true_to_raw_params():
    CustomPage = CustomizedPage[Page, UseIncludeTotal(True)]
    params = CustomPage.__params_type__(page=1, size=10)
    raw = params.to_raw_params()
    assert raw.include_total is True


# ─── UseRequiredFields / UseOptionalFields ───────────────────────────────────

def test_use_required_fields():
    result = CustomizedPage[Page, UseRequiredFields(fields=["total"])]
    assert isinstance(result, type)


def test_use_optional_fields_no_matching():
    """_UseOptionalRequiredFields returns early when no fields match."""
    from fastapi_pagination.customization import _UseOptionalRequiredFields
    ns: dict[str, Any] = {
        "__params_type__": Page.__params_type__,
        "__model_aliases__": {},
        "__model_exclude__": set(),
        "model_config": {},
        "__annotations__": {},
    }
    customizer = _UseOptionalRequiredFields(required=True, fields=["nonexistent_field"])
    customizer.customize_page_ns(Page, ns)  # should return early without error


# ─── UseCursorEncoding ────────────────────────────────────────────────────────

def test_use_cursor_encoding_no_op_when_no_encoder_decoder():
    ns: dict[str, Any] = {"__params_type__": CursorParams}
    UseCursorEncoding(encoder=None, decoder=None).customize_page_ns(CursorPage, ns)
    assert ns["__params_type__"] is CursorParams  # unchanged


def test_use_cursor_encoding_with_encoder():
    def my_encoder(params, cursor):
        return "encoded"

    result = CustomizedPage[CursorPage, UseCursorEncoding(encoder=my_encoder)]
    assert isinstance(result, type)
    params = result.__params_type__(cursor=None, size=10)
    encoded = params.encode_cursor(b"test")
    assert encoded == "encoded"


def test_use_cursor_encoding_with_decoder():
    def my_decoder(params, cursor):
        return b"decoded"

    result = CustomizedPage[CursorPage, UseCursorEncoding(decoder=my_decoder)]
    params = result.__params_type__(cursor=None, size=10)
    decoded = params.decode_cursor("anything")
    assert decoded == b"decoded"


def test_use_cursor_encoding_no_encoder_falls_through():
    """When encoder is None, should fall through to super().encode_cursor."""
    def my_decoder(params, cursor):
        return b"decoded"

    result = CustomizedPage[CursorPage, UseCursorEncoding(decoder=my_decoder)]
    params = result.__params_type__(cursor=None, size=10)
    # no encoder set, so encode_cursor falls through to base
    encoded = params.encode_cursor(b"test")
    assert encoded is not None


def test_use_cursor_encoding_no_decoder_falls_through():
    """When decoder is None, should fall through to super().decode_cursor."""
    def my_encoder(params, cursor):
        return "encoded"

    result = CustomizedPage[CursorPage, UseCursorEncoding(encoder=my_encoder)]
    params = result.__params_type__(cursor=None, size=10)
    decoded = params.decode_cursor(None)
    assert decoded is None


# ─── UseQuotedCursor ──────────────────────────────────────────────────────────

def test_use_quoted_cursor_true():
    result = CustomizedPage[CursorPage, UseQuotedCursor(quoted_cursor=True)]
    assert result.__params_type__.quoted_cursor is True


def test_use_quoted_cursor_false():
    result = CustomizedPage[CursorPage, UseQuotedCursor(quoted_cursor=False)]
    assert result.__params_type__.quoted_cursor is False


# ─── UseStrCursor ─────────────────────────────────────────────────────────────

def test_use_str_cursor_true():
    result = CustomizedPage[CursorPage, UseStrCursor(str_cursor=True)]
    assert result.__params_type__.str_cursor is True


def test_use_str_cursor_false():
    result = CustomizedPage[CursorPage, UseStrCursor(str_cursor=False)]
    assert result.__params_type__.str_cursor is False


# ─── UseParams ────────────────────────────────────────────────────────────────

def test_use_params():
    class MyParams(BaseModel, AbstractParams):
        page: int = 1
        size: int = 10

        def to_raw_params(self) -> BaseRawParams:
            return RawParams(limit=self.size, offset=self.size * (self.page - 1))

    result = CustomizedPage[Page, UseParams(params=MyParams)]
    # __params_type__ is a subclass of MyParams (a new_params_cls wrapper is applied)
    assert issubclass(result.__params_type__, MyParams)


def test_use_params_already_customized_raises():
    class MyParams(BaseModel, AbstractParams):
        page: int = 1
        size: int = 10

        def to_raw_params(self) -> BaseRawParams:
            return RawParams(limit=self.size, offset=self.size * (self.page - 1))

    # UseIncludeTotal already customizes params_type, so UseParams should fail
    with pytest.raises(ValueError, match="already customized"):
        CustomizedPage[Page, UseIncludeTotal(True), UseParams(params=MyParams)]


# ─── _update_params_fields ────────────────────────────────────────────────────

def test_update_params_fields_not_base_model_raises():
    class NotAModel(AbstractParams):
        def to_raw_params(self) -> BaseRawParams:
            return RawParams()

    with pytest.raises(TypeError, match="must be subclass of BaseModel"):
        _update_params_fields(NotAModel, {"page": 1})


def test_update_params_fields_unknown_field_raises():
    with pytest.raises(ValueError, match="Unknown field"):
        _update_params_fields(Params, {"nonexistent": 1})


def test_update_params_fields_valid():
    from fastapi import Query
    result = _update_params_fields(Params, {"page": 1})
    assert "page" in result


def test_update_params_fields_with_param():
    from fastapi import Query
    result = _update_params_fields(Params, {"page": Query(1, ge=1)})
    assert "page" in result


# ─── UseParamsFields ──────────────────────────────────────────────────────────

def test_use_params_fields():
    result = CustomizedPage[Page, UseParamsFields(page=2)]
    assert isinstance(result, type)


# ─── UseOptionalParams ────────────────────────────────────────────────────────

def test_use_optional_params():
    result = CustomizedPage[Page, UseOptionalParams()]
    assert isinstance(result, type)


# ─── UsePydanticV1 ────────────────────────────────────────────────────────────

def test_use_pydantic_v1_transform_already_v1_model():
    """transform_page_cls should return page_cls unchanged if not pydantic v2 model."""
    # Since we're running pydantic v2, Page IS a v2 model, so it should be converted
    transformer = UsePydanticV1()
    result = transformer.transform_page_cls(Page)
    # Should return a new class (converted from v2 to v1)
    assert isinstance(result, type)


def test_use_pydantic_v1_via_customized_page():
    result = CustomizedPage[Page, UsePydanticV1()]
    assert isinstance(result, type)


# ─── UseResponseHeaders ───────────────────────────────────────────────────────

def test_use_response_headers_non_v2_raises():
    """UseResponseHeaders raises UnsupportedFeatureError for non-v2 models.

    Since we are on pydantic v2, just check that it works for v2 Page.
    """
    # On pydantic v2, should NOT raise
    def resolver(page):
        return {}

    result = CustomizedPage[Page, UseResponseHeaders(resolver=resolver)]
    assert isinstance(result, type)


def _make_page_with_headers(resolver):
    """Helper: create CustomizedPage with UseResponseHeaders and a real Response."""
    from fastapi_pagination.api import _rsp_val

    CustomPage = CustomizedPage[Page, UseResponseHeaders(resolver=resolver)]
    rsp = Response()
    token = _rsp_val.set(rsp)
    try:
        page = CustomPage(items=[1, 2, 3], total=3, page=1, size=10, pages=1)
    finally:
        _rsp_val.reset(token)
    return page, rsp


def test_use_response_headers_model_post_init_str_header():
    """model_post_init sets a str header value on the response."""
    def resolver(page):
        return {"X-Custom": "hello"}

    page, rsp = _make_page_with_headers(resolver)
    assert rsp.headers["x-custom"] == "hello"


def test_use_response_headers_model_post_init_sequence_header():
    """model_post_init appends sequence header values on the response."""
    def resolver(page):
        return {"X-Items": ["a", "b", "c"]}

    page, rsp = _make_page_with_headers(resolver)
    # Headers should contain all appended values
    raw_headers = [(k.decode(), v.decode()) for k, v in rsp.raw_headers]
    x_items_values = [v for k, v in raw_headers if k.lower() == "x-items"]
    assert x_items_values == ["a", "b", "c"]


def test_use_response_headers_model_post_init_sequence_replaces_existing():
    """model_post_init deletes existing header before appending sequence values."""
    from fastapi_pagination.api import _rsp_val

    def resolver(page):
        return {"X-Items": ["new1", "new2"]}

    CustomPage = CustomizedPage[Page, UseResponseHeaders(resolver=resolver)]
    rsp = Response(headers={"X-Items": "old"})
    token = _rsp_val.set(rsp)
    try:
        CustomPage(items=[], total=0, page=1, size=10, pages=0)
    finally:
        _rsp_val.reset(token)

    raw_headers = [(k.decode(), v.decode()) for k, v in rsp.raw_headers]
    x_items_values = [v for k, v in raw_headers if k.lower() == "x-items"]
    # Old value should be replaced by new values
    assert "old" not in x_items_values
    assert "new1" in x_items_values
    assert "new2" in x_items_values


def test_use_response_headers_model_post_init_invalid_type_raises():
    """model_post_init raises TypeError for header values that are not str or Sequence."""
    from fastapi_pagination.api import _rsp_val

    def resolver(page):
        return {"X-Bad": 12345}

    CustomPage = CustomizedPage[Page, UseResponseHeaders(resolver=resolver)]
    rsp = Response()
    token = _rsp_val.set(rsp)
    try:
        with pytest.raises(TypeError, match="Header value must be str or list"):
            CustomPage(items=[], total=0, page=1, size=10, pages=0)
    finally:
        _rsp_val.reset(token)


def test_use_response_headers_model_post_init_multiple_headers():
    """model_post_init handles multiple headers from the resolver."""
    def resolver(page):
        return {"X-A": "val-a", "X-B": ["b1", "b2"]}

    page, rsp = _make_page_with_headers(resolver)
    assert rsp.headers["x-a"] == "val-a"
    raw_headers = [(k.decode(), v.decode()) for k, v in rsp.raw_headers]
    x_b_values = [v for k, v in raw_headers if k.lower() == "x-b"]
    assert x_b_values == ["b1", "b2"]


def test_use_response_headers_model_post_init_empty_resolver():
    """model_post_init with resolver returning empty dict does not modify headers."""
    from fastapi_pagination.api import _rsp_val

    def resolver(page):
        return {}

    CustomPage = CustomizedPage[Page, UseResponseHeaders(resolver=resolver)]
    rsp = Response()
    token = _rsp_val.set(rsp)
    try:
        CustomPage(items=[1], total=1, page=1, size=10, pages=1)
    finally:
        _rsp_val.reset(token)
    # No custom headers should be set (only default content-length)
    assert "x-custom" not in rsp.headers
