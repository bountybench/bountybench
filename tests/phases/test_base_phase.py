from typing import Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.agent_manager import AgentManager
from agents.base_agent import AgentConfig, BaseAgent
from messages.action_messages.answer_message import AnswerMessageInterface
from messages.agent_messages.agent_message import AgentMessage
from messages.message import Message
from messages.phase_messages.phase_message import PhaseMessage
from messages.workflow_message import WorkflowMessage
from phases.base_phase import BasePhase, PhaseConfig
from resources.base_resource import BaseResourceConfig
from resources.resource_manager import ResourceManager
from resources.resource_type import ResourceType
from workflows.base_workflow import BaseWorkflow


@pytest.fixture
def mock_workflow():
    # Mock the workflow object to simulate its behavior
    workflow_id = "workflow-123"
    workflow = MagicMock(spec=BaseWorkflow)
    workflow.workflow_message = MagicMock(spec=WorkflowMessage)
    workflow.workflow_message.workflow_id = workflow_id
    workflow.agent_manager = MagicMock(spec=AgentManager(workflow_id))
    workflow.resource_manager = MagicMock(spec=ResourceManager(workflow_id))

    workflow.resource_manager.is_resource_equivalent.return_value = False
    return workflow


@pytest.fixture
def mock_phase(mock_workflow):
    mock_phase = MockPhase(mock_workflow)
    return mock_phase


class MockConfig1(AgentConfig):
    pass


class MockConfig2(AgentConfig):
    pass


class MockPhase(BasePhase):
    """
    Mock subclass of BasePhase for testing purposes
    """

    def define_resources(self):
        return [
            (ResourceType.KALI_ENV, BaseResourceConfig()),
            (ResourceType.DOCKER, BaseResourceConfig()),
            (ResourceType.BOUNTY_SETUP, BaseResourceConfig()),
            (ResourceType.INIT_FILES, BaseResourceConfig()),
            (ResourceType.REPO_SETUP, BaseResourceConfig()),
            (ResourceType.MEMORY, BaseResourceConfig()),
        ]

    def define_agents(self):
        return [
            ("agent1", MockConfig1()),
            ("agent2", MockConfig2()),
        ]

    def run_one_iteration(
        self,
        agent_instance: BaseAgent,
        previous_output: Optional[Message],
        iteration_num: int,
    ) -> Tuple[Message, bool]:
        input_list = []
        if previous_output:
            input_list.append(previous_output)

        message = agent_instance.run(input_list)

        if isinstance(message, AnswerMessageInterface):
            # logger.info("SamplePhase success condition met!")
            self._set_phase_summary("completed_success")
            return message, True

        return message, False


def test_phase_config_from_phase(mock_phase):
    kwargs = {"max_iterations": 20, "interactive": True, "extra_param": "value"}
    phase_config = PhaseConfig.from_phase(mock_phase, **kwargs)

    assert phase_config.phase_name == mock_phase.name

    assert phase_config.agent_configs[0][0] == mock_phase.define_agents()[0][0]
    assert type(phase_config.agent_configs[0][1]) == type(
        mock_phase.define_agents()[0][1]
    )
    assert phase_config.agent_configs[1][0] == mock_phase.define_agents()[1][0]
    assert type(phase_config.agent_configs[1][1]) == type(
        mock_phase.define_agents()[1][1]
    )

    assert phase_config.max_iterations == 20
    assert phase_config.interactive is True
    assert phase_config.phase_idx is None

    # Ensure invalid kwargs (like 'extra_param') are ignored
    assert not hasattr(phase_config, "extra_param")


# Test BasePhase.setup()
def test_base_phase_setup(mock_phase):
    # Make sure that the resources are sorted correctly when passed into initialize_phase_resources.
    resource_configs_keys = [
        "init_files",
        "repo_setup",
        "bounty_setup",
        "docker",
        "executor_agent_memory",
        "kali_env_workflow-123",
    ]

    mock_phase.setup()

    mock_phase.resource_manager.register_resource.assert_called()
    assert mock_phase.resource_manager.register_resource.call_count == 6

    mock_phase.resource_manager.initialize_phase_resources.assert_called_once_with(
        mock_phase.phase_config.phase_idx, resource_configs_keys
    )
    mock_phase.resource_manager.initialize_phase_resources.assert_called_once()
    mock_phase.agent_manager.initialize_phase_agents.assert_called_once()


