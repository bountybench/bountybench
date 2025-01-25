import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Importing the necessary classes from your project
from agents.agent_manager import AgentManager
from agents.base_agent import AgentConfig, BaseAgent
from agents.dataclasses.agent_lm_spec import AgentLMConfig
from agents.executor_agent.executor_agent import ExecutorAgent, ExecutorAgentConfig
from messages.message import Message
from phases.base_phase import BasePhase, PhaseConfig
from resources.base_resource import BaseResource, BaseResourceConfig
from resources.resource_manager import ResourceManager

# Mock logger to prevent actual logging during tests
with patch("utils.logger.get_main_logger") as mock_logger:
    mock_logger.return_value = MagicMock()


class TestAgentManager(unittest.TestCase):
    def setUp(self):
        self.agent_manager = AgentManager()

    def test_create_new_agent(self):
        # Create a mock ExecutorAgentConfig

        executor_agent_lm_config = AgentLMConfig(
            model="anthropic/claude-3-5-sonnet-20240620",
            max_output_tokens=100,
            max_input_tokens=100,
            max_iterations_stored_in_memory=3,
            use_helm=True,
        )

        executor_config = ExecutorAgentConfig(
            id="executor_agent",
            lm_config=executor_agent_lm_config,
            # logger=self.workflow_logger,
            target_host="localhost",
        )

        # Mock the ExecutorAgent's run method
        with patch.object(
            ExecutorAgent, "run", return_value=Message("Executed successfully.")
        ) as mock_run:
            agent = self.agent_manager.get_or_create_agent(
                agent_id="executor_agent",
                agent_class=ExecutorAgent,
                config=executor_config,
            )
            self.assertIsInstance(agent, ExecutorAgent)
            self.assertEqual(agent.agent_config.id, "executor_agent")
            mock_run.assert_not_called()  # run should not be called during instantiation

    def test_reuse_existing_agent(self):
        # Create a mock ExecutorAgentConfig
        executor_agent_lm_config_1 = AgentLMConfig(
            model="anthropic/claude-3-5-sonnet-20240620",
            max_output_tokens=100,
            max_input_tokens=100,
            max_iterations_stored_in_memory=3,
            use_helm=True,
        )

        executor_agent_lm_config_2 = AgentLMConfig(
            model="anthropic/claude-3-5-sonnet-20240620",
            max_output_tokens=50,
            max_input_tokens=50,
            max_iterations_stored_in_memory=3,
            use_helm=True,
        )

        executor_config_1 = ExecutorAgentConfig(
            id="executor_agent",
            lm_config=executor_agent_lm_config_1,
            # logger=self.workflow_logger,
            target_host="localhost",
        )

        executor_config_2 = ExecutorAgentConfig(
            id="executor_agent",
            lm_config=executor_agent_lm_config_2,
            # logger=self.workflow_logger,
            target_host="localhost",
        )

        # Mock the ExecutorAgent's run method
        with patch.object(
            ExecutorAgent, "run", return_value=Message("Executed successfully.")
        ) as mock_run:
            agent1 = self.agent_manager.get_or_create_agent(
                agent_id="executor_agent",
                agent_class=ExecutorAgent,
                config=executor_config_1,
            )
            agent2 = self.agent_manager.get_or_create_agent(
                agent_id="executor_agent",
                agent_class=ExecutorAgent,
                config=executor_config_2,
            )

            self.assertIs(agent1, agent2)
            # Ensure that the agent was initialized with the first config
            self.assertEqual(agent1.agent_config.lm_config.max_output_tokens, 100)
            # The second config should not overwrite the first one
            self.assertNotEqual(agent2.agent_config.lm_config.max_output_tokens, 50)

    def test_register_existing_agent(self):
        # Create a mock ExecutorAgentConfig
        executor_agent_lm_config = AgentLMConfig(
            model="anthropic/claude-3-5-sonnet-20240620",
            max_output_tokens=100,
            max_input_tokens=100,
            max_iterations_stored_in_memory=3,
            use_helm=True,
        )

        executor_config = ExecutorAgentConfig(
            id="executor_agent",
            lm_config=executor_agent_lm_config,
            # logger=self.workflow_logger,
            target_host="localhost",
        )

        # Create a mock agent instance
        mock_agent = ExecutorAgent(
            agent_config=executor_config,
            resource_manager=self.agent_manager.resource_manager,
        )
        mock_agent.run = MagicMock(return_value=Message("Executed successfully."))

        # Register the agent manually
        self.agent_manager.register_agent("executor_agent", mock_agent)

        # Retrieve the agent
        agent = self.agent_manager.get_agent("executor_agent")
        self.assertIs(agent, mock_agent)

    def test_remove_agent(self):
        # Create a mock ExecutorAgentConfig
        executor_agent_lm_config = AgentLMConfig(
            model="anthropic/claude-3-5-sonnet-20240620",
            max_output_tokens=100,
            max_input_tokens=100,
            max_iterations_stored_in_memory=3,
            use_helm=True,
        )

        executor_config = ExecutorAgentConfig(
            id="executor_agent",
            lm_config=executor_agent_lm_config,
            # logger=self.workflow_logger,
            target_host="localhost",
        )
        # Create and register an agent
        agent = self.agent_manager.get_or_create_agent(
            agent_id="executor_agent", agent_class=ExecutorAgent, config=executor_config
        )

        # Remove the agent
        self.agent_manager.remove_agent("executor_agent")
        agent_after_removal = self.agent_manager.get_agent("executor_agent")
        self.assertIsNone(agent_after_removal)


