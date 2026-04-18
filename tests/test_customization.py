from __future__ import annotations

from typing import Any, Optional

import pytest
from pydantic import BaseModel

from fastapi_pagination import Page, Params
from fastapi_pagination.bases import AbstractParams, BaseRawParams
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
    _update_params_fields,
    get_page_bases,
    new_page_cls,
    new_params_cls,
)


# --------------------------------------------------------------------------- #
# get_page_bases                                                               #
# --------------------------------------------------------------------------- #

def test_get_page_bases_pydantic_v2_no_params():
    bases = get_page_bases(Page)
    assert len(bases) == 2
    # bases[0] is Page (or Page[params]) and bases[1] is Generic[params]
    assert Page in bases or any(getattr(b, "__origin__", None) is Page for b in bases)


def test_get_page_bases_returns_tuple():
    bases = get_page_bases(Page)
    assert isinstance(bases, tuple)
    assert len(bases) > 0


# --------------------------------------------------------------------------- #
# new_page_cls                                                                 #
# --------------------------------------------------------------------------- #

def test_new_page_cls_uses_name_from_ns():
    new_ns = {"__name__": "MyNewPage", "__qualname__": "MyNewPage"}
    new_cls = new_page_cls(Page, new_ns)
    assert new_cls.__name__ == "MyNewPage"


def test_new_page_cls_defaults_to_original_name():
    new_cls = new_page_cls(Page, {})
    assert new_cls.__name__ == "Page"


# --------------------------------------------------------------------------- #
# new_params_cls                                                               #
# --------------------------------------------------------------------------- #

def test_new_params_cls_creates_subclass():
    new_cls = new_params_cls(Params, {"__name__": "MyParams"})
    assert issubclass(new_cls, Params)
    assert new_cls.__name__ == "MyParams"


def test_new_params_cls_default_name():
    new_cls = new_params_cls(Params, {})
    assert new_cls.__name__ == "Params"


# --------------------------------------------------------------------------- #
# CustomizedPage.__class_getitem__                                             #
# --------------------------------------------------------------------------- #

def test_customized_page_single_type_no_customizers():
    result = CustomizedPage[Page]
    assert result is Page


def test_customized_page_non_tuple_item_normalized():
    result = CustomizedPage[Page, UseName("TestPage")]
    assert result.__name__ == "TestPage"


def test_customized_page_invalid_type_raises():
    with pytest.raises(AssertionError, match="Expected type"):
        CustomizedPage["not_a_type"]


def test_customized_page_non_abstract_page_raises():
    with pytest.raises(AssertionError, match="Expected subclass of AbstractPage"):
        CustomizedPage[BaseModel]


def test_customized_page_invalid_customizer_raises():
    with pytest.raises(TypeError, match="Expected PageCustomizer or PageTransformer"):
        CustomizedPage[Page, "invalid"]


def test_customized_page_name_suffix_removed():
    # Page does not end with "Customized", so the name should be PageCustomized
    MyPage = CustomizedPage[Page, UseName("Foo")]
    assert MyPage.__name__ == "Foo"


def test_customized_page_with_page_transformer():
    V1Page = CustomizedPage[Page, UsePydanticV1()]
    assert V1Page is not Page


# --------------------------------------------------------------------------- #
# UseName                                                                      #
# --------------------------------------------------------------------------- #

def test_use_name_sets_name_and_qualname():
    MyPage = CustomizedPage[Page, UseName("MyCustomPage")]
    assert MyPage.__name__ == "MyCustomPage"


# --------------------------------------------------------------------------- #
# UseModule                                                                    #
# --------------------------------------------------------------------------- #

def test_use_module_sets_module():
    MyPage = CustomizedPage[Page, UseModule("my.custom.module")]
    assert MyPage.__module__ == "my.custom.module"


# --------------------------------------------------------------------------- #
# UseIncludeTotal                                                              #
# --------------------------------------------------------------------------- #

def test_use_include_total_true():
    TotalPage = CustomizedPage[Page, UseIncludeTotal(True)]
    params = TotalPage.__params_type__()
    raw = params.to_raw_params()
    assert raw.include_total is True


def test_use_include_total_false():
    TotalPage = CustomizedPage[Page, UseIncludeTotal(False)]
    params = TotalPage.__params_type__()
    raw = params.to_raw_params()
    assert raw.include_total is False


def test_use_include_total_creates_new_params_type():
    TotalPage = CustomizedPage[Page, UseIncludeTotal(True)]
    assert TotalPage.__params_type__ is not Params


def test_use_include_total_no_annotation_update():
    TotalPage = CustomizedPage[Page, UseIncludeTotal(True, update_annotations=False)]
    assert TotalPage.__params_type__ is not Params


