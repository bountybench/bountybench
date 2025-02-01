from pathlib import Path

from fastapi import APIRouter, Request

from backend.schema import StartWorkflowInput

workflows_router = APIRouter()


@workflows_router.get("/workflow/list")
async def list_workflows():
    return {
        "workflows": [
            {
                "id": "detect",
                "name": "Detect Workflow",
                "description": "Workflow for detecting and exploiting vulnerabilities",
            },
            {
                "id": "exploit_and_patch",
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


@workflows_router.get("/workflows/active")
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
            interactive=workflow_data.interactive,
            phase_iterations=workflow_data.iterations,
        )

        workflow_id = workflow.workflow_message.workflow_id
        active_workflows[workflow_id] = {
            "instance": workflow,
            "status": "initializing",
            "workflow_message": workflow.workflow_message,
        }
        return {"workflow_id": workflow_id, "status": "initializing"}
    except Exception as e:
        return {"error": str(e)}
