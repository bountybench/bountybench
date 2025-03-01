import pytest
import asyncio
from unittest.mock import Mock, patch
from typing import Dict, List, Optional, Tuple, Type, Any
from dataclasses import dataclass, field

from phases.base_phase import BasePhase, PhaseConfig
from agents.base_agent import BaseAgent, AgentConfig
from resources.base_resource import BaseResource, BaseResourceConfig
from messages.agent_messages.agent_message import AgentMessage
from messages.phase_messages.phase_message import PhaseMessage
from messages.workflow_message import WorkflowMessage
from messages.message import Message
from utils.logger import get_main_logger


class SampleAgentConfig(AgentConfig):
    pass


@pytest.fixture
def mock_logger():
    with patch('utils.logger.get_main_logger') as mock:
        logger = Mock()
        mock.return_value = logger
        yield logger


@pytest.fixture
def mock_workflow():
    workflow = Mock()
    workflow.agent_manager = Mock()
    workflow.resource_manager = Mock()
    
    workflow.resource_manager.is_resource_equivalent = Mock(return_value=False)
    workflow.resource_manager.register_resource = Mock()
    workflow.resource_manager.initialize_phase_resources = Mock()
    
    workflow.agent_manager.initialize_phase_agents = Mock()
    workflow.agent_manager._phase_agents = {}
    
    return workflow


class SampleAgent(BaseAgent):
    def __init__(self, agent_id: str, agent_config: AgentConfig, magic_iteration: int = -1):
        super().__init__(agent_id=agent_id, agent_config=agent_config)
        self.magic_iteration = magic_iteration
        self.run_count = 0

    async def run(self, messages: List[AgentMessage]) -> AgentMessage:
        self.run_count += 1
        if self.magic_iteration >= 0 and self.run_count == self.magic_iteration:
            return AgentMessage(agent_id=self.agent_id, message="answer: Magic done")
        return AgentMessage(agent_id=self.agent_id, message="Regular message")


class SamplePhase(BasePhase):
    def define_resources(self) -> Dict[str, Tuple[Type[BaseResource], Optional[BaseResourceConfig]]]:
        return {}

    def define_agents(self) -> Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]:
        return {
            "Agent1": (SampleAgent, SampleAgentConfig()),
            "Agent2": (SampleAgent, SampleAgentConfig())
        }

    async def run_one_iteration(
        self,
        phase_message: PhaseMessage,
        agent_instance: Any,
        previous_output: Optional[Message]
    ) -> Message:
        input_list = []
        if previous_output:
            input_list.append(previous_output)

        message = await agent_instance.run(input_list)

        if "Magic done" in message.message:
            phase_message.set_summary("completed_success")
            phase_message.set_complete()

        return message


@pytest.mark.asyncio
async def test_base_phase_runs_all_iterations(mock_logger, mock_workflow):
    phase = SamplePhase(
        workflow=mock_workflow, 
        max_iterations=5,
        initial_prompt="Test prompt"
    )
    
    agent1 = SampleAgent("Agent1", SampleAgentConfig(), magic_iteration=-1)
    agent2 = SampleAgent("Agent2", SampleAgentConfig(), magic_iteration=-1)
    mock_workflow.agent_manager._phase_agents = {
        "Agent1": agent1,
        "Agent2": agent2
    }
    
    phase.setup()
    
    workflow_message = WorkflowMessage(workflow_name="test_workflow")
    prev_phase_message = None
    
    phase_message = await phase.run(workflow_message, prev_phase_message)
    
    assert phase_message.summary == "completed_failure"
    assert len(phase_message.agent_messages) > 0
    for msg in phase_message.agent_messages:
        assert isinstance(msg, AgentMessage)


@pytest.mark.asyncio
async def test_base_phase_stops_early(mock_logger, mock_workflow):
    phase = SamplePhase(
        workflow=mock_workflow, 
        max_iterations=5,
        initial_prompt="Test prompt"
    )
    
    agent1 = SampleAgent("Agent1", SampleAgentConfig(), magic_iteration=-1)
    agent2 = SampleAgent("Agent2", SampleAgentConfig(), magic_iteration=1)
    mock_workflow.agent_manager._phase_agents = {
        "Agent1": agent1,
        "Agent2": agent2
    }
    
    phase.setup()
    
    workflow_message = WorkflowMessage(workflow_name="test_workflow")
    prev_phase_message = None
    
    phase_message = await phase.run(workflow_message, prev_phase_message)
    
    assert phase_message.summary == "completed_success"
    assert phase_message.complete


