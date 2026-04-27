from __future__ import annotations

import pytest
from pydantic import BaseModel

from fastapi_pagination.bases import AbstractParams, BaseAbstractPage
from fastapi_pagination.cursor import CursorPage, CursorParams
from fastapi_pagination.customization import (
    ClsNamespace,
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
    UseOptionalFields,
    UseOptionalParams,
    UseParams,
    UseParamsFields,
    UsePydanticV1,
    UseQuotedCursor,
    UseRequiredFields,
    UseResponseHeaders,
    UseStrCursor,
    _convert_v2_field_to_v1,
    _convert_v2_page_cls_to_v1,
    _update_params_fields,
    get_page_bases,
    new_page_cls,
    new_params_cls,
)
from fastapi_pagination.default import Page, Params
from fastapi_pagination.limit_offset import LimitOffsetPage, LimitOffsetParams


# ---------------------------------------------------------------------------
# get_page_bases
# ---------------------------------------------------------------------------


def test_get_page_bases_non_concrete():
    bases = get_page_bases(Page)
    assert len(bases) == 2
    # second base should be a Generic
    import typing
    assert hasattr(bases[1], "__origin__") or str(bases[1]).startswith("typing.Generic")


def test_get_page_bases_pydantic_v2_with_params():
    bases = get_page_bases(Page)
    assert Page in bases or Page.__class__.__name__ in [b.__name__ for b in bases if isinstance(b, type)]


def test_get_page_bases_returns_tuple():
    bases = get_page_bases(Page)
    assert isinstance(bases, tuple)
    assert len(bases) > 0


# ---------------------------------------------------------------------------
# new_page_cls
# ---------------------------------------------------------------------------


def test_new_page_cls_returns_correct_type():
    new_cls = new_page_cls(Page, {"__name__": "MyPage", "__qualname__": "MyPage"})
    assert new_cls.__name__ == "MyPage"


def test_new_page_cls_without_name_uses_original():
    new_cls = new_page_cls(Page, {})
    assert new_cls.__name__ == Page.__name__


def test_new_page_cls_is_subclass_related():
    new_cls = new_page_cls(Page, {"__name__": "DerivedPage", "__qualname__": "DerivedPage"})
    assert isinstance(new_cls, type)


# ---------------------------------------------------------------------------
# new_params_cls
# ---------------------------------------------------------------------------


def test_new_params_cls_returns_subclass():
    new_cls = new_params_cls(Params, {"__name__": "MyParams", "__qualname__": "MyParams"})
    assert new_cls.__name__ == "MyParams"
    assert issubclass(new_cls, Params)


def test_new_params_cls_without_name_uses_original():
    new_cls = new_params_cls(Params, {})
    assert new_cls.__name__ == Params.__name__


# ---------------------------------------------------------------------------
# CustomizedPage.__class_getitem__
# ---------------------------------------------------------------------------


def test_customized_page_single_item_returns_page_cls():
    result = CustomizedPage[Page]
    assert result is Page


def test_customized_page_with_name_customizer():
    result = CustomizedPage[Page, UseName("CustomPage")]
    assert result.__name__ == "CustomPage"


def test_customized_page_multiple_customizers():
    result = CustomizedPage[Page, UseName("MultiCustom"), UseModule("mymodule")]
    assert result.__name__ == "MultiCustom"
    assert result.__module__ == "mymodule"


def test_customized_page_non_type_raises():
    with pytest.raises(AssertionError, match="Expected type"):
        CustomizedPage["not_a_type"]


def test_customized_page_non_abstract_page_raises():
    class NotPage(BaseModel):
        pass

    with pytest.raises(AssertionError, match="Expected subclass of AbstractPage"):
        CustomizedPage[NotPage]


def test_customized_page_invalid_customizer_raises():
    with pytest.raises(TypeError, match="Expected PageCustomizer or PageTransformer"):
        CustomizedPage[Page, "invalid_customizer"]


def test_customized_page_removesuffix_customized():
    # first customization gives "PageCustomized"
    p1 = CustomizedPage[Page, UseName("FooCustomized")]
    # second level should strip the "Customized" suffix for cls_name
    p2 = CustomizedPage[p1, UseName("BarCustomized")]
    assert p2.__name__ == "BarCustomized"


def test_customized_page_with_use_pydantic_v1_transformer():
    result = CustomizedPage[Page, UsePydanticV1()]
    assert result is not Page
    assert isinstance(result, type)


# ---------------------------------------------------------------------------
# UseName
# ---------------------------------------------------------------------------


def test_use_name_customize_page_ns():
    ns: ClsNamespace = {}
    customizer = UseName("NewName")
    customizer.customize_page_ns(Page, ns)
    assert ns["__name__"] == "NewName"
    assert ns["__qualname__"] == "NewName"


