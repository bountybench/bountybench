from time import sleep
from typing import List

import pytest

from messages.agent_messages.agent_message import AgentMessage
from resources.model_resource.model_provider import ModelProvider
from resources.model_resource.model_resource import ModelResource, ModelResourceConfig
from resources.model_resource.model_response import ModelResponse


class SlowFakeProvider(ModelProvider):
    def create_client(self):
        pass

    def request(
        self,
        model: str,
        message: str,
        temperature: float,
        max_tokens: int,
        stop_sequences: List[str],
    ) -> ModelResponse:
        sleep(10)  # Simulate a long-running request
        return ModelResponse(
            content="This should never return",
            input_tokens=10,
            output_tokens=10,
            time_taken_in_ms=5000,
        )

    def tokenize(self, model: str, message: str) -> List[int]:
        return [1, 2, 3]

    def decode(self, model: str, tokens: List[int]) -> str:
        return "decoded"

    def get_num_tokens(self, model: str, message: str) -> int:
        return 3


class FakeModelResourceConfig(ModelResourceConfig):
    def validate(self):
        pass


def test_model_run_times_out():
    config = FakeModelResourceConfig(
        model="openai/gpt-4",
        use_mock_model=False,
        timeout=5,  # 5 second timeout (since 5 second logging)
    )
    model = ModelResource("test_model", config)
    model.model_provider = SlowFakeProvider()  # Inject our slow provider

    input_message = AgentMessage(agent_id="agent_1", message="Test")
    input_message.memory = "Some test context"

    with pytest.raises(TimeoutError, match="timed out after 5 seconds"):
        model.run(input_message)
