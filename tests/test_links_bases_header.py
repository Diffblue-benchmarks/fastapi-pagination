from types import SimpleNamespace
from typing import Any

import pytest

from fastapi_pagination.links.bases import BaseUseHeaderLinks, Links


class ConcreteHeaderLinks(BaseUseHeaderLinks):
    def resolve_links(self, page: Any, /) -> Links:
        return Links()


@pytest.fixture
def customizer():
    return ConcreteHeaderLinks()


def test_customize_page_ns_pydantic_v1_adds_validator_to_ns(customizer):
    ns: dict = {}
    customizer._customize_page_ns_pydantic_v1(object, ns)
    assert "__add_links_to_header__" in ns


def test_customize_page_ns_pydantic_v1_inner_function_returns_values(customizer):
    ns: dict = {}
    customizer._customize_page_ns_pydantic_v1(object, ns)

    validator_descriptor = ns["__add_links_to_header__"]
    inner_func = validator_descriptor.wrapped.__func__

    values = {"items": [], "total": 0}
    result = inner_func(None, values)
    assert result == values


def test_customize_page_ns_pydantic_v1_inner_function_calls_resolve_links(customizer, mocker):
    ns: dict = {}
    customizer._customize_page_ns_pydantic_v1(object, ns)

    spy = mocker.spy(customizer, "resolve_links")
    validator_descriptor = ns["__add_links_to_header__"]
    inner_func = validator_descriptor.wrapped.__func__

    values = {"items": [], "total": 0}
    inner_func(None, values)

    spy.assert_called_once()


def test_customize_page_ns_pydantic_v1_inner_function_with_links(mocker):
    mock_response = mocker.MagicMock()
    mock_response.headers = {}
    mocker.patch("fastapi_pagination.links.bases.response", return_value=mock_response)

    class LinkReturningCustomizer(BaseUseHeaderLinks):
        def resolve_links(self, page: Any, /) -> Links:
            return Links(first="/api?page=1", last="/api?page=10")

    customizer = LinkReturningCustomizer()
    ns: dict = {}
    customizer._customize_page_ns_pydantic_v1(object, ns)

    validator_descriptor = ns["__add_links_to_header__"]
    inner_func = validator_descriptor.wrapped.__func__

    values = {"items": [], "total": 0}
    result = inner_func(None, values)
    assert result == values
    assert "Link" in mock_response.headers