class TestResourceManager(unittest.TestCase):
    def setUp(self):
        self.resource_manager = ResourceManager()

        # Mock resource classes and configurations
        self.MockResource1 = MagicMock(spec=BaseResource)
        self.MockResource2 = MagicMock(spec=BaseResource)
        self.MockConfig1 = MagicMock(spec=BaseResourceConfig)
        self.MockConfig2 = MagicMock(spec=BaseResourceConfig)

        # Register mocked resources using string identifiers as resource_id
        self.resource_manager.register_resource(
            "MockResource1", self.MockResource1, self.MockConfig1
        )
        self.resource_manager.register_resource(
            "MockResource2", self.MockResource2, self.MockConfig2
        )

        # Set up `_phase_resources` and `_resource_lifecycle`
        self.resource_manager._phase_resources = {0: {"MockResource1", "MockResource2"}}
        self.resource_manager._resource_lifecycle = {
            "MockResource1": (0, 1),
            "MockResource2": (0, 1),
        }

    def test_register_resource(self):
        """Test that resources are registered correctly."""
        # Assert that resources are registered as tuples (class, config)
        self.assertIn("MockResource1", self.resource_manager._resource_registration)
        self.assertIn("MockResource2", self.resource_manager._resource_registration)
        self.assertEqual(
            self.resource_manager._resource_registration["MockResource1"],
            (self.MockResource1, self.MockConfig1),
        )
        self.assertEqual(
            self.resource_manager._resource_registration["MockResource2"],
            (self.MockResource2, self.MockConfig2),
        )

    def test_initialize_phase_resources(self):
        """Test resource initialization for a specific phase."""
        # Mock resource initialization
        self.MockResource1.return_value = self.MockResource1
        self.MockResource2.return_value = self.MockResource2

        # Initialize resources for phase 0
        self.resource_manager.initialize_phase_resources(0)

        # Assert resources are initialized
        self.assertIn("MockResource1", self.resource_manager._resources)
        self.assertIn("MockResource2", self.resource_manager._resources)
        self.assertEqual(
            self.resource_manager._resources["MockResource1"], self.MockResource1
        )
        self.assertEqual(
            self.resource_manager._resources["MockResource2"], self.MockResource2
        )

    def test_deallocate_phase_resources(self):
        """Test resource deallocation for a specific phase."""
        # Mock resource initialization
        mock_resource_instance1 = MagicMock()
        mock_resource_instance2 = MagicMock()
        self.resource_manager._resources = {
            self.MockResource1: mock_resource_instance1,
            self.MockResource2: mock_resource_instance2,
        }

        # Set up `_phase_resources` and `_resource_lifecycle`
        self.resource_manager._phase_resources = {
            1: {self.MockResource1, self.MockResource2}
        }
        self.resource_manager._resource_lifecycle = {
            self.MockResource1: (0, 1),
            self.MockResource2: (0, 1),
        }

        # Deallocate resources for phase 1
        self.resource_manager.deallocate_phase_resources(1)

        # Assert that stop() was called and resources were removed
        mock_resource_instance1.stop.assert_called_once()
        mock_resource_instance2.stop.assert_called_once()
        self.assertNotIn(self.MockResource1, self.resource_manager._resources)
        self.assertNotIn(self.MockResource2, self.resource_manager._resources)


