from pathlib import Path
from typing import List, Optional, Union

from pydantic import BaseModel, Field


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


class SaveConfigRequest(BaseModel):
    fileName: str
    config: str

class TaskConfig(BaseModel):
    task_dir: str = Field(..., description="Directory of the tasks")
    bounty_number: str = Field(
        ..., description="Bounty number associated with the workflow"
    )

class ModelConfig(BaseModel):
    name: str = Field(..., description="Name of the model")
    use_helm: bool = Field(..., description="Using HELM vs. Non-Helm")

class ExperimentConfig(BaseModel):
    workflow_name: str = Field(..., description="Name of the workflow to start")
    tasks: List[TaskConfig]
    models: List[ModelConfig]
    vulnerability_type: Optional[str] = Field(default="", description="Vulnerability type to detect")
    interactive: bool = Field(
        default=False, description="Whether the workflow is interactive"
    )
    phase_iterations: Union[List[int], int] = Field(..., description="Number of phase iterations")
    use_mock_model: bool = Field(default=False, description="Mock Model")
    trials_per_config: int = Field(default=1, description="Number of trials per configuration")