# ---------------------------------------------------------------------------
# UseModule
# ---------------------------------------------------------------------------


def test_use_module_customize_page_ns():
    ns: ClsNamespace = {}
    customizer = UseModule("some.module")
    customizer.customize_page_ns(Page, ns)
    assert ns["__module__"] == "some.module"


# ---------------------------------------------------------------------------
# UseOptionalFields / UseRequiredFields (_UseOptionalRequiredFields)
# ---------------------------------------------------------------------------


def test_use_optional_fields_customize_page_ns():
    result = CustomizedPage[Page, UseOptionalFields()]
    assert result is not Page
    assert isinstance(result, type)


def test_use_required_fields_customize_page_ns():
    result = CustomizedPage[Page, UseRequiredFields()]
    assert result is not Page
    assert isinstance(result, type)


def test_use_optional_fields_no_matching_fields():
    # UseOptionalFields with fields that don't exist on Page - should be no-op
    from fastapi_pagination.customization import _UseOptionalRequiredFields

    ns: ClsNamespace = {
        "__params_type__": Page.__params_type__,
        "__model_aliases__": {},
        "__model_exclude__": set(),
        "model_config": {},
    }
    customizer = _UseOptionalRequiredFields(required=False, fields=["nonexistent_field"])
    customizer.customize_page_ns(Page, ns)
    # Should return without modifying annotations
    assert "__annotations__" not in ns


# ---------------------------------------------------------------------------
# UseIncludeTotal
# ---------------------------------------------------------------------------


def test_use_include_total_true():
    p = CustomizedPage[Page, UseIncludeTotal(True)]
    params = p.__params_type__()
    raw = params.to_raw_params()
    assert raw.include_total is True


def test_use_include_total_false():
    p = CustomizedPage[Page, UseIncludeTotal(False)]
    params = p.__params_type__()
    raw = params.to_raw_params()
    assert raw.include_total is False


def test_use_include_total_without_update_annotations():
    p = CustomizedPage[Page, UseIncludeTotal(True, update_annotations=False)]
    assert p is not Page


def test_use_include_total_to_raw_params_returns_base_raw_params():
    p = CustomizedPage[Page, UseIncludeTotal(True)]
    params = p.__params_type__()
    raw = params.to_raw_params()
    assert hasattr(raw, "include_total")


# ---------------------------------------------------------------------------
# UseCursorEncoding
# ---------------------------------------------------------------------------


def test_use_cursor_encoding_with_encoder_and_decoder():
    p = CustomizedPage[
        CursorPage,
        UseCursorEncoding(
            encoder=lambda params, cursor: "encoded" if cursor else None,
            decoder=lambda params, cursor: "decoded" if cursor else None,
        ),
    ]
    params = p.__params_type__()
    assert params.encode_cursor(b"hello") == "encoded"
    assert params.decode_cursor("anything") == "decoded"


def test_use_cursor_encoding_encoder_fallback_with_none_cursor():
    p = CustomizedPage[
        CursorPage,
        UseCursorEncoding(
            encoder=lambda params, cursor: "enc" if cursor else None,
        ),
    ]
    params = p.__params_type__()
    # encoder returns None for None cursor
    assert params.encode_cursor(None) is None


def test_use_cursor_encoding_decoder_fallback():
    p = CustomizedPage[
        CursorPage,
        UseCursorEncoding(
            decoder=lambda params, cursor: "dec",
        ),
    ]
    params = p.__params_type__()
    assert params.decode_cursor("anything") == "dec"


def test_use_cursor_encoding_no_encoder_no_decoder_is_noop():
    # Empty UseCursorEncoding should not change params type
    from fastapi_pagination.customization import UseCursorEncoding

    ns: ClsNamespace = {
        "__params_type__": CursorParams,
        "__model_aliases__": {},
        "__model_exclude__": set(),
        "model_config": {},
    }
    original_params = ns["__params_type__"]
    UseCursorEncoding().customize_page_ns(CursorPage, ns)
    assert ns["__params_type__"] is original_params


def test_use_cursor_encoding_encode_cursor_without_encoder_uses_super():
    p = CustomizedPage[
        CursorPage,
        UseCursorEncoding(
            encoder=None,
            decoder=lambda params, cursor: "decoded",
        ),
    ]
    params = p.__params_type__()
    # encode_cursor without encoder falls back to parent
    assert params.encode_cursor(None) is None


# ---------------------------------------------------------------------------
# UseQuotedCursor
# ---------------------------------------------------------------------------


def test_use_quoted_cursor_true():
    p = CustomizedPage[CursorPage, UseQuotedCursor(True)]
    assert p.__params_type__.quoted_cursor is True


def test_use_quoted_cursor_false():
    p = CustomizedPage[CursorPage, UseQuotedCursor(False)]
    assert p.__params_type__.quoted_cursor is False


