from typing import List
from models.model_provider import ModelProvider

from helm.common.authentication import Authentication
from helm.common.request import Request, RequestResult
from helm.common.tokenization_request import (
    DecodeRequest,
    TokenizationRequest,
    TokenizationRequestResult,
)
from helm.proxy.services.remote_service import RemoteService


class HelmModels(ModelProvider):
    def __init__(self):
        self.authentication = Authentication(
            api_key=self._get_env_var("HELM_API_KEY"))
        self.client = self.create_client()

    def create_client(self) -> RemoteService:
        remote_service = RemoteService(
            "https://crfm-models.stanford.edu")
        return remote_service

    def request(self, deployment_name: str, message: str, temperature: float, max_tokens: int, stop_sequences: List[str]):
        if "o1" in str(
            self.agent_config.deployment_name
        ):  # o1 and o1-mini don't have stop argument
            request = Request(
                model=ModelRegistry.get_model(
                    deployment_name=DeploymentName.from_string(
                        self.agent_config.deployment_name
                    )
                ),
                model_deployment=str(self.agent_config.deployment_name),
                prompt=model_input.value,
                # o1 and o1-mini have fixed temperature=1 (see https://platform.openai.com/docs/guides/reasoning)
                temperature=1,
                echo_prompt=False,
                max_tokens=self.task_run_config.max_output_tokens_per_iteration,
            )
        else:
            request = Request(
                model=ModelRegistry.get_model(
                    deployment_name=DeploymentName.from_string(
                        self.agent_config.deployment_name
                    )
                ),
                model_deployment=str(self.agent_config.deployment_name),
                prompt=model_input.value,
                temperature=TEMPERATURE,
                echo_prompt=False,
                max_tokens=self.task_run_config.max_output_tokens_per_iteration,
                stop_sequences=[STOP_TOKEN],
            )
