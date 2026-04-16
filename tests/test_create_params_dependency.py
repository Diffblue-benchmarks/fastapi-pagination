import inspect
from unittest.mock import patch

import pytest

from fastapi_pagination.api import _create_params_dependency, set_params
from fastapi_pagination.bases import AbstractParams, RawParams


class NonPydanticParams(AbstractParams):
    def __init__(self, page: int = 1, size: int = 10):
        self.page = page
        self.size = size

    def to_raw_params(self) -> RawParams:
        return RawParams(limit=self.size, offset=self.size * (self.page - 1))


@pytest.mark.asyncio
async def test_non_pydantic_params_hits_direct_call():
    # Line 241: params(*args, **kwargs) path - is_pydantic_v2_model is False
    dep = _create_params_dependency(NonPydanticParams)
    collected = []
    async for val in dep(page=2, size=5):
        collected.append(val)

    assert len(collected) == 1
    assert collected[0].page == 2
    assert collected[0].size == 5


@pytest.mark.asyncio
async def test_non_pydantic_params_sets_context():
    # Line 241: verify set_params context is active during yield
    dep = _create_params_dependency(NonPydanticParams)
    from fastapi_pagination.api import resolve_params

    async for val in dep(page=3, size=20):
        resolved = resolve_params()
        assert resolved is val


@pytest.mark.asyncio
async def test_pydantic_params_required_field_no_default():
    # Line 260: param_default = inspect.Parameter.empty when field has no default
    from pydantic import BaseModel

    class RequiredFieldParams(BaseModel, AbstractParams):
        page: int
        size: int = 10

        def to_raw_params(self) -> RawParams:
            return RawParams(limit=self.size, offset=self.size * (self.page - 1))

    dep = _create_params_dependency(RequiredFieldParams)
    sig = dep.__signature__

    page_param = sig.parameters["page"]
    assert page_param.default is inspect.Parameter.empty

    collected = []
    async for val in dep(page=1):
        collected.append(val)

    assert len(collected) == 1
    assert collected[0].page == 1
    assert collected[0].size == 10


@pytest.mark.asyncio
async def test_pydantic_params_old_v2_path():
    # Lines 270-271: _get_param without by_name, pydantic v2 < 2.12.5 path
    from pydantic import BaseModel

    class SimpleModel(BaseModel, AbstractParams):
        page: int = 1
        size: int = 50

        def to_raw_params(self) -> RawParams:
            return RawParams(limit=self.size, offset=self.size * (self.page - 1))

    with patch("fastapi_pagination.api.IS_PYDANTIC_V2_12_5_OR_HIGHER", False):
        dep = _create_params_dependency(SimpleModel)

    sig = dep.__signature__
    # In the old v2 path, the annotation is the raw type (not annotated)
    page_param = sig.parameters["page"]
    assert page_param.annotation is int

    collected = []
    async for val in dep(page=7):
        collected.append(val)

    assert len(collected) == 1
    assert collected[0].page == 7
