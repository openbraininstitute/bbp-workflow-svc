from unittest.mock import Mock, patch

import pytest
import requests

from bbp_workflow_svc import util as test_module
from bbp_workflow_svc.testing import patchenv


@patchenv(TEST_ENV_VAR="test_value")
def test_get_required_env_returns_value():

    result = test_module.get_required_env("TEST_ENV_VAR")

    assert result == "test_value"


@patchenv()
def test_get_required_env_raises_error_when_not_set():

    test_var_name = "FOO"

    expected_str = f"Required environment variable '{test_var_name}' is not set."

    with pytest.raises(ValueError, match=expected_str) as exc_info:
        test_module.get_required_env(test_var_name)


@patchenv(FOO="")
def test_get_required_env_raises_error_when_not_set():

    test_var_name = "FOO"

    expected_str = f"Required environment variable '{test_var_name}' cannot be empty."

    with pytest.raises(ValueError, match=expected_str) as exc_info:
        test_module.get_required_env(test_var_name)


def test_make_request_success():
    # Mock the requests.request method
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": "Hello, world!"}

    with patch("requests.request", return_value=mock_response):
        response = test_module.make_request("https://api.example.com/test", method="GET")
        assert response.status_code == 200
        assert response.json() == {"message": "Hello, world!"}


def test_make_request_failure():
    # Mock requests.request to raise an HTTPError
    with patch("requests.request", side_effect=requests.exceptions.HTTPError()):
        with pytest.raises(requests.exceptions.HTTPError):
            test_module.make_request("https://api.example.com/test", method="GET")