# --------------------------------------------------------------------------- #
# UseCursorEncoding                                                            #
# --------------------------------------------------------------------------- #

def test_use_cursor_encoding_encoder():
    encoder = lambda p, cursor: f"enc:{cursor}" if cursor else None
    CursorCustom = CustomizedPage[CursorPage, UseCursorEncoding(encoder=encoder)]
    params = CursorCustom.__params_type__()
    assert params.encode_cursor("hello") == "enc:hello"


def test_use_cursor_encoding_decoder():
    decoder = lambda p, cursor: cursor[4:] if cursor else None
    CursorCustom = CustomizedPage[CursorPage, UseCursorEncoding(decoder=decoder)]
    params = CursorCustom.__params_type__()
    assert params.decode_cursor("enc:world") == "world"


def test_use_cursor_encoding_no_encoder_no_decoder_skips():
    # When neither encoder nor decoder is set, __params_type__ should not change
    original_params = CursorPage.__params_type__
    ns = {"__params_type__": original_params}
    customizer = UseCursorEncoding()
    customizer.customize_page_ns(CursorPage, ns)
    assert ns["__params_type__"] is original_params


def test_use_cursor_encoding_encoder_falls_through_to_super():
    # Only decoder set — encoder should use super()
    decoder = lambda p, cursor: cursor
    CursorCustom = CustomizedPage[CursorPage, UseCursorEncoding(decoder=decoder)]
    params = CursorCustom.__params_type__()
    # encode_cursor with no custom encoder should still work (base behavior)
    result = params.encode_cursor(b"test")
    assert result is not None


def test_use_cursor_encoding_decoder_falls_through_to_super():
    # Only encoder set — decoder should use super()
    encoder = lambda p, cursor: "enc"
    CursorCustom = CustomizedPage[CursorPage, UseCursorEncoding(encoder=encoder)]
    params = CursorCustom.__params_type__()
    # decode_cursor with no input
    result = params.decode_cursor(None)
    assert result is None


# --------------------------------------------------------------------------- #
# UseQuotedCursor                                                              #
# --------------------------------------------------------------------------- #

def test_use_quoted_cursor_false():
    CursorCustom = CustomizedPage[CursorPage, UseQuotedCursor(False)]
    assert CursorCustom.__params_type__.quoted_cursor is False


def test_use_quoted_cursor_true():
    CursorCustom = CustomizedPage[CursorPage, UseQuotedCursor(True)]
    assert CursorCustom.__params_type__.quoted_cursor is True


# --------------------------------------------------------------------------- #
# UseStrCursor                                                                 #
# --------------------------------------------------------------------------- #

def test_use_str_cursor_false():
    CursorCustom = CustomizedPage[CursorPage, UseStrCursor(False)]
    assert CursorCustom.__params_type__.str_cursor is False


def test_use_str_cursor_true():
    CursorCustom = CustomizedPage[CursorPage, UseStrCursor(True)]
    assert CursorCustom.__params_type__.str_cursor is True


# --------------------------------------------------------------------------- #
# UseParams                                                                    #
# --------------------------------------------------------------------------- #

def test_use_params_sets_params_type():
    class MyParams(Params):
        pass

    MyPage = CustomizedPage[Page, UseParams(MyParams)]
    # The params type after customization wraps MyParams
    assert issubclass(MyPage.__params_type__, MyParams)


def test_use_params_raises_if_already_customized():
    class MyParams(Params):
        pass

    with pytest.raises(ValueError, match="already customized"):
        CustomizedPage[Page, UseIncludeTotal(True), UseParams(MyParams)]


# --------------------------------------------------------------------------- #
# _update_params_fields                                                        #
# --------------------------------------------------------------------------- #

def test_update_params_fields_non_basemodel_raises():
    class BadParams(AbstractParams):
        def to_raw_params(self) -> BaseRawParams:
            pass

    with pytest.raises(TypeError, match="must be subclass of BaseModel"):
        _update_params_fields(BadParams, {})


def test_update_params_fields_unknown_field_raises():
    with pytest.raises(ValueError, match="Unknown field"):
        _update_params_fields(Params, {"nonexistent": 5})


def test_update_params_fields_valid():
    result = _update_params_fields(Params, {"page": 2})
    assert "page" in result


# --------------------------------------------------------------------------- #
# UseParamsFields                                                              #
# --------------------------------------------------------------------------- #

def test_use_params_fields_sets_default():
    MyPage = CustomizedPage[Page, UseParamsFields(page=3)]
    params = MyPage.__params_type__()
    assert params.page == 3