class TestBasePhase(unittest.TestCase):
    def setUp(self):
        # Initialize AgentManager with a mocked ResourceManager
        self.agent_manager = AgentManager()
        self.agent_manager.resource_manager = MagicMock()

        # Create mock resources
        self.MockResource1 = MagicMock(spec=BaseResource)
        self.MockResource2 = MagicMock(spec=BaseResource)
        self.MockConfig1 = MagicMock(spec=BaseResourceConfig)
        self.MockConfig2 = MagicMock(spec=BaseResourceConfig)

        # Register mocked resources
        self.agent_manager.resource_manager.register_resource(
            "MockResource1", self.MockResource1, self.MockConfig1
        )
        self.agent_manager.resource_manager.register_resource(
            "MockResource2", self.MockResource2, self.MockConfig2
        )

    def test_phase_initialization_with_agents(self):
        """Test initialization of a phase with agents."""
        # Mock agent configurations
        MockAgentConfig1 = MagicMock()
        MockAgentConfig2 = MagicMock()

        # Define a mock PhaseConfig
        phase_config = PhaseConfig(
            phase_idx=0,
            max_iterations=1,
            agent_configs=[
                ("mock_agent1", MockAgentConfig1),
                ("mock_agent2", MockAgentConfig2),
            ],
            interactive=False,
        )

        # Define a mock phase
        mock_phase = MagicMock(spec=BasePhase)
        mock_phase.phase_config = phase_config

        # Verify agents are initialized correctly
        self.assertEqual(len(phase_config.agent_configs), 2)
        self.assertEqual(phase_config.agent_configs[0][0], "mock_agent1")
        self.assertEqual(phase_config.agent_configs[1][0], "mock_agent2")
        self.assertIsInstance(phase_config.agent_configs[0][1], MagicMock)
        self.assertIsInstance(phase_config.agent_configs[1][1], MagicMock)

    def test_phase_register_resources(self):
        """Test that phase resources are registered correctly."""
        # Mock agent configurations
        MockAgentConfig1 = MagicMock()
        MockAgentConfig2 = MagicMock()

        # Define a mock PhaseConfig
        phase_config = PhaseConfig(
            phase_idx=0,
            max_iterations=1,
            agent_configs=[
                ("mock_agent1", MockAgentConfig1),
                ("mock_agent2", MockAgentConfig2),
            ],
            interactive=False,
        )

        # Define a mock phase
        mock_phase = MagicMock(spec=BasePhase)
        mock_phase.phase_config = phase_config

        # Mock `register_resources` and call it
        mock_phase.register_resources = MagicMock()
        mock_phase.register_resources()

        # Assert `register_resources` was called once
        mock_phase.register_resources.assert_called_once()

    def test_phase_run(self):
        """Test running a phase with mocked agents and resources."""
        # Mock agent and resource manager methods
        self.agent_manager.resource_manager.initialize_phase_resources = MagicMock()
        self.agent_manager.resource_manager.deallocate_phase_resources = MagicMock()

        # Mock agents and their messages
        MockAgent1 = MagicMock()
        MockAgent1.run.return_value = Message("MockAgent1 Message")

        MockAgent2 = MagicMock()
        MockAgent2.run.return_value = Message("MockAgent2 Message")

        # Define a mock PhaseConfig
        phase_config = PhaseConfig(
            phase_idx=0,
            max_iterations=1,
            agent_configs=[("mock_agent1", MockAgent1), ("mock_agent2", MockAgent2)],
            interactive=False,
        )

        # Define a mock phase
        mock_phase = MagicMock(spec=BasePhase)
        mock_phase.phase_config = phase_config
        mock_phase.run_phase.return_value = (Message("Phase Completed"), True)

        # Simulate running the phase
        output, success = mock_phase.run_phase()

        # Assert the phase ran successfully
        mock_phase.run_phase.assert_called_once()
        self.assertEqual(output.message, "Phase Completed")
        self.assertTrue(success)


