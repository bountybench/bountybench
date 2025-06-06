from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from workflows.interactive_controller import IterationType


class StartWorkflowInput(BaseModel):
    workflow_name: str = Field(..., description="Name of the workflow to start")
    task_dir: Path = Field(..., description="Directory of the tasks")
    bounty_number: str = Field(
        ..., description="Bounty number associated with the workflow"
    )
    vulnerability_type: str = Field(..., description="Vulnerability type to detect")
    interactive: bool = Field(
        default=False, description="Whether the workflow is interactive"
    )
    iterations: int = Field(..., gt=0, description="Number of phase iterations")
    model: str = Field(..., description="Name of the model")
    use_mock_model: bool = Field(default=False, description="Mock Model")
    use_cwe: bool = Field(..., description="Using CWE vs. No CWE")
    use_helm: bool = Field(..., description="Using HELM vs. Non-Helm")
    max_input_tokens: Optional[int] = Field(
        None, ge=1, description="Maximum input tokens for the model"
    )
    max_output_tokens: Optional[int] = Field(
        None, ge=1, description="Maximum output tokens for the model"
    )


class MessageInputData(BaseModel):
    message_id: str
    new_input_data: str


class MessageData(BaseModel):
    message_id: str
    num_iter: Optional[int] = 1
    type_iter: Optional[IterationType] = IterationType.AGENT


class UpdateInteractiveModeInput(BaseModel):
    interactive: bool


class ApiKeyInput(BaseModel):
    api_key_name: str
    api_key_value: str


class SaveConfigRequest(BaseModel):
    fileName: str
    config: str
