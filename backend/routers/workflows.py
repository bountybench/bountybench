from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.schema import StartWorkflowInput

router = APIRouter()


def setup_routes(app, workflow_factory, active_workflows, websocket_manager):
    router.add_api_route("/workflow/list", list_workflows, methods=["GET"])
    router.add_api_route("/workflows/active", list_active_workflows, methods=["GET"])
    router.add_api_route("/workflow/start", start_workflow, methods=["POST"])

    app.include_router(router)


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


async def list_active_workflows(active_workflows):
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


async def start_workflow(
    workflow_data: StartWorkflowInput, workflow_factory, active_workflows
):
    print(workflow_data)
    try:
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