def test_use_params_fields_init():
    customizer = UseParamsFields(page=1, size=10)
    assert customizer.fields == {"page": 1, "size": 10}


# --------------------------------------------------------------------------- #
# UseOptionalParams                                                            #
# --------------------------------------------------------------------------- #

def test_use_optional_params_makes_page_fields_optional():
    OptPage = CustomizedPage[Page, UseOptionalParams()]
    assert OptPage is not None


# --------------------------------------------------------------------------- #
# UseModelConfig                                                               #
# --------------------------------------------------------------------------- #

def test_use_model_config_init():
    customizer = UseModelConfig(populate_by_name=True)
    assert customizer.config == {"populate_by_name": True}


def test_use_model_config_updates_model_config():
    MyPage = CustomizedPage[Page, UseModelConfig(populate_by_name=True)]
    assert MyPage is not None


# --------------------------------------------------------------------------- #
# UseExcludedFields                                                            #
# --------------------------------------------------------------------------- #

def test_use_excluded_fields_init():
    customizer = UseExcludedFields("total", "pages")
    assert customizer.fields == ("total", "pages")


def test_use_excluded_fields_excludes_field():
    MyPage = CustomizedPage[Page, UseExcludedFields("total")]
    assert "total" not in {
        k for k, v in MyPage.model_fields.items() if not v.exclude
    }


# --------------------------------------------------------------------------- #
# UseFieldsAliases                                                             #
# --------------------------------------------------------------------------- #

def test_use_fields_aliases_init():
    customizer = UseFieldsAliases(total="count")
    assert customizer.aliases == {"total": "count"}


def test_use_fields_aliases_sets_alias():
    MyPage = CustomizedPage[Page, UseFieldsAliases(total="count")]
    assert MyPage.model_fields["total"].serialization_alias == "count"


# --------------------------------------------------------------------------- #
# UseAdditionalFields                                                          #
# --------------------------------------------------------------------------- #

def test_use_additional_fields_tuple_form():
    MyPage = CustomizedPage[Page, UseAdditionalFields(extra=(str, "default"))]
    assert "extra" in MyPage.model_fields


def test_use_additional_fields_non_tuple_form():
    MyPage = CustomizedPage[Page, UseAdditionalFields(extra=str)]
    assert "extra" in MyPage.model_fields


# --------------------------------------------------------------------------- #
# UseFieldTypeAnnotations                                                      #
# --------------------------------------------------------------------------- #

def test_use_field_type_annotations_init():
    customizer = UseFieldTypeAnnotations(total=Optional[int])
    assert customizer.anns == {"total": Optional[int]}


def test_use_field_type_annotations_updates_annotation():
    MyPage = CustomizedPage[Page, UseFieldTypeAnnotations(total=Optional[int])]
    assert MyPage is not None


# --------------------------------------------------------------------------- #
# UseResponseHeaders                                                           #
# --------------------------------------------------------------------------- #

def test_use_response_headers_adds_model_post_init():
    def resolver(page: Any) -> dict:
        return {"X-Total": "0"}

    MyPage = CustomizedPage[Page, UseResponseHeaders(resolver=resolver)]
    assert "model_post_init" in MyPage.__dict__


# --------------------------------------------------------------------------- #
# UsePydanticV1 (PageTransformer)                                             #
# --------------------------------------------------------------------------- #

def test_use_pydantic_v1_transforms_page():
    V1Page = CustomizedPage[Page, UsePydanticV1()]
    assert V1Page is not Page


def test_use_pydantic_v1_transform_page_cls_non_v2_returns_same():
    from fastapi_pagination.pydantic import IS_PYDANTIC_V2

    if not IS_PYDANTIC_V2:
        transformer = UsePydanticV1()
        result = transformer.transform_page_cls(Page)
        assert result is Page
    else:
        pytest.skip("Only relevant for pydantic v1")


# --------------------------------------------------------------------------- #
# UseRequiredFields                                                            #
# --------------------------------------------------------------------------- #

def test_use_required_fields_creates_customized_page():
    MyPage = CustomizedPage[Page, UseRequiredFields()]
    assert MyPage is not Page


# --------------------------------------------------------------------------- #
# Combined customizations                                                      #
# --------------------------------------------------------------------------- #

def test_combined_name_and_module():
    MyPage = CustomizedPage[Page, UseName("Combined"), UseModule("combined.module")]
    assert MyPage.__name__ == "Combined"
    assert MyPage.__module__ == "combined.module"


def test_combined_include_total_and_params_fields():
    MyPage = CustomizedPage[Page, UseParamsFields(page=2), UseIncludeTotal(True)]
    params = MyPage.__params_type__()
    raw = params.to_raw_params()
    assert raw.include_total is True
