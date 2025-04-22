import os
from pathlib import Path
from typing import Callable, Optional, Tuple

from dotenv import find_dotenv, load_dotenv, set_key

from resources.model_resource.model_mapping import (
    HelmModelInfo,
    NonHelmModelInfo,
    get_model_info,
)
from resources.model_resource.services.service_providers import PROVIDER_CONFIG


def _api_key_lookup(model_name: str, helm: bool) -> str:
    """
    Given a model name, return the associated API key environment variable name.
    If using Helm, return the Helm API key environment variable name.
    """
    if helm:
        model_info: HelmModelInfo = get_model_info(model_name, helm=True)
        print(f"[API Service] Helm model info: {model_info}")
        return PROVIDER_CONFIG[model_info.provider].api_key_name
    else:
        model_info: NonHelmModelInfo = get_model_info(model_name, helm=False)
        print(f"[API Service] Non-Helm model info: {model_info}")
        return PROVIDER_CONFIG[model_info.provider].api_key_name


def _auth_service_lookup(model_name: str, helm: bool) -> Optional[Callable]:
    """
    Given a model name, return the associated authentication service.
    If using Helm, return the Helm authentication service.
    """
    if helm:
        model_info: HelmModelInfo = get_model_info(model_name, helm=True)
        print(f"[API Service] Helm model info: {model_info}")
        return PROVIDER_CONFIG[model_info.provider].auth_function
    else:
        model_info: NonHelmModelInfo = get_model_info(model_name, helm=False)
        print(f"[API Service] Non-Helm model info: {model_info}")
        return PROVIDER_CONFIG[model_info.provider].auth_function


def verify_and_auth_api_key(
    model_name: str, helm: bool, auth_service: Optional[Callable] = None
):
    requested_api_key: str = _api_key_lookup(model_name, helm)
    print(f"[API Service] requested_api_key: {requested_api_key}")

    env_path = Path(find_dotenv())
    if env_path.is_file():
        print(f"[API Service] .env file found at {env_path}")
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

    auth_service = auth_service or _auth_service_lookup(model_name, helm)
    if not auth_service:
        raise NotImplementedError(
            f"No authentication service found for {model_name, requested_api_key}. Did you want to use Helm?"
        )

    _ok, _message = auth_service(requested_api_value, model_name, verify_model=True)

    while not _ok:
        print(
            f"[API Service] API key authentication failed. Please double-check: {_message}"
        )
        requested_api_value = input(
            f"[API Service] Please enter your {requested_api_key}: "
        )
        print("[API Service] Received new API key.")
        _new_key_requested = True

        _ok, _message = auth_service(requested_api_value, model_name, verify_model=True)

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
    requested_api_key: str = _api_key_lookup(model_name, helm)

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
    auth_service = _auth_service_lookup(model_name, helm)
    if not auth_service:
        print(f"[API Service] No authentication service found for {requested_api_key}.")
        return False

    _ok, _message = auth_service(requested_api_value)

    if not _ok:
        print(
            f"[API Service] API key authentication failed. Please double-check: {_message}"
        )
        return False

    return True
