import inspect
import pytest
from pydantic import BaseModel
from fastapi import Query

from fastapi_pagination.api import _create_params_dependency
from fastapi_pagination.bases import AbstractParams, RawParams


class NonPydanticParams(AbstractParams):
    def __init__(self, page: int = 1, size: int = 10):
        self.page = page
        self.size = size

    def to_raw_params(self) -> RawParams:
        return RawParams(limit=self.size, offset=self.size * (self.page - 1))


class RequiredFieldParams(BaseModel, AbstractParams):
    page: int
    size: int

    def to_raw_params(self) -> RawParams:
        return RawParams(limit=self.size, offset=self.size * (self.page - 1))


class DefaultFieldParams(BaseModel, AbstractParams):
    page: int = Query(1, ge=1)
    size: int = Query(10, ge=1)

    def to_raw_params(self) -> RawParams:
        return RawParams(limit=self.size, offset=self.size * (self.page - 1))


@pytest.mark.asyncio
async def test_non_pydantic_params_uses_direct_constructor():
    dep = _create_params_dependency(NonPydanticParams)
    gen = dep(page=2, size=5)
    val = await gen.__anext__()
    assert isinstance(val, NonPydanticParams)
    assert val.page == 2
    assert val.size == 5


@pytest.mark.asyncio
async def test_required_field_pydantic_params_no_default():
    dep = _create_params_dependency(RequiredFieldParams)
    gen = dep(page=1, size=20)
    val = await gen.__anext__()
    assert isinstance(val, RequiredFieldParams)
    assert val.page == 1
    assert val.size == 20


@pytest.mark.asyncio
async def test_pydantic_params_with_defaults():
    dep = _create_params_dependency(DefaultFieldParams)
    gen = dep(page=3, size=15)
    val = await gen.__anext__()
    assert isinstance(val, DefaultFieldParams)
    assert val.page == 3
    assert val.size == 15


@pytest.mark.asyncio
async def test_non_pydantic_params_signature_preserved():
    dep = _create_params_dependency(NonPydanticParams)
    sig = inspect.signature(dep)
    assert "page" in sig.parameters
    assert "size" in sig.parameters


def test_create_params_dependency_with_mocked_old_pydantic(mocker):
    mocker.patch("fastapi_pagination.api.IS_PYDANTIC_V2_12_5_OR_HIGHER", False)
    dep = _create_params_dependency(RequiredFieldParams)
    sig = inspect.signature(dep)
    assert "page" in sig.parameters
    assert "size" in sig.parameters
