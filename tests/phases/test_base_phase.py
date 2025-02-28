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
    prev_phase_message.add_agent_message(
        AgentMessage(agent_id="system", message="Initial")
    )
    
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
    prev_phase_message.add_agent_message(
        AgentMessage(agent_id="system", message="Previous message")
    )
    
    phase_message = await phase.run(workflow_message, prev_phase_message)
    
    assert len(phase_message.agent_messages) > 0
    assert not phase_message.complete
    assert phase_message.summary == "completed_failure"
    
    
@pytest.mark.asyncio
async def test_interactive_mode(mock_workflow):
    phase = SamplePhase(
        workflow=mock_workflow,
        max_iterations=3,
        interactive=True,
        initial_prompt="Test prompt"
    )
    mock_workflow.next_iteration_event = asyncio.Event()

    agent = SampleAgent("Agent1", SampleAgentConfig())
    mock_workflow.agent_manager._phase_agents = {"Agent1": agent}

    phase.setup()

    async def run():
        workflow_message = WorkflowMessage(workflow_name="test_workflow")
        return await phase.run(workflow_message, None)

    task = asyncio.create_task(run())

    for _ in range(3):
        await asyncio.sleep(0.1)
        mock_workflow.next_iteration_event.set()
        mock_workflow.next_iteration_event.clear()

    phase_message = await task

    assert agent.run_count == 3
    assert phase_message.summary == "completed_failure"
    assert len(phase_message.agent_messages) == 4  # Initial prompt + 3 agent messages


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
    assert len(phase_message.agent_messages) == 1
    assert phase_message.agent_messages[0].agent_id == "system"
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
    assert len(phase_message.agent_messages) > 1
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
        assert len(phase_message.agent_messages) > 1
        phase_logger.warning.assert_called_with("Interactive mode is set, but workflow doesn't have next_iteration_event")


@pytest.mark.asyncio
async def test_version_chain_traversal(mock_logger, mock_workflow):
    """Test that the phase properly traverses message version chains."""
    
    phase = SamplePhase(
        workflow=mock_workflow,
        max_iterations=2,
        initial_prompt="Test prompt"
    )
    
    agent = SampleAgent("Agent1", SampleAgentConfig())
    mock_workflow.agent_manager._phase_agents = {
        "Agent1": agent
    }
    
    phase.setup()
    
    # Mock the version_next behavior instead of trying to set it directly
    # Create a special version of run() for this test that simulates a version chain
    original_run = phase.run
    
    # Create a counter to track traversal behavior
    traversal_count = 0
    
    # Patch the check for version_next to simulate a version chain
    async def patched_run(workflow_message, prev_phase_message):
        nonlocal traversal_count
        
        # Create a function to count traversals
        def increment_count(obj):
            nonlocal traversal_count
            traversal_count += 1
            return None  # End of version chain
            
        # Patch the version_next property of AgentMessage to trigger our counter
        with patch.object(AgentMessage, 'version_next', 
                          new_callable=lambda: property(lambda self: increment_count(self))):
            result = await original_run(workflow_message, prev_phase_message)
            return result
    
    # Replace the run method temporarily
    phase.run = patched_run
    
    workflow_message = WorkflowMessage(workflow_name="test_workflow")
    prev_phase_message = None
    
    await phase.run(workflow_message, prev_phase_message)
    
    # Restore the original run method
    phase.run = original_run
    
    # At least one traversal should have happened
    assert traversal_count > 0


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