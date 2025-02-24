import os
import traceback
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from backend.schema import SaveConfigRequest, StartWorkflowInput
from prompts.vulnerability_prompts import VulnerabilityType
from resources.model_resource.model_mapping import NonHELMMapping, TokenizerMapping

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
    active_workflows = request.app.state.active_workflows
    active_workflows_list = []
    for workflow_id, workflow_data in active_workflows.items():
        active_workflows_list.append(
            {
                "id": workflow_id,
                "status": workflow_data["status"],
                "name": workflow_data["instance"].__class__.__name__,
                "task": workflow_data["instance"].task,
                "timestamp": getattr(
                    workflow_data["workflow_message"], "timestamp", None
                ),
            }
        )
    return {"active_workflows": active_workflows_list}


@workflows_router.post("/workflow/start")
async def start_workflow(workflow_data: StartWorkflowInput, request: Request):
    try:
        workflow_factory = request.app.state.workflow_factory
        active_workflows = request.app.state.active_workflows

        workflow = workflow_factory[workflow_data.workflow_name](
            task_dir=Path(workflow_data.task_dir),
            bounty_number=workflow_data.bounty_number,
            vulnerability_type=workflow_data.vulnerability_type,
            interactive=workflow_data.interactive,
            phase_iterations=workflow_data.iterations,
            model=workflow_data.model,
            use_helm=workflow_data.use_helm,
            use_mock_model=workflow_data.use_mock_model,
        )
        workflow_id = workflow.workflow_message.workflow_id
        active_workflows[workflow_id] = {
            "instance": workflow,
            "status": "initializing",
            "workflow_message": workflow.workflow_message,
        }
        return {
            "workflow_id": workflow_id,
            "model": workflow_data.model,
            "status": "initializing",
        }
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


@workflows_router.post("/workflow/save-config")
async def save_config(request: SaveConfigRequest):
    try:
        # Get the parent directory of the current working directory
        config_dir = Path(os.getcwd()) / "configs"

        # Create the configs directory if it doesn't exist
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create the full file path
        file_path = config_dir / request.fileName

        # Write the configuration to the file
        file_path.write_text(request.config)

        return {"message": f"Configuration saved successfully to {file_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
