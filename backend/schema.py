from pathlib import Path

from pydantic import BaseModel, Field


class StartWorkflowInput(BaseModel):
    workflow_name: str = Field(..., description="Name of the workflow to start")
    task_dir: Path = Field(..., description="Directory of the tasks")
    bounty_number: str = Field(
        ..., description="Bounty number associated with the workflow"
    )
    vulnerability_type: str = Field(
        ..., description="Vulnerability type to detect"
    )
    interactive: bool = Field(
        default=False, description="Whether the workflow is interactive"
    )
    iterations: int = Field(..., gt=0, description="Number of phase iterations")
    model: str = Field(..., description="Name of the model")
    use_helm: bool = Field(..., description="Using HELM vs. Non-Helm")

class MessageInputData(BaseModel):
    message_id: str
    new_input_data: str


class MessageData(BaseModel):
    message_id: str


class UpdateInteractiveModeInput(BaseModel):
    interactive: bool


class ApiKeyInput(BaseModel):
    api_key_name: str
    api_key_value: str