def test_base_phase_resource_init_order(mock_phase):
    order = mock_phase.define_resource_init_order()
    assert order[ResourceType.INIT_FILES] == 0
    assert order[ResourceType.REPO_SETUP] == 1
    assert order[ResourceType.BOUNTY_SETUP] == 2
    assert order[ResourceType.DOCKER] == 3
    assert order[ResourceType.MEMORY] == 3
    assert order[ResourceType.KALI_ENV] == 4


def test_phase_rshift_operator(mock_workflow):
    """Test that the `>>` operator correctly links phases in the workflow."""

    # Mock workflow with a phase graph
    mock_workflow._phase_graph = {}

    # Define register_phase behavior
    def register_phase_mock(phase):
        if phase not in mock_workflow._phase_graph:
            mock_workflow._phase_graph[phase] = []

    mock_workflow.register_phase.side_effect = register_phase_mock

    # Create mock phases
    phase1 = MockPhase(mock_workflow)
    phase2 = MockPhase(mock_workflow)
    phase3 = MockPhase(mock_workflow)

    # Link phases using `>>`
    phase1 >> phase2 >> phase3

    # Assertions
    assert phase1 in mock_workflow._phase_graph, "Phase 1 should be registered."
    assert phase2 in mock_workflow._phase_graph, "Phase 2 should be registered."
    assert phase3 in mock_workflow._phase_graph, "Phase 3 should be registered."

    assert (
        phase2 in mock_workflow._phase_graph[phase1]
    ), "Phase 1 should link to Phase 2."
    assert (
        phase3 in mock_workflow._phase_graph[phase2]
    ), "Phase 2 should link to Phase 3."
    assert (
        mock_workflow._phase_graph[phase3] == []
    ), "Phase 3 should have no next phases."


@pytest.mark.asyncio
async def test_base_phase_run(mock_phase):
    # Mock the workflow message and previous phase message
    mock_phase.params["initial_prompt"] = "Initial Prompt\n"

    mock_workflow_message = MagicMock(spec=WorkflowMessage)
    mock_previous_phase_message = MagicMock(spec=PhaseMessage)

    # Mock methods that the `run` method will use
    mock_phase._get_current_iteration = MagicMock(return_value=0)
    mock_phase._get_current_agent = MagicMock(
        return_value=("agent1", MagicMock(spec=BaseAgent))
    )
    mock_phase._run_iteration = AsyncMock(return_value=MagicMock(spec=AgentMessage))
    mock_phase._finalize_phase = MagicMock()

    # Run the phase
    result = await mock_phase.run(mock_workflow_message, mock_previous_phase_message)

    # Check that the run loop was executed and ended
    mock_phase._run_iteration.assert_called()
    assert mock_phase._run_iteration.call_count == 10  # max iterations is 10
    assert not result.complete
    mock_phase._finalize_phase.assert_called_once()


# Test BasePhase._handle_interactive_mode()
@pytest.mark.asyncio
async def test_base_phase_handle_interactive_mode(mock_phase):
    # Simulate that interactive mode is enabled
    mock_phase.phase_config.interactive = True
    mock_workflow = mock_phase.workflow
    mock_workflow.next_iteration_event = MagicMock()

    # Mock the next iteration event behavior
    mock_workflow.next_iteration_event.wait = AsyncMock()

    # Run the method to handle interactive mode
    await mock_phase._handle_interactive_mode()

    # Ensure that next_iteration_event.wait() was called
    mock_workflow.next_iteration_event.wait.assert_called_once()


# Test if resources are deallocated
def test_base_phase_deallocate_resources_success(mock_phase):
    # Mock the resource manager to verify deallocation
    mock_phase.resource_manager.deallocate_phase_resources = MagicMock()

    # Test deallocation
    mock_phase.deallocate_resources()
    mock_phase.resource_manager.deallocate_phase_resources.assert_called_once_with(
        mock_phase.phase_config.phase_idx
    )