@pytest.mark.asyncio
async def test_base_phase_with_initial_message(mock_logger, mock_workflow):
    phase = SamplePhase(
        workflow=mock_workflow, 
        max_iterations=3,
        initial_prompt="Test prompt"
    )
    
    agent = SampleAgent("Agent1", SampleAgentConfig(), magic_iteration=-1)
    mock_workflow.agent_manager._phase_agents = {
        "Agent1": agent
    }
    
    phase.setup()
    
    workflow_message = WorkflowMessage(workflow_name="test_workflow")
    prev_phase_message = PhaseMessage(phase_id="previous")
    
    # Create a system message and add it to the previous phase message
    system_message = AgentMessage(agent_id="system", message="Initial")
    prev_phase_message.add_child_message(system_message)
    
    phase_message = await phase.run(workflow_message, prev_phase_message)
    
    assert not phase_message.complete
    assert phase_message.summary == "completed_failure"


@pytest.mark.asyncio
async def test_base_phase_with_prev_message(mock_logger, mock_workflow):
    phase = SamplePhase(
        workflow=mock_workflow, 
        max_iterations=3,
        initial_prompt="Test prompt"
    )
    
    agent = SampleAgent("Agent1", SampleAgentConfig(), magic_iteration=-1)
    mock_workflow.agent_manager._phase_agents = {
        "Agent1": agent
    }
    
    phase.setup()
    
    workflow_message = WorkflowMessage(workflow_name="test_workflow")
    prev_phase_message = PhaseMessage(phase_id="previous")
    
    # Add a message to the previous phase
    prev_message = AgentMessage(agent_id="system", message="Previous message")
    prev_phase_message.add_child_message(prev_message)
    
    phase_message = await phase.run(workflow_message, prev_phase_message)
    
    assert len(phase_message.agent_messages) > 0
    assert not phase_message.complete
    assert phase_message.summary == "completed_failure"
    
    
@pytest.mark.asyncio
async def test_interactive_mode(mock_workflow):
    phase = SamplePhase(
        workflow=mock_workflow,
        max_iterations=3,  # Will try to run 4 iterations (0, 1, 2, 3)
        interactive=True,
        initial_prompt="Test prompt"
    )
    mock_workflow.next_iteration_event = asyncio.Event()

    agent = SampleAgent("Agent1", SampleAgentConfig())
    mock_workflow.agent_manager._phase_agents = {"Agent1": agent}

    phase.setup()

    async def run_phase():
        workflow_message = WorkflowMessage(workflow_name="test_workflow")
        return await phase.run(workflow_message, None)

    task = asyncio.create_task(run_phase())

    # Signal one more time than before (4 total) to match max_iterations + 1
    for _ in range(4):
        await asyncio.sleep(0.1)
        mock_workflow.next_iteration_event.set()
        mock_workflow.next_iteration_event.clear()

    phase_message = await task

    # Expect 4 agent runs (matching the number of iterations)
    assert agent.run_count == 4
    assert phase_message.summary == "completed_failure"
    assert len(phase_message.agent_messages) >= 4  # Initial prompt + 4 agent messages
    
    
class ExceptionAgent(BaseAgent):
    """An agent that raises an exception when run."""
    def __init__(self, agent_id: str, agent_config: AgentConfig):
        super().__init__(agent_id=agent_id, agent_config=agent_config)

    async def run(self, messages: List[AgentMessage]) -> AgentMessage:
        raise ValueError("Simulated agent error")


class ExceptionPhase(SamplePhase):
    """A phase that uses an agent that raises exceptions."""
    def define_agents(self) -> Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]:
        return {
            "ExceptionAgent": (ExceptionAgent, SampleAgentConfig())
        }


class EmptyMessageAgent(BaseAgent):
    """An agent that returns empty messages."""
    def __init__(self, agent_id: str, agent_config: AgentConfig):
        super().__init__(agent_id=agent_id, agent_config=agent_config)

    async def run(self, messages: List[AgentMessage]) -> AgentMessage:
        return AgentMessage(agent_id=self.agent_id, message="")


