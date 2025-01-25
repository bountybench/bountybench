import requests
import os
from typing import Tuple
from dotenv import load_dotenv, set_key
from pathlib import Path


def _model_provider_lookup(model_name: str, helm: bool) -> str:
    """
    Given a model name, return the associated API key environment variable name.
    If using Helm, return the Helm API key environment variable name.
    """
    if helm:
        return "HELM_API_KEY"
    else:
        provider = model_name.split("/")[0]
        assert provider in ["openai", "anthropic"]
        return f"{provider.upper()}_API_KEY"


# Authentication helpers
def _auth_helm_api_key(api_key: str) -> Tuple[bool, str]:
    url = f"https://crfm-models.stanford.edu/api/account?auth=%7B%22api_key%22%3A%22{api_key}%22%7D"
    response = requests.get(url)
    if response.status_code == 200:
        if "error" in response.json():
            return False, response.json()["error"]
        return True, ""

    return False, response.text


def _auth_openai_api_key(api_key: str) -> Tuple[bool, str]:
    url = "https://api.openai.com/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        if "error" in response.json():
            return False, response.json()["error"]
        return True, ""

    return False, response.text


def _auth_anthropic_api_key(api_key: str) -> Tuple[bool, str]:
    url = "https://api.anthropic.com/v1/models"
    headers = {"x-api-key": f"{api_key}", "anthropic-version": "2023-06-01"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        if "error" in response.json():
            return False, response.json()["error"]
        return True, ""

    return False, response.text


AUTH_SERVICE = {
    "HELM_API_KEY": _auth_helm_api_key,
    "OPENAI_API_KEY": _auth_openai_api_key,
    "AZURE_OPENAI_API_KEY": None,
    "AZURE_OPENAI_ENDPOINT": None,
    "ANTHROPIC_API_KEY": _auth_anthropic_api_key,
    "GOOGLE_API_KEY": None,
    "TOGETHER_API_KEY": None,
}


def verify_and_auth_api_key(model_name: str, helm: bool):
    requested_api_key: str = _model_provider_lookup(
        model_name, helm
    )  # Get the API key name

    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.is_file():
        load_dotenv(dotenv_path=env_path)

    _new_key_requested = False

    # Prompt user for API key if not found in environment variables
    if requested_api_key not in os.environ:
        print(f"[API Service] {requested_api_key} not registered.")
        requested_api_value = input(
            f"[API Service] Please Enter your {requested_api_key}: "
        )
        _new_key_requested = True
    else:
        requested_api_value = os.environ[requested_api_key]

    # Authenticate the API key, keep prompting for input until a valid key is entered
    auth_service = AUTH_SERVICE[requested_api_key]
    _ok, _message = auth_service(requested_api_value)
    while not _ok:
        print("[API Service] API key authentication failed. Please double-check.")
        requested_api_value = input(
            f"[API Service] Please enter your {requested_api_key}: "
        )
        _new_key_requested = True
        _ok, _message = auth_service(requested_api_value)

    # Ask user if they want to save the API key to the .env file
    if _new_key_requested:
        _save_ok = (
            input(
                f"Do you want to save your {requested_api_key} to .env file? (y/n): "
            ).lower()
            == "y"
        )
        if _save_ok:
            set_key(
                env_path, requested_api_key, requested_api_value, quote_mode="never"
            )
            load_dotenv(dotenv_path=env_path, override=True)
        else:
            os.environ[requested_api_key] = requested_api_value
    return


# -----------------------------------------------------
# |                      Tests                        |
# -----------------------------------------------------


def test_auth_helm_api_key():
    assert _auth_helm_api_key("obviously_invalid_api_key", "")[0] is False

    valid_api_key = input("Enter a valid HELM API key: ")
    assert _auth_helm_api_key(valid_api_key)[0] is True


def test_auth_openai_api_key():
    assert _auth_openai_api_key("obviously_invalid_api_key")[0] is False

    valid_api_key = input("Enter a valid OpenAI API key: ")
    assert _auth_openai_api_key(valid_api_key)[0] is True


def test_auth_anthropic_api_key():
    assert _auth_anthropic_api_key("obviously_invalid_api_key")[0] is False

    valid_api_key = input("Enter a valid Anthropic API key: ")
    assert _auth_anthropic_api_key(valid_api_key)[0] is True


if __name__ == "__main__":
    test_auth_helm_api_key()
    print(" - auth_helm_api_key passed")

    test_auth_openai_api_key()
    print(" - auth_openai_api_key passed")

    test_auth_anthropic_api_key()
    print(" - auth_anthropic_api_key passed")