# ---------------------------------------------------------------------------
# UseStrCursor
# ---------------------------------------------------------------------------


def test_use_str_cursor_true():
    p = CustomizedPage[CursorPage, UseStrCursor(True)]
    assert p.__params_type__.str_cursor is True


def test_use_str_cursor_false():
    p = CustomizedPage[CursorPage, UseStrCursor(False)]
    assert p.__params_type__.str_cursor is False


# ---------------------------------------------------------------------------
# UseParams
# ---------------------------------------------------------------------------


def test_use_params_sets_params_type():
    p = CustomizedPage[Page, UseParams(LimitOffsetParams)]
    assert issubclass(p.__params_type__, LimitOffsetParams)


def test_use_params_already_customized_raises():
    with pytest.raises(ValueError, match="Params type was already customized"):
        CustomizedPage[Page, UseParamsFields(page=1), UseParams(LimitOffsetParams)]


# ---------------------------------------------------------------------------
# _update_params_fields
# ---------------------------------------------------------------------------


def test_update_params_fields_basic():
    result = _update_params_fields(Params, {"page": 1})
    assert "page" in result
    # value is (annotation, wrapped_val)
    assert isinstance(result["page"], tuple)
    assert len(result["page"]) == 2


def test_update_params_fields_unknown_field_raises():
    with pytest.raises(ValueError, match="Unknown field invalid_field"):
        _update_params_fields(Params, {"invalid_field": 1})


def test_update_params_fields_multiple_unknown_fields_raises():
    with pytest.raises(ValueError, match="Unknown fields"):
        _update_params_fields(Params, {"a": 1, "b": 2})


def test_update_params_fields_non_basemodel_raises():
    class NotModel(AbstractParams):
        def to_raw_params(self):
            pass

    with pytest.raises(TypeError, match="must be subclass of BaseModel"):
        _update_params_fields(NotModel, {"page": 1})


def test_update_params_fields_class_var():
    result = _update_params_fields(CursorParams, {"str_cursor": True})
    assert "str_cursor" in result


# ---------------------------------------------------------------------------
# UseParamsFields
# ---------------------------------------------------------------------------


def test_use_params_fields_init():
    customizer = UseParamsFields(page=1, size=10)
    assert customizer.fields == {"page": 1, "size": 10}


def test_use_params_fields_customize_page_ns():
    p = CustomizedPage[Page, UseParamsFields(page=1)]
    params = p.__params_type__()
    assert params.page == 1


# ---------------------------------------------------------------------------
# UseOptionalParams
# ---------------------------------------------------------------------------


def test_use_optional_params_customize_page_ns():
    p = CustomizedPage[Page, UseOptionalParams()]
    params = p.__params_type__()
    assert params.page is None
    assert params.size is None


# ---------------------------------------------------------------------------
# UseModelConfig
# ---------------------------------------------------------------------------


def test_use_model_config_init():
    customizer = UseModelConfig(populate_by_name=True)
    assert customizer.config == {"populate_by_name": True}


def test_use_model_config_customize_page_ns_v2():
    p = CustomizedPage[Page, UseModelConfig(populate_by_name=True)]
    assert p is not Page


# ---------------------------------------------------------------------------
# UseExcludedFields
# ---------------------------------------------------------------------------


def test_use_excluded_fields_init():
    customizer = UseExcludedFields("page", "size")
    assert customizer.fields == ("page", "size")


def test_use_excluded_fields_customize_page_ns():
    p = CustomizedPage[Page, UseExcludedFields("page")]
    assert "page" in p.__model_exclude__


# ---------------------------------------------------------------------------
# UseFieldsAliases
# ---------------------------------------------------------------------------


def test_use_fields_aliases_init():
    customizer = UseFieldsAliases(page="p", size="s")
    assert customizer.aliases == {"page": "p", "size": "s"}


def test_use_fields_aliases_customize_page_ns():
    p = CustomizedPage[Page, UseFieldsAliases(page="p")]
    assert "page" in p.__model_aliases__
    assert p.__model_aliases__["page"] == "p"


# ---------------------------------------------------------------------------
# UseAdditionalFields
# ---------------------------------------------------------------------------


def test_use_additional_fields_init():
    customizer = UseAdditionalFields(custom=(str, "default"))
    assert "custom" in customizer.fields


def test_use_additional_fields_customize_page_ns_tuple():
    p = CustomizedPage[Page, UseAdditionalFields(custom_field=(str, "hello"))]
    assert isinstance(p, type)


def test_use_additional_fields_customize_page_ns_non_tuple():
    p = CustomizedPage[Page, UseAdditionalFields(custom_field=str)]
    assert isinstance(p, type)


# ---------------------------------------------------------------------------
# UseFieldTypeAnnotations
# ---------------------------------------------------------------------------


