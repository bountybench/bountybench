from typing import Tuple

import requests

REASONING_MODELS = ["o1", "o3", "o4"]

# Authentication helpers


## Bulk providers
def _auth_helm_api_key(
    api_key: str, model_name: str = None, verify_model: bool = False
) -> Tuple[bool, str]:
    auth_url = f"https://crfm-models.stanford.edu/api/account?auth=%7B%22api_key%22%3A%22{api_key}%22%7D"
    response = requests.get(auth_url)
    if response.status_code == 200:
        if "error" in response.json():
            return False, response.json()["error"]

        if not verify_model or model_name is None:
            return True, ""

        model_url = "https://crfm-models.stanford.edu/api/general_info"
        response = requests.get(model_url)
        try:
            valid_models = [model["name"] for model in response.json()["all_models"]]
            if model_name not in valid_models:
                raise ValueError(
                    f"Model {model_name} not found.\n\nAvailable models from Helm: {valid_models}"
                )
            return True, ""
        except Exception as e:
            return False, str(e)

    return False, response.text


def _auth_together_api_key(
    api_key: str, model_name: str = None, verify_model: bool = False
) -> Tuple[bool, str]:
    url = "https://api.together.xyz/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        try:
            if not verify_model or model_name is None:
                return True, ""

            valid_models = [model["id"] for model in response.json()]

            if model_name not in valid_models:
                raise ValueError(
                    f"Model {model_name} not found.\n\nAvailable models from together.ai: {valid_models}"
                )
            return True, ""
        except Exception as e:
            return False, str(e)

    return False, response.text


## Individual providers
def _auth_openai_api_key(
    api_key: str, model_name: str = None, verify_model: bool = False
) -> Tuple[bool, str]:
    url = "https://api.openai.com/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        try:
            if not verify_model or model_name is None:
                return True, ""

            valid_models = [model["id"] for model in response.json()["data"]]

            model_id = model_name.split("/")[-1]

            # Strip -high-reasoning-effort or -low-reasoning-effort suffixes from openai reasoning models
            if any(model_id.startswith(prefix) for prefix in REASONING_MODELS):
                for suffix in ["-high-reasoning-effort", "-low-reasoning-effort"]:
                    if model_id.endswith(suffix):
                        model_id = model_id[: -len(suffix)]
                        break

            if model_id not in valid_models:
                error_msg = f"Model {model_name} not found.\n\nAvailable models from OpenAI: {valid_models}"
                raise ValueError(error_msg)

            return True, ""
        except Exception as e:
            return False, str(e)

    return False, response.text


def _auth_anthropic_api_key(
    api_key: str, model_name: str = None, verify_model: bool = False
) -> Tuple[bool, str]:
    url = "https://api.anthropic.com/v1/models"
    headers = {"x-api-key": f"{api_key}", "anthropic-version": "2023-06-01"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        try:
            if not verify_model or model_name is None:
                return True, ""

            valid_models = [model["id"] for model in response.json()["data"]]

            if model_name.split("/")[-1] not in valid_models:
                raise ValueError(
                    f"Model {model_name} not found.\n\nAvailable models from Anthropic: {valid_models}"
                )

            return True, ""
        except Exception as e:
            return False, str(e)

    return False, response.text


def _auth_google_gemini_api_key(
    api_key: str, model_name: str = None, verify_model: bool = False
) -> Tuple[bool, str]:
    url = "https://generativelanguage.googleapis.com/v1/models"
    params = {"key": api_key}

    response = requests.get(url, params=params)
    if response.status_code == 200:
        try:
            if not verify_model or model_name is None:
                return True, ""

            valid_models = [
                model["name"].split("/")[-1] for model in response.json()["models"]
            ]

            if model_name.split("/")[-1] not in valid_models:
                raise ValueError(
                    f"Model {model_name} not found.\n\nAvailable models from Google: {valid_models}"
                )
            return True, ""
        except Exception as e:
            return False, str(e)

    return False, response.text


def _auth_xai_api_key(
    api_key: str, model_name: str = None, verify_model: bool = False
) -> Tuple[bool, str]:
    url = "https://api.x.ai/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}

    model_name = model_name.split("/")[-1] if model_name else None

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        try:
            if not verify_model or model_name is None:
                return True, ""

            valid_models = [model["id"] for model in response.json()["data"]]

            if model_name not in valid_models:
                raise ValueError(
                    f"Model {model_name} not found.\n\nAvailable models from X.ai: {valid_models}"
                )
            return True, ""
        except Exception as e:
            return False, str(e)

    return False, response.text
