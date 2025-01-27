import pytest

from bbp_workflow_svc.testing import patchenv
from bbp_workflow_svc.util import get_required_env


@patchenv(TEST_ENV_VAR="test_value")
def test_get_required_env_returns_value():

    result = get_required_env("TEST_ENV_VAR")

    assert result == "test_value"


@patchenv()
def test_get_required_env_raises_error_when_not_set():

    test_var_name = "FOO"

    expected_str = f"Required environment variable '{test_var_name}' is not set."

    with pytest.raises(ValueError, match=expected_str) as exc_info:
        get_required_env(test_var_name)


@patchenv(FOO="")
def test_get_required_env_raises_error_when_not_set():

    test_var_name = "FOO"

    expected_str = f"Required environment variable '{test_var_name}' cannot be empty."

    with pytest.raises(ValueError, match=expected_str) as exc_info:
        get_required_env(test_var_name)