def test_use_field_type_annotations_init():
    customizer = UseFieldTypeAnnotations(page=int)
    assert customizer.anns == {"page": int}


def test_use_field_type_annotations_customize_page_ns():
    p = CustomizedPage[Page, UseFieldTypeAnnotations(page=int)]
    assert isinstance(p, type)


# ---------------------------------------------------------------------------
# UseResponseHeaders
# ---------------------------------------------------------------------------


def test_use_response_headers_customize_page_ns_adds_model_post_init():
    ns: ClsNamespace = {
        "__params_type__": Page.__params_type__,
        "__model_aliases__": {},
        "__model_exclude__": set(),
        "model_config": {},
    }
    customizer = UseResponseHeaders(resolver=lambda page: {"X-Total": "0"})
    customizer.customize_page_ns(Page, ns)
    assert "model_post_init" in ns
    assert callable(ns["model_post_init"])


def test_use_response_headers_model_post_init_str_header():
    from fastapi import Response
    from fastapi_pagination.api import _rsp_val

    rsp = Response()
    token = _rsp_val.set(rsp)
    try:
        p = CustomizedPage[Page, UseResponseHeaders(resolver=lambda _page: {"X-Custom": "hello"})]
        instance = p.create(items=[], params=p.__params_type__(), total=0)
        assert rsp.headers["X-Custom"] == "hello"
    finally:
        _rsp_val.reset(token)


def test_use_response_headers_model_post_init_sequence_header():
    from fastapi import Response
    from fastapi_pagination.api import _rsp_val

    rsp = Response()
    token = _rsp_val.set(rsp)
    try:
        p = CustomizedPage[
            Page,
            UseResponseHeaders(resolver=lambda _page: {"X-Items": ["val1", "val2"]}),
            UseName("PageWithSeqHeaders"),
        ]
        p.create(items=[], params=p.__params_type__(), total=0)
        header_values = rsp.headers.getlist("X-Items")
        assert "val1" in header_values
        assert "val2" in header_values
    finally:
        _rsp_val.reset(token)


def test_use_response_headers_model_post_init_sequence_existing_header_deleted():
    from fastapi import Response
    from fastapi_pagination.api import _rsp_val

    rsp = Response()
    rsp.headers["X-Replace"] = "old"
    token = _rsp_val.set(rsp)
    try:
        p = CustomizedPage[
            Page,
            UseResponseHeaders(resolver=lambda _page: {"X-Replace": ["new1", "new2"]}),
            UseName("PageWithReplaceHeaders"),
        ]
        p.create(items=[], params=p.__params_type__(), total=0)
        header_values = rsp.headers.getlist("X-Replace")
        assert "old" not in header_values
        assert "new1" in header_values
        assert "new2" in header_values
    finally:
        _rsp_val.reset(token)


def test_use_response_headers_model_post_init_invalid_type_raises():
    from fastapi import Response
    from fastapi_pagination.api import _rsp_val

    rsp = Response()
    token = _rsp_val.set(rsp)
    try:
        p = CustomizedPage[
            Page,
            UseResponseHeaders(resolver=lambda _page: {"X-Bad": 123}),
            UseName("PageWithBadHeaders"),
        ]
        with pytest.raises(TypeError, match="Header value must be str or list"):
            p.create(items=[], params=p.__params_type__(), total=0)
    finally:
        _rsp_val.reset(token)


# ---------------------------------------------------------------------------
# _convert_v2_field_to_v1
# ---------------------------------------------------------------------------


def test_convert_v2_field_to_v1_basic():
    field = Page.model_fields["total"]
    tp, field_info = _convert_v2_field_to_v1(field)
    assert tp is not None


def test_convert_v2_field_to_v1_with_default():
    field = Page.model_fields["total"]
    tp, field_info = _convert_v2_field_to_v1(field)
    assert field_info is not None


def test_convert_v2_field_to_v1_annotated_field():
    # page field uses Annotated type (GreaterEqualOne)
    field = Page.model_fields["page"]
    tp, field_info = _convert_v2_field_to_v1(field)
    assert tp is not None


# ---------------------------------------------------------------------------
# _convert_v2_page_cls_to_v1
# ---------------------------------------------------------------------------


def test_convert_v2_page_cls_to_v1():
    result = _convert_v2_page_cls_to_v1(Page)
    assert result is not Page
    assert isinstance(result, type)


# ---------------------------------------------------------------------------
# UsePydanticV1
# ---------------------------------------------------------------------------


def test_use_pydantic_v1_transform_page_cls():
    transformer = UsePydanticV1()
    result = transformer.transform_page_cls(Page)
    assert result is not Page
    assert isinstance(result, type)


def test_use_pydantic_v1_via_customized_page():
    p = CustomizedPage[Page, UsePydanticV1()]
    assert p is not Page
    assert isinstance(p, type)
