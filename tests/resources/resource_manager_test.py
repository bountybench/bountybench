import unittest
from unittest.mock import MagicMock, patch

from agents.base_agent import BaseAgent
from phases.base_phase import BasePhase, PhaseConfig
from resources.base_resource import BaseResource, BaseResourceConfig
from resources.resource_manager import ResourceManager
from responses.response import Response

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
    REQUIRED_AGENTS = [MockAgent]  # We want at least one MockAgent

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
    We patch `phases.base_phase.workflow_logger` so that calls like
    `with workflow_logger.phase(self)` do not raise initialization errors.
    """

    def setUp(self):
        self.resource_manager = ResourceManager

    def test_resource_allocation_workflow(self, mock_logger):
        """
        Because workflow_logger is patched, any calls to `workflow_logger.phase(...)`
        will not raise RuntimeError.
        """
        # Mock the context manager for the logger
        mock_logger.phase.return_value.__enter__.return_value = MagicMock()

        # 1) Create the ResourceManager
        rm = self.resource_manager()

        # 2) Register resource definitions
        rm.register_resource(
            resource_id="mock_resource", 
            resource_class=MockResource, 
            resource_config=MockResourceConfig()
        )
        rm.register_resource(
            resource_id="another_resource", 
            resource_class=AnotherMockResource, 
            resource_config=MockResourceConfig()
        )

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
        rm.register_phase(phase1_config)

        # 5) Allocate resources for Phase1
        rm.allocate_resources_for_phase("Phase1")

        # 6) Now that they're allocated, let the agent bind them
        agent1.initialize_resources()

        # 7) Run Phase1
        phase1 = MockPhase(phase_config=phase1_config)
        last_output, success_flag = phase1.run_phase()

        # Confirm the resources are allocated
        self.assertIn("mock_resource", rm._instances)
        self.assertIn("another_resource", rm._instances)

        # 8) Release Phase1 => no phases are active, so resources should be freed
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

        rm.allocate_resources_for_phase("Phase2")
        agent2.initialize_resources()

        phase2 = MockPhase(phase_config=phase2_config)
        last_output2, success_flag2 = phase2.run_phase()

        # Check resources re-allocated
        self.assertIn("mock_resource", rm._instances,
            "mock_resource should be re-allocated for Phase2's agent.")
        self.assertIn("another_resource", rm._instances,
            "another_resource should be re-allocated for Phase2's agent.")

        # 13) Release Phase2 => everything freed again
        rm.release_resources_for_phase("Phase2")
        self.assertNotIn("mock_resource", rm._instances)
        self.assertNotIn("another_resource", rm._instances)

        # 14) stop_all_resources (just in case)
        rm.stop_all_resources()

        print("Test passed: resource allocation/release across phases worked as expected.")


if __name__ == "__main__":
    unittest.main()