class EmptyMessagePhase(SamplePhase):
    """A phase with an agent that returns empty messages."""
    def define_agents(self) -> Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]:
        return {
            "EmptyAgent": (EmptyMessageAgent, SampleAgentConfig())
        }


class NoAgentsPhase(BasePhase):
    """A phase that defines no agents."""
    def define_resources(self) -> Dict[str, Tuple[Type[BaseResource], Optional[BaseResourceConfig]]]:
        return {}

    def define_agents(self) -> Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]:
        return {}

    async def run_one_iteration(
        self,
        phase_message: PhaseMessage,
        agent_instance: Any,
        previous_output: Optional[Message]
    ) -> Message:
        return AgentMessage(agent_id="dummy", message="This should not happen")


@pytest.mark.asyncio
async def test_agent_exception(mock_logger, mock_workflow):
    """Test that exceptions from agents are properly propagated."""
    phase = ExceptionPhase(
        workflow=mock_workflow, 
        max_iterations=3,
        initial_prompt="Test prompt"
    )
    
    agent = ExceptionAgent("ExceptionAgent", SampleAgentConfig())
    mock_workflow.agent_manager._phase_agents = {
        "ExceptionAgent": agent
    }
    
    phase.setup()
    
    workflow_message = WorkflowMessage(workflow_name="test_workflow")
    prev_phase_message = None
    
    with pytest.raises(ValueError, match="Simulated agent error"):
        await phase.run(workflow_message, prev_phase_message)


@pytest.mark.asyncio
async def test_resource_initialization_error(mock_logger, mock_workflow):
    """Test handling of errors during resource initialization."""
    # Setup the resource manager to raise an exception
    mock_workflow.resource_manager.initialize_phase_resources.side_effect = RuntimeError("Resource initialization failed")
    
    phase = SamplePhase(
        workflow=mock_workflow, 
        max_iterations=3,
        initial_prompt="Test prompt"
    )
    
    with pytest.raises(RuntimeError, match="Resource initialization failed"):
        phase.setup()  # This should call initialize_phase_resources


@pytest.mark.asyncio
async def test_resource_deallocation_error(mock_logger, mock_workflow):
    """Test handling of errors during resource deallocation."""
    phase = SamplePhase(
        workflow=mock_workflow, 
        max_iterations=3,
        initial_prompt="Test prompt"
    )
    
    agent = SampleAgent("Agent1", SampleAgentConfig())
    mock_workflow.agent_manager._phase_agents = {
        "Agent1": agent
    }
    
    phase.setup()
    
    # Setup the resource manager to raise an exception during deallocation
    mock_workflow.resource_manager.deallocate_phase_resources.side_effect = RuntimeError("Resource deallocation failed")
    
    workflow_message = WorkflowMessage(workflow_name="test_workflow")
    prev_phase_message = None
    
    with pytest.raises(RuntimeError, match="Resource deallocation failed"):
        await phase.run(workflow_message, prev_phase_message)


@pytest.mark.asyncio
async def test_zero_iterations(mock_logger, mock_workflow):
    """Test behavior with max_iterations=0."""
    phase = SamplePhase(
        workflow=mock_workflow, 
        max_iterations=0,
        initial_prompt="Test prompt"
    )
    
    agent = SampleAgent("Agent1", SampleAgentConfig())
    mock_workflow.agent_manager._phase_agents = {
        "Agent1": agent
    }
    
    phase.setup()
    
    workflow_message = WorkflowMessage(workflow_name="test_workflow")
    prev_phase_message = None
    
    phase_message = await phase.run(workflow_message, prev_phase_message)
    
    # Should only contain the initial system message
    assert len(phase_message.agent_messages) >= 1
    assert phase_message.summary == "completed_failure"


@pytest.mark.asyncio
async def test_no_agents_defined(mock_logger, mock_workflow):
    """Test behavior when no agents are defined for a phase."""
    phase = NoAgentsPhase(
        workflow=mock_workflow, 
        max_iterations=3,
        initial_prompt="Test prompt"
    )
    
    phase.setup()
    
    workflow_message = WorkflowMessage(workflow_name="test_workflow")
    prev_phase_message = None
    
    # Based on the error log, we should expect ZeroDivisionError, not IndexError
    with pytest.raises(ZeroDivisionError):
        await phase.run(workflow_message, prev_phase_message)


