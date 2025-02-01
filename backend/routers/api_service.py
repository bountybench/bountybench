import os
from pathlib import Path

from dotenv import dotenv_values, find_dotenv, load_dotenv, set_key
from fastapi import APIRouter, HTTPException

from backend.schema import ApiKeyInput
from resources.model_resource.services.api_key_service import AUTH_SERVICE

router = APIRouter()


def setup_routes(app):
    router.add_api_route("/service/api-service/get", get_api_key, methods=["GET"])
    router.add_api_route(
        "/service/api-service/update", update_api_key, methods=["POST"]
    )

    app.include_router(router)


async def get_api_key():
    env_path = Path(find_dotenv())
    if not env_path.is_file():
        raise HTTPException(
            status_code=400, detail="Could not find .env file in project directory."
        )

    load_dotenv(dotenv_path=env_path, override=True)
    return {k: os.environ[k] for k in dotenv_values(env_path)}


async def update_api_key(data: ApiKeyInput):
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
    if data.api_key_name not in AUTH_SERVICE or AUTH_SERVICE[data.api_key_name] is None:
        warning_msg = f"No auth service implemented for {data.api_key_name}."
    else:
        _ok, _message = AUTH_SERVICE[data.api_key_name](data.api_key_value)
        if not _ok:
            raise HTTPException(status_code=400, detail=_message)
    set_key(env_path, data.api_key_name, data.api_key_value, quote_mode="never")

    return {
        "message": f"{data.api_key_name} updated successfully",
        "warning": warning_msg,
    }
