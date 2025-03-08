from typing import List, Optional, Tuple
from unittest.mock import MagicMock

import pytest

from agents.agent_manager import AgentManager
from agents.base_agent import AgentConfig, BaseAgent
from messages.action_messages.answer_message import AnswerMessageInterface
from messages.message import Message
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


def test_phase_config_from_phase(mock_workflow):
    mock_phase = MockPhase(workflow=mock_workflow)
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
def test_base_phase_setup(mock_workflow):
    mock_phase = MockPhase(workflow=mock_workflow)

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


"""
# Test BasePhase.run() - Single iteration
@pytest.mark.asyncio
async def test_base_phase_run_single_iteration(mock_phase, mock_workflow):
    # Mock the workflow message and previous phase message
    mock_phase_message = MagicMock(spec=PhaseMessage)
    mock_phase_message.complete = False
    mock_workflow_message = MagicMock(spec=WorkflowMessage)
    mock_previous_phase_message = MagicMock(spec=PhaseMessage)

    # Mock methods that the `run` method will use
    mock_phase._get_current_iteration = MagicMock(return_value=0)
    mock_phase._get_current_agent = MagicMock(return_value=("agent1", MagicMock(spec=BaseAgent)))
    mock_phase._run_iteration = MagicMock(return_value=MagicMock(spec=AgentMessage))

    # Run the phase
    result = await mock_phase.run(mock_workflow_message, mock_previous_phase_message)

    # Check that the run loop was executed and ended
    mock_phase._run_iteration.assert_called_once()
    assert result == mock_phase_message


# Test BasePhase._handle_interactive_mode()
@pytest.mark.asyncio
async def test_base_phase_handle_interactive_mode(mock_phase, mock_workflow):
    # Simulate that interactive mode is enabled
    mock_phase.phase_config.interactive = True
    mock_workflow.next_iteration_event = MagicMock()

    # Mock the next iteration event behavior
    mock_workflow.next_iteration_event.wait = MagicMock()

    # Run the method to handle interactive mode
    await mock_phase._handle_interactive_mode()

    # Ensure that next_iteration_event.wait() was called
    mock_workflow.next_iteration_event.wait.assert_called_once()


# Test if resources are deallocated
def test_base_phase_deallocate_resources(mock_phase):
    # Mock the resource manager to verify deallocation
    mock_phase.resource_manager.deallocate_phase_resources = MagicMock()

    # Test deallocation
    mock_phase.deallocate_resources()
    mock_phase.resource_manager.deallocate_phase_resources.assert_called_once_with(mock_phase.phase_config.phase_idx)

"""
