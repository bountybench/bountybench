import os
from pathlib import Path
from typing import Callable, Optional, Tuple

import requests
from dotenv import find_dotenv, load_dotenv, set_key


def _model_provider_lookup(model_name: str, helm: bool) -> str:
    """
    Given a model name, return the associated API key environment variable name.
    If using Helm, return the Helm API key environment variable name.
    """
    if helm:
        return "HELM_API_KEY"
    else:
        if "/" in model_name:
            provider = model_name.split("/")[0].lower()
            # Map provider prefixes to environment variable names
            if provider == "openai":
                return "OPENAI_API_KEY"
            elif provider == "anthropic":
                return "ANTHROPIC_API_KEY"
            elif provider == "google":
                return "GOOGLE_API_KEY"
            elif provider in ["meta", "mistralai"]:
                return "TOGETHER_API_KEY"
        raise Exception(f"Unknown model: {model_name}, cannot lookup key")


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


def verify_and_auth_api_key(
    model_name: str, helm: bool, auth_service: Optional[Callable] = None
):
    requested_api_key: str = _model_provider_lookup(
        model_name, helm
    )  # Get the API key name

    env_path = Path(find_dotenv())
    if env_path.is_file():
        f"[API Service] .env file found at {env_path}"
        load_dotenv(dotenv_path=env_path)
    else:
        raise FileNotFoundError("Could not find .env file in project directory.")

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
    auth_service = auth_service or AUTH_SERVICE[requested_api_key]
    _ok, _message = auth_service(requested_api_value)

    while not _ok:
        print("[API Service] API key authentication failed. Please double-check.")
        requested_api_value = input(
            f"[API Service] Please enter your {requested_api_key}: "
        )
        print("[API Service] Received new API key.")
        _new_key_requested = True
        _ok, _message = auth_service(requested_api_value)

    print("[API Service] API key authentication successful.")
    # Ask user if they want to save the API key to the .env file
    if _new_key_requested:
        _save_ok = (
            input(
                f"Do you want to save your {requested_api_key} to .env file? (y/n): "
            ).lower()
            == "y"
        )
        if _save_ok:
            print("[API Service] Saving API key to .env file.")
            set_key(
                env_path, requested_api_key, requested_api_value, quote_mode="never"
            )
            load_dotenv(dotenv_path=env_path, override=True)
        else:
            print("[API Service] API key NOT saved to .env file.")
            os.environ[requested_api_key] = requested_api_value
    return


def check_api_key_validity(model_name: str, helm: bool) -> bool:
    """
    Check if the API key exists and is valid without prompting the user.
    Returns True if the API key is valid, False otherwise.
    """
    requested_api_key: str = _model_provider_lookup(model_name, helm)

    env_path = Path(find_dotenv())
    if env_path.is_file():
        load_dotenv(dotenv_path=env_path)
    else:
        print("[API Service] .env file not found.")
        return False

    # Check if API key exists and is not empty
    if requested_api_key not in os.environ or not os.environ[requested_api_key].strip():
        print(f"[API Service] {requested_api_key} is missing or empty.")
        return False

    requested_api_value = os.environ[requested_api_key]

    # Authenticate the API key
    auth_service = AUTH_SERVICE.get(requested_api_key)
    if not auth_service:
        print(f"[API Service] No authentication service found for {requested_api_key}.")
        return False

    _ok, _message = auth_service(requested_api_value)

    if not _ok:
        print(f"[API Service] API key authentication failed: {_message}")
        return False

    return True