class TestResourceLifecycle(unittest.TestCase):
    def setUp(self):
        # Initialize ResourceManager
        self.resource_manager = ResourceManager()

        # Create mock resources and configurations
        self.MockResource1 = MagicMock(spec=BaseResource)
        self.MockResource2 = MagicMock(spec=BaseResource)
        self.MockConfig1 = MagicMock(spec=BaseResourceConfig)
        self.MockConfig2 = MagicMock(spec=BaseResourceConfig)

        # Register mocked resources
        self.resource_manager.register_resource(
            "MockResource1", self.MockResource1, self.MockConfig1
        )
        self.resource_manager.register_resource(
            "MockResource2", self.MockResource2, self.MockConfig2
        )

    def test_resource_initialization_and_teardown(self):
        """Test initialization and teardown of resources across phases."""

        # Define mock phases
        class Phase1(BasePhase):
            pass

        class Phase2(BasePhase):
            pass

        # Mock `get_required_resources`
        with (
            patch.object(
                Phase1,
                "get_required_resources",
                return_value={"MockResource1", "MockResource2"},
            ),
            patch.object(
                Phase2, "get_required_resources", return_value={"MockResource2"}
            ),
        ):

            # Compute resource schedule
            self.resource_manager.compute_schedule([Phase1, Phase2])

            # Initialize resources for Phase1 (phase_idx=0)
            self.resource_manager.initialize_phase_resources(0)
            self.assertIn("MockResource1", self.resource_manager._resources)
            self.assertIn("MockResource2", self.resource_manager._resources)

            # Initialize resources for Phase2 (phase_idx=1)
            self.resource_manager.initialize_phase_resources(1)
            self.assertIn("MockResource2", self.resource_manager._resources)

            # Deallocate resources after Phase1
            self.resource_manager.deallocate_phase_resources(0)
            self.assertNotIn("MockResource1", self.resource_manager._resources)
            self.assertIn("MockResource2", self.resource_manager._resources)

            # Deallocate resources after Phase2
            self.resource_manager.deallocate_phase_resources(1)
            self.assertNotIn("MockResource2", self.resource_manager._resources)

    def test_resource_initialization_failure(self):
        """Test behavior when resource initialization fails."""

        # Define a failing resource class
        class FailingResource(BaseResource):
            def __init__(self, resource_id, resource_config):
                raise RuntimeError("Failed to initialize FailingResource")

            def stop(self):
                pass

        # Mock failing resource configuration
        failing_config = MagicMock(spec=BaseResourceConfig)
        self.resource_manager.register_resource(
            "FailingResource", FailingResource, failing_config
        )

        # Define a phase that requires the failing resource
        class PhaseWithFailingResource(BasePhase):
            pass

        with patch.object(
            PhaseWithFailingResource,
            "get_required_resources",
            return_value={"FailingResource"},
        ):
            self.resource_manager.compute_schedule([PhaseWithFailingResource])

            # Attempt to initialize resources for phase_idx=0
            with self.assertRaises(RuntimeError) as context:
                self.resource_manager.initialize_phase_resources(0)

            self.assertIn(
                "Failed to initialize FailingResource", str(context.exception)
            )
            self.assertNotIn("FailingResource", self.resource_manager._resources)


if __name__ == "__main__":
    unittest.main()
