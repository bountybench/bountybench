import itertools
import os
import traceback
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from backend.schema import ExperimentConfig, SaveConfigRequest
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
async def start(workflow_data: ExperimentConfig, request: Request):
    """Unified endpoint for starting one or more workflows."""
    try:
        workflow_factory = request.app.state.workflow_factory
        active_workflows = request.app.state.active_workflows

        # Get workflow name in proper format
        workflow_type = workflow_data.workflow_name

        if workflow_type not in workflow_factory:
            return {"error": f"Workflow '{workflow_type}' not found"}

        # Prepare data for combinations
        tasks = workflow_data.tasks
        models = workflow_data.models
        vulnerability_type = (
            [workflow_data.vulnerability_type]
            if workflow_data.vulnerability_type
            else [""]
        )
        phase_iterations = workflow_data.phase_iterations
        trials_per_config = workflow_data.trials_per_config
        interactive = workflow_data.interactive
        use_mock_model = workflow_data.use_mock_model

        # Generate workflows using the helper function
        workflows = generate_workflows(
            workflow_factory,
            workflow_type,
            tasks,
            models,
            phase_iterations,
            vulnerability_type,
            trials_per_config,
            interactive,
            use_mock_model,
        )

        # Store workflows in active workflows and collect IDs
        workflow_ids = []
        for wf in workflows:
            active_workflows[wf["workflow_id"]] = {
                "instance": wf["instance"],
                "status": wf["status"],
                "workflow_message": wf["workflow_message"],
            }
            workflow_ids.append(
                {
                    "workflow_id": wf["workflow_id"],
                    "model": wf["model"],
                    "status": wf["status"],
                }
            )

        # For backward compatibility, if only one workflow was started, return its details
        if len(workflow_ids) == 1:
            return workflow_ids[0]

        # Otherwise return all workflow IDs
        return {
            "status": "started",
            "workflows": workflow_ids,
            "total_workflows": len(workflow_ids),
        }

    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Error in parallel run: {str(e)}\n{error_traceback}")
        return {"error": str(e)}


def generate_workflows(
    workflow_factory,
    workflow_type,
    tasks,
    models,
    phase_iterations,
    vulnerability_type,
    trials_per_config,
    interactive,
    use_mock_model,
):
    """Generates workflow instances based on the provided configuration."""
    workflow_instances = []

    # Build parameter combinations
    params = [tasks, models, phase_iterations]
    if vulnerability_type[0] and workflow_type.lower().startswith("detect"):
        params.append(vulnerability_type)

    # Generate all workflows from parameter combinations
    for combination in itertools.product(*params):
        task, model, iterations = combination[:3]
        vuln_type = combination[3] if len(combination) > 3 else ""

        # Run each configuration the specified number of trials
        for _ in range(trials_per_config):
            try:
                # Create workflow instance
                workflow = workflow_factory[workflow_type](
                    task_dir=Path(f"bountybench/{task.task_dir}"),
                    bounty_number=task.bounty_number,
                    vulnerability_type=vuln_type,
                    interactive=interactive,
                    phase_iterations=iterations,
                    model=model.name,
                    use_helm=model.use_helm,
                    use_mock_model=use_mock_model,
                )

                # Store workflow information
                workflow_instances.append(
                    {
                        "instance": workflow,
                        "workflow_id": workflow.workflow_message.workflow_id,
                        "model": model.name,
                        "status": "initializing",
                        "workflow_message": workflow.workflow_message,
                    }
                )

                print(
                    f"Started workflow {workflow.workflow_message.workflow_id} with model {model.name}"
                )

            except Exception as e:
                error_traceback = traceback.format_exc()
                print(
                    f"Error starting individual workflow: {str(e)}\n{error_traceback}"
                )
                # Continue with other workflows even if one fails

    return workflow_instances


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
