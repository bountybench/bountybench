import unittest
from unittest.mock import MagicMock, patch

from agents.base_agent import BaseAgent
from phases.base_phase import BasePhase, PhaseConfig
from resources.base_resource import BaseResource, BaseResourceConfig
from resources.resource_manager import ResourceManager
from responses.response import Response


# A concrete subclass of Response so we can instantiate it
class MockResponse(Response):
    def __init__(self, content="mock response"):
        self.content = content

    def to_dict(self):
        return {"content": self.content}


class MockResourceConfig(BaseResourceConfig):
    pass

class MockResource(BaseResource):
    def stop(self):
        pass

class AnotherMockResource(BaseResource):
    def stop(self):
        pass


class MockAgent(BaseAgent):
    REQUIRED_RESOURCES = [(MockResource, "mock_resource")]
    OPTIONAL_RESOURCES = [(AnotherMockResource, "another_resource")]
    ACCESSIBLE_RESOURCES = [
        (MockResource, "mock_resource"), 
        (AnotherMockResource, "another_resource")
    ]

    def run(self, responses: list) -> Response:
        return MockResponse("mock agent output")


class MockPhase(BasePhase):
    REQUIRED_AGENTS = [MockAgent]

    def run_one_iteration(self, agent_instance, previous_output, iteration_num: int):
        input_responses = []
        if previous_output:
            input_responses.append(previous_output)

        new_response = agent_instance.run(input_responses)
        done = (iteration_num == self.phase_config.max_iterations)
        return new_response, done


@patch("phases.base_phase.workflow_logger")
class TestResourceManagerWorkflow(unittest.TestCase):
    """
    Patching `phases.base_phase.workflow_logger` to avoid the "logger not initialized" error.
    """

    def setUp(self, mock_logger=None):
        # Mock the workflow_logger to avoid initialization errors
        mock_logger = MagicMock()
        mock_logger.phase.return_value.__enter__.return_value = MagicMock()

    def test_resource_allocation_workflow(self, mock_logger):
        """
        Test resource allocation and release across phases with strict agent binding.
        """
        # Mock the logger context manager
        mock_logger.phase.return_value.__enter__.return_value = MagicMock()

        # 1) Create the ResourceManager
        rm = ResourceManager()

        # 2) Register resource definitions
        rm.register_resource("mock_resource", MockResource, MockResourceConfig())
        rm.register_resource("another_resource", AnotherMockResource, MockResourceConfig())

        # --- PHASE 1 ---
        # 3) Create the agent first
        agent1 = MockAgent(resource_manager=rm)

        # 4) Build Phase1 config that includes the agent
        phase1_config = PhaseConfig(
            phase_idx=0,
            phase_name="Phase1",
            max_iterations=2,
            agents=[("mock_agent1", agent1)]
        )

        # 5) Register the phase so ResourceManager knows what resources are needed
        rm.register_phase(phase1_config)

        # 6) Create the phase object with resource_manager
        phase1 = MockPhase(phase_config=phase1_config, resource_manager=rm)

        # 7) Let the phase allocate resources and strictly bind the agent's resources
        phase1.allocate_resources()

        # 8) Run Phase1
        last_output, success_flag = phase1.run_phase()

        # Check resources allocated
        self.assertIn("mock_resource", rm._instances)
        self.assertIn("another_resource", rm._instances)

        # 9) Release Phase1 => no phases active => resources freed
        rm.release_resources_for_phase("Phase1")
        self.assertNotIn("mock_resource", rm._instances)
        self.assertNotIn("another_resource", rm._instances)

        # --- PHASE 2 ---
        agent2 = MockAgent(resource_manager=rm)
        phase2_config = PhaseConfig(
            phase_idx=1,
            phase_name="Phase2",
            max_iterations=1,
            agents=[("mock_agent2", agent2)]
        )
        rm.register_phase(phase2_config)

        # Create the phase
        phase2 = MockPhase(phase_config=phase2_config, resource_manager=rm)

        # Allocate & strictly bind
        phase2.allocate_resources()

        # Run Phase2
        last_output2, success_flag2 = phase2.run_phase()

        # Check resources re-allocated
        self.assertIn("mock_resource", rm._instances)
        self.assertIn("another_resource", rm._instances)

        # Release
        rm.release_resources_for_phase("Phase2")
        self.assertNotIn("mock_resource", rm._instances)
        self.assertNotIn("another_resource", rm._instances)

        rm.stop_all_resources()

        print("Test passed: resource allocation/release.")


if __name__ == "__main__":
    unittest.main()