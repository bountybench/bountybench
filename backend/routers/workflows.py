import os
import traceback
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from backend.schema import SaveConfigRequest, StartWorkflowInput
from backend.execution_backends import ExecutionBackend
from prompts.vulnerability_prompts import VulnerabilityType
from resources.model_resource.model_mapping import NonHELMMapping, TokenizerMapping
from resources.model_resource.model_resource import ModelResourceConfig

workflows_router = APIRouter()


@workflows_router.get("/workflow/list")
async def list_workflows():
    return {
        "workflows": [
            {
                "id": "detect_patch",
                "name": "Detect Patch Workflow",
                "description": "Workflow for detecting and patching vulnerabilities",
            },
            {
                "id": "exploit_patch",
                "name": "Exploit and Patch Workflow",
                "description": "Workflow for exploiting and patching vulnerabilities",
            },
            {
                "id": "patch",
                "name": "Patch Workflow",
                "description": "Workflow for patching vulnerabilities",
            },
            {
                "id": "chat",
                "name": "Chat Workflow",
                "description": "Workflow for chatting",
            },
        ]
    }


@workflows_router.get("/workflow/active")
async def list_active_workflows(request: Request):
    execution_backend: ExecutionBackend = request.app.state.execution_backend
    try:
        workflows = await execution_backend.list_active_workflows()
        return {"active_workflows": workflows}
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Error listing workflows: {str(e)}\n{error_traceback}")
        return {"error": str(e)}


@workflows_router.post("/workflow/start")
async def start_workflow(workflow_data: StartWorkflowInput, request: Request):
    try:
        execution_backend: ExecutionBackend = request.app.state.execution_backend
        result = await execution_backend.start_workflow(workflow_data)
        return result
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Error starting workflow: {str(e)}\n{error_traceback}")
        return {"error": str(e)}


@workflows_router.get("/workflow/allmodels")
async def list_all_models():
    """List available model types"""
    helm_models = list(set(TokenizerMapping.mapping.keys()))
    nonhelm_models = [
        value if "/" in value else key for key, value in NonHELMMapping.mapping.items()
    ]
    all_models = sorted(set(helm_models + nonhelm_models))
    all_models = [{"name": model} for model in all_models]
    return {"allModels": all_models}


@workflows_router.get("/workflow/models")
async def list_helm_models():
    """List HELM and NONHELM model types separately"""
    helm_models = sorted(set(TokenizerMapping.mapping.keys()))
    helm_mapping = [{"name": model} for model in helm_models]
    nonhelm_models = sorted(
        [
            value if "/" in value else key
            for key, value in NonHELMMapping.mapping.items()
        ]
    )
    nonhelm_mapping = [{"name": model} for model in nonhelm_models]
    return {"helmModels": helm_mapping, "nonHelmModels": nonhelm_mapping}


@workflows_router.get("/workflow/vulnerability-types")
async def list_vulnerability_types():
    return {
        "vulnerability_types": [
            {"name": vt.name, "value": vt.value} for vt in VulnerabilityType
        ]
    }


@workflows_router.get("/workflow/config-defaults")
async def get_config_defaults():
    """Return default configuration values for the UI"""
    # Get defaults from the class fields
    max_input_tokens = next(
        field.default
        for field in ModelResourceConfig.__dataclass_fields__.values()
        if field.name == "max_input_tokens"
    )
    max_output_tokens = next(
        field.default
        for field in ModelResourceConfig.__dataclass_fields__.values()
        if field.name == "max_output_tokens"
    )

    return {
        "max_input_tokens": max_input_tokens,
        "max_output_tokens": max_output_tokens,
    }


@workflows_router.post("/workflow/save-config")
async def save_config(config_request: SaveConfigRequest, request: Request):
    """
    Save configuration with the execution backend.
    """
    execution_backend: ExecutionBackend =  request.app.state.execution_backend
    try:
        result = await execution_backend.save_config(config_request.fileName, config_request.config)
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