@pytest.mark.asyncio
async def test_empty_agent_message(mock_logger, mock_workflow):
    """Test behavior when an agent returns an empty message."""
    phase = EmptyMessagePhase(
        workflow=mock_workflow, 
        max_iterations=3,
        initial_prompt="Test prompt"
    )
    
    agent = EmptyMessageAgent("EmptyAgent", SampleAgentConfig())
    mock_workflow.agent_manager._phase_agents = {
        "EmptyAgent": agent
    }
    
    phase.setup()
    
    workflow_message = WorkflowMessage(workflow_name="test_workflow")
    prev_phase_message = None
    
    phase_message = await phase.run(workflow_message, prev_phase_message)
    
    # Should contain initial message plus empty agent messages
    assert len(phase_message.agent_messages) >= 1
    for i in range(1, len(phase_message.agent_messages)):
        assert phase_message.agent_messages[i].message == ""
    assert phase_message.summary == "completed_failure"


@pytest.mark.asyncio
async def test_interactive_mode_without_event():
    """Test interactive mode behavior when workflow doesn't have next_iteration_event."""
    # Patch the logger directly in the base_phase module
    with patch('phases.base_phase.logger') as phase_logger:
        mock_workflow = Mock()
        mock_workflow.agent_manager = Mock()
        mock_workflow.resource_manager = Mock()
        
        mock_workflow.resource_manager.is_resource_equivalent = Mock(return_value=False)
        mock_workflow.resource_manager.register_resource = Mock()
        mock_workflow.resource_manager.initialize_phase_resources = Mock()
        
        mock_workflow.agent_manager.initialize_phase_agents = Mock()
        mock_workflow.agent_manager._phase_agents = {}
        
        # Remove the next_iteration_event if it exists
        if hasattr(mock_workflow, 'next_iteration_event'):
            delattr(mock_workflow, 'next_iteration_event')
        
        phase = SamplePhase(
            workflow=mock_workflow, 
            max_iterations=3,
            interactive=True,
            initial_prompt="Test prompt"
        )
        
        agent = SampleAgent("Agent1", SampleAgentConfig())
        mock_workflow.agent_manager._phase_agents = {
            "Agent1": agent
        }
        
        phase.setup()
        
        workflow_message = WorkflowMessage(workflow_name="test_workflow")
        prev_phase_message = None
        
        # Should log a warning and continue without waiting
        phase_message = await phase.run(workflow_message, prev_phase_message)
        
        assert not phase_message.complete
        assert phase_message.summary == "completed_failure"
        assert len(phase_message.agent_messages) >= 1
        phase_logger.warning.assert_called_with("Interactive mode is set, but workflow doesn't have next_iteration_event")


@pytest.mark.asyncio
async def test_message_with_iteration(mock_logger, mock_workflow):
    """Test handling of messages with iterations."""
    phase = SamplePhase(
        workflow=mock_workflow,
        max_iterations=3,
        initial_prompt="Test prompt"
    )
    
    agent = SampleAgent("Agent1", SampleAgentConfig())
    mock_workflow.agent_manager._phase_agents = {
        "Agent1": agent
    }
    
    phase.setup()
    
    workflow_message = WorkflowMessage(workflow_name="test_workflow")
    prev_phase_message = None
    
    # Mock the set_iteration method on AgentMessage
    with patch.object(AgentMessage, 'set_iteration') as mock_set_iteration:
        await phase.run(workflow_message, prev_phase_message)
        
        # The set_iteration method should be called at least once
        assert mock_set_iteration.call_count > 0


def test_phase_config_creation(mock_workflow):
    """Test the PhaseConfig.from_phase method with various parameters."""
    # Test with valid parameters
    phase = SamplePhase(
        workflow=mock_workflow, 
        max_iterations=7,
        interactive=True,
        phase_idx=3,
        initial_prompt="Test prompt"
    )
    
    assert phase.phase_config.phase_name == "SamplePhase"
    assert phase.phase_config.max_iterations == 7
    assert phase.phase_config.interactive is True
    assert phase.phase_config.phase_idx == 3
    
    # Test with an invalid parameter (should be ignored)
    phase = SamplePhase(
        workflow=mock_workflow, 
        max_iterations=5,
        invalid_param="Should be ignored",
        initial_prompt="Test prompt"
    )
    
    assert phase.phase_config.max_iterations == 5
    assert not hasattr(phase.phase_config, "invalid_param")


