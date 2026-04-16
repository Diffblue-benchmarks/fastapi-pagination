from unittest.mock import MagicMock, patch

import pytest

from fastapi_pagination.paginator import paginate


@pytest.fixture
def mock_page():
    return MagicMock()


def test_paginate_calls_check_installed_extensions_when_not_safe(mock_page):
    sequence = [1, 2, 3]
    with patch("fastapi_pagination.paginator.check_installed_extensions") as mock_check, \
         patch("fastapi_pagination.paginator.run_sync_flow", return_value=mock_page):
        result = paginate(sequence, safe=False)

    mock_check.assert_called_once()
    assert result is mock_page


def test_paginate_skips_check_installed_extensions_when_safe(mock_page):
    sequence = [1, 2, 3]
    with patch("fastapi_pagination.paginator.check_installed_extensions") as mock_check, \
         patch("fastapi_pagination.paginator.run_sync_flow", return_value=mock_page):
        result = paginate(sequence, safe=True)

    mock_check.assert_not_called()
    assert result is mock_page


def test_paginate_uses_len_as_default_length_function(mock_page):
    sequence = [10, 20, 30]
    captured = {}

    def fake_run_sync_flow(flow_obj):
        captured["flow"] = flow_obj
        return mock_page

    with patch("fastapi_pagination.paginator.check_installed_extensions"), \
         patch("fastapi_pagination.paginator.run_sync_flow", side_effect=fake_run_sync_flow), \
         patch("fastapi_pagination.paginator.generic_flow") as mock_generic_flow, \
         patch("fastapi_pagination.paginator.flow_expr") as mock_flow_expr:
        paginate(sequence)

    assert mock_generic_flow.called


def test_paginate_uses_custom_length_function(mock_page):
    sequence = [1, 2, 3, 4, 5]
    custom_len = MagicMock(return_value=99)

    with patch("fastapi_pagination.paginator.check_installed_extensions"), \
         patch("fastapi_pagination.paginator.run_sync_flow", return_value=mock_page), \
         patch("fastapi_pagination.paginator.generic_flow") as mock_generic_flow, \
         patch("fastapi_pagination.paginator.flow_expr"):
        result = paginate(sequence, length_function=custom_len)

    assert result is mock_page
    assert mock_generic_flow.called


def test_paginate_returns_result_from_run_sync_flow():
    sequence = ["a", "b", "c"]
    expected = MagicMock()

    with patch("fastapi_pagination.paginator.check_installed_extensions"), \
         patch("fastapi_pagination.paginator.run_sync_flow", return_value=expected):
        result = paginate(sequence, safe=True)

    assert result is expected


def test_paginate_passes_params_to_generic_flow(mock_page):
    sequence = [1, 2, 3]
    mock_params = MagicMock()

    with patch("fastapi_pagination.paginator.check_installed_extensions"), \
         patch("fastapi_pagination.paginator.run_sync_flow", return_value=mock_page), \
         patch("fastapi_pagination.paginator.generic_flow") as mock_generic_flow, \
         patch("fastapi_pagination.paginator.flow_expr"):
        paginate(sequence, params=mock_params, safe=True)

    call_kwargs = mock_generic_flow.call_args.kwargs
    assert call_kwargs["params"] is mock_params


def test_paginate_passes_additional_data_and_config_to_generic_flow(mock_page):
    sequence = [1, 2, 3]
    mock_additional_data = MagicMock()
    mock_config = MagicMock()

    with patch("fastapi_pagination.paginator.check_installed_extensions"), \
         patch("fastapi_pagination.paginator.run_sync_flow", return_value=mock_page), \
         patch("fastapi_pagination.paginator.generic_flow") as mock_generic_flow, \
         patch("fastapi_pagination.paginator.flow_expr"):
        paginate(sequence, safe=True, additional_data=mock_additional_data, config=mock_config)

    call_kwargs = mock_generic_flow.call_args.kwargs
    assert call_kwargs["additional_data"] is mock_additional_data
    assert call_kwargs["config"] is mock_config