def test_base_phase_deallocate_resources_success(mock_phase):
    """Test successful resource deallocation."""
    mock_phase.resource_manager.deallocate_phase_resources = MagicMock()

    # Test successful deallocation
    mock_phase.deallocate_resources()
    mock_phase.resource_manager.deallocate_phase_resources.assert_called_once_with(
        mock_phase.phase_config.phase_idx
    )


def test_base_phase_deallocate_resources_failure(mock_phase):
    """Test failure during resource deallocation."""
    mock_phase.resource_manager.deallocate_phase_resources = MagicMock(
        side_effect=Exception("Deallocation error")
    )

    with (
        patch("logging.Logger.error") as mock_logger,
        pytest.raises(Exception, match="Deallocation error"),
    ):
        mock_phase.deallocate_resources()

    # Verify the logger was called with the expected message
    mock_logger.assert_called_once()
    expected_message = f"Failed to deallocate resources for phase {mock_phase.phase_config.phase_idx}: Deallocation error"
    mock_logger.assert_any_call(expected_message)


def test_initialize_last_agent_message_with_prev_messages(mock_phase):
    """Test `_initialize_last_agent_message` when previous phase has agent messages."""
    mock_phase._create_initial_agent_message = MagicMock()  # Mock method

    # Mock previous phase message with agent messages
    mock_prev_message = MagicMock()
    mock_prev_message.agent_messages = [
        MagicMock(),
        MagicMock(),
        MagicMock(),
    ]  # List of agent messages

    # Call the method
    mock_phase._initialize_last_agent_message(mock_prev_message)

    # Assert the last agent message is set correctly
    assert mock_phase._last_agent_message == mock_prev_message.agent_messages[-1]

    # Ensure `_create_initial_agent_message` was NOT called
    mock_phase._create_initial_agent_message.assert_not_called()


def test_initialize_last_agent_message_with_no_prev_messages(mock_phase):
    """Test `_initialize_last_agent_message` when no previous agent messages exist."""
    mock_phase._create_initial_agent_message = MagicMock()  # Mock method

    # Mock previous phase message with empty agent messages
    mock_prev_message = MagicMock()
    mock_prev_message.agent_messages = []

    # Call the method
    with patch("logging.Logger.info") as mock_logger:
        mock_phase._initialize_last_agent_message(mock_prev_message)

        # Ensure logger was called with expected message
        mock_logger.assert_called_with("Adding initial prompt to phase")

    # Ensure `_create_initial_agent_message` was called
    mock_phase._create_initial_agent_message.assert_called_once()


def test_create_initial_agent_message(mock_phase):
    """Test `_create_initial_agent_message` initializes the agent message correctly."""
    # Mock BasePhase
    mock_phase.params = {
        "initial_prompt": "Hello, {name}!",
        "name": "Test",
    }  # Sample params
    mock_phase._phase_message = MagicMock()  # Mock phase message

    # Call the method
    mock_phase._create_initial_agent_message()

    # Assertions
    assert mock_phase._last_agent_message is not None, "Agent message should be created"
    assert (
        mock_phase._last_agent_message.agent_id == "system"
    ), "Agent ID should be 'system'"
    assert (
        mock_phase._last_agent_message.message == "Hello, Test!"
    ), "Message should be formatted correctly"
    assert (
        mock_phase._last_agent_message.iteration == -1
    ), "Iteration should be set to -1"

    # Ensure `_phase_message.add_child_message` was called with the new message
    mock_phase._phase_message.add_child_message.assert_called_once_with(
        mock_phase._last_agent_message
    )


