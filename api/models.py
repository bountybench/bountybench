from pydantic import BaseModel

class WorkflowStartRequest(BaseModel):
    workflow_name: str
    task_repo_dir: str
    bounty_number: str
    interactive: bool = False
