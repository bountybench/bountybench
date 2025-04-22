import os
from pathlib import Path

from dotenv import dotenv_values, find_dotenv, load_dotenv, set_key
from fastapi import APIRouter, HTTPException, Request

from backend.schema import ApiKeyInput
from resources.model_resource.services.service_providers import (
    ALL_API_KEYS,
    API_KEY_TO_AUTH,
)

api_service_router = APIRouter()


@api_service_router.get("/service/api-service/get")
async def get_api_key(request: Request):
    env_path = Path(find_dotenv())
    if not env_path.is_file():
        raise HTTPException(
            status_code=400, detail="Could not find .env file in project directory."
        )

    load_dotenv(dotenv_path=env_path, override=True)

    # Get values from .env file first
    env_values = dotenv_values(env_path)

    # List of specific API keys to look for
    specific_keys = ALL_API_KEYS

    # Add specific OS environment variables if they're not in .env
    for key in specific_keys:
        if key in os.environ and key not in env_values:
            env_values[key] = os.environ[key]

    masked_values = {}
    for k, v in env_values.items():
        if v:
            if len(v) < 20:
                # For shorter keys, only show last 4 characters
                masked_values[k] = "*" * (len(v) - 4) + v[-4:] if len(v) > 4 else v
            else:
                # For longer keys, show first 4 and last 4 characters
                masked_values[k] = v[:4] + "*" * (len(v) - 8) + v[-4:]
        else:
            masked_values[k] = v

    return masked_values


@api_service_router.post("/service/api-service/update")
async def update_api_key(data: ApiKeyInput, request: Request):
    env_path = Path(find_dotenv())
    if not env_path.is_file():
        raise HTTPException(
            status_code=400, detail="Could not find .env file in project directory."
        )

    if not data.api_key_name or not data.api_key_value:
        raise HTTPException(
            status_code=400, detail="Both API key name and value are required."
        )

    warning_msg = None
    if (
        data.api_key_name not in API_KEY_TO_AUTH
        or API_KEY_TO_AUTH[data.api_key_name] is None
    ):
        warning_msg = f"No auth service implemented for {data.api_key_name}."
    else:
        _ok, _message = API_KEY_TO_AUTH[data.api_key_name](data.api_key_value)
        if not _ok:
            raise HTTPException(status_code=400, detail=_message)
    set_key(env_path, data.api_key_name, data.api_key_value, quote_mode="never")

    return {
        "message": f"{data.api_key_name} updated successfully",
        "warning": warning_msg,
    }