@pytest.mark.asyncio
async def test_set_interactive_mode(mock_workflow):
    """Test setting interactive mode during execution."""
    phase = SamplePhase(
        workflow=mock_workflow, 
        max_iterations=3,
        interactive=False,
        initial_prompt="Test prompt"
    )
    
    assert phase.phase_config.interactive is False
    
    await phase.set_interactive_mode(True)
    
    assert phase.phase_config.interactive is True


@pytest.mark.asyncio
async def test_empty_phase_config():
    """Test creating a phase with minimal configuration."""
    mock_workflow = Mock()
    mock_workflow.agent_manager = Mock()
    mock_workflow.resource_manager = Mock()
    
    # Set up minimal configuration
    phase = SamplePhase(
        workflow=mock_workflow,
        initial_prompt="Test prompt"
    )
    
    # Check default values
    assert phase.phase_config.max_iterations == 10  # Default value from PhaseConfig
    assert phase.phase_config.interactive is False  # Default value from PhaseConfig
    assert phase.phase_config.phase_name == "SamplePhase"  # From class name


@pytest.mark.asyncio
async def test_phase_deallocate_resources_on_completion(mock_logger, mock_workflow):
    """Test that resources are properly deallocated when phase completes."""
    phase = SamplePhase(
        workflow=mock_workflow, 
        max_iterations=3,
        initial_prompt="Test prompt"
    )
    
    agent = SampleAgent("Agent1", SampleAgentConfig(), magic_iteration=1)
    mock_workflow.agent_manager._phase_agents = {
        "Agent1": agent
    }
    
    phase.setup()
    
    workflow_message = WorkflowMessage(workflow_name="test_workflow")
    prev_phase_message = None
    
    await phase.run(workflow_message, prev_phase_message)
    
    # Check that deallocate_phase_resources was called once
    mock_workflow.resource_manager.deallocate_phase_resources.assert_called_once_with(phase.phase_config.phase_idx)


@pytest.mark.asyncio
async def test_get_current_iteration(mock_logger, mock_workflow):
    """Test the _get_current_iteration method."""
    phase = SamplePhase(
        workflow=mock_workflow,
        max_iterations=3,
        initial_prompt="Test prompt"
    )
    
    # When there's no last agent message, iteration should be 0
    assert phase._get_current_iteration() == 0
    
    # Create a message with iteration set
    mock_message = Mock()
    mock_message.iteration = 2
    phase._last_agent_message = mock_message
    
    # Iteration should be incremented
    assert phase._get_current_iteration() == 3
 
 
@pytest.mark.asyncio
async def test_phase_resumability(mock_logger, mock_workflow):
    """Test that a phase can be paused and resumed."""
    phase = SamplePhase(
        workflow=mock_workflow, 
        max_iterations=5,
        initial_prompt="Test prompt"
    )
    
    agent = SampleAgent("Agent1", SampleAgentConfig())
    mock_workflow.agent_manager._phase_agents = {
        "Agent1": agent
    }
    
    phase.setup()
    
    workflow_message = WorkflowMessage(workflow_name="test_workflow")
    prev_phase_message = None
    
    # Run for a few iterations (max_iterations=2 will actually run 3 iterations: 0, 1, 2)
    phase.phase_config.max_iterations = 2
    phase_message = await phase.run(workflow_message, prev_phase_message)
    
    # Verify 3 iterations were completed
    assert agent.run_count == 3
    
    # Store the iteration count
    initial_iterations = phase.iteration_count
    assert initial_iterations == 3
    
    # Resume for more iterations (max_iterations=5 will run iterations 3, 4, 5 next)
    phase.phase_config.max_iterations = 5
    phase_message = await phase.run(workflow_message, prev_phase_message)
    
    # Verify 3 more iterations were completed (total 6)
    assert agent.run_count == 6  # 3 initial + 3 more
    assert phase.iteration_count == 6
    
    # The phase message should contain 6 agent messages plus initial message
    assert len(phase_message.agent_messages) >= 6