@pytest.mark.asyncio
async def test_run_iteration(mock_phase):
    """Test `_run_iteration()` correctly executes an iteration and updates state."""

    # Mock BasePhase
    mock_phase._get_current_iteration = MagicMock(return_value=3)
    mock_phase._get_current_agent = MagicMock(return_value=("agent_1", MagicMock()))
    mock_phase.run_one_iteration = AsyncMock(return_value=MagicMock())
    mock_phase.set_last_agent_message = AsyncMock()
    mock_phase._phase_message = MagicMock()

    # Mock returned agent message
    mock_agent_message = MagicMock()
    mock_phase.run_one_iteration.return_value = mock_agent_message

    # Call async method
    with patch("logging.Logger.info") as mock_logger:
        result = await mock_phase._run_iteration()

        # Ensure logging was called
        mock_logger.assert_any_call("Finished iteration 3 of MockPhase with agent_1")

    # Assertions
    mock_phase._get_current_iteration.assert_called_once()
    mock_phase._get_current_agent.assert_called_once()
    mock_phase.run_one_iteration.assert_awaited_once_with(
        phase_message=mock_phase._phase_message,
        agent_instance=mock_phase._get_current_agent.return_value[1],
        previous_output=mock_phase._last_agent_message,
    )
    mock_agent_message.set_iteration.assert_called_once_with(3)
    mock_phase.set_last_agent_message.assert_awaited_once_with(mock_agent_message)
    mock_phase._phase_message.add_child_message.assert_called_once_with(
        mock_agent_message
    )

    assert result == mock_agent_message, "Returned message should be the agent message"


def test_finalize_phase(mock_phase):
    """Test `_finalize_phase()` updates summary and deallocates resources."""
    mock_phase._phase_message = MagicMock()
    mock_phase._phase_message.summary = "incomplete"
    mock_phase.deallocate_resources = MagicMock()

    # Call the method
    mock_phase._finalize_phase()

    # Check if summary was updated
    assert mock_phase._phase_message.set_summary.called_once_with("completed_failure")

    # Ensure `deallocate_resources()` was called
    mock_phase.deallocate_resources.assert_called_once()


@pytest.mark.parametrize(
    "last_message, expected_iteration",
    [
        (None, 0),  # No message -> iteration 0
        (MagicMock(parent=None, iteration=None), 0),  # Wrong parent, no iteration
        (
            MagicMock(parent=MagicMock(), iteration=None),
            0,
        ),  # Correct parent, but no iteration
        (MagicMock(parent=MagicMock(), iteration=4), 5),  # Valid case, should increment
    ],
)
def test_get_current_iteration(last_message, expected_iteration, mock_phase):
    """Test `_get_current_iteration()` returns the correct iteration count."""
    mock_phase._last_agent_message = last_message
    mock_phase._phase_message = (
        last_message.parent if last_message is not None else MagicMock()
    )

    assert mock_phase._get_current_iteration() == expected_iteration


def test_get_agent_from_message(mock_phase):
    """Test `_get_agent_from_message()` correctly retrieves an agent or warns."""
    mock_phase.agents = [MagicMock(spec=BaseAgent), MagicMock(spec=BaseAgent)]

    mock_message = MagicMock()
    mock_message.iteration = 3  # Should map to index 1

    # Check valid agent retrieval
    agent = mock_phase._get_agent_from_message(mock_message)
    assert agent == mock_phase.agents[1]

    # Check warning case
    mock_message.iteration = None
    with patch("logging.Logger.warning") as mock_logger:
        assert mock_phase._get_agent_from_message(mock_message) is None
        mock_logger.assert_called_once_with(
            f"Message {mock_message} iteration unset or negative"
        )


def test_get_current_agent(mock_phase):
    """Test `_get_current_agent()` returns the correct agent in a round-robin fashion."""
    mock_phase.agents = [
        ("agent1", MagicMock(spec=BaseAgent)),
        ("agent2", MagicMock(spec=BaseAgent)),
    ]
    mock_phase._get_current_iteration = MagicMock(
        return_value=2
    )  # Should select index 0

    agent_id, agent = mock_phase._get_current_agent()
    assert agent == mock_phase.agents[0][1]
    assert agent_id == mock_phase.agents[0][0]


@pytest.mark.asyncio
async def test_set_interactive_mode(mock_phase):
    """Test `set_interactive_mode()` correctly sets interactive mode and logs it."""
    mock_phase.phase_config = MagicMock()

    with patch("logging.Logger.info") as mock_logger:
        await mock_phase.set_interactive_mode(True)

        assert mock_phase.phase_config.interactive is True
        mock_logger.assert_called_with(
            f"Interactive mode for phase {mock_phase.name} set to True"
        )
