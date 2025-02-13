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
    
    phase_message = await phase.run_phase(workflow_message, prev_phase_message)
    
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
    
    phase_message = await phase.run_phase(workflow_message, prev_phase_message)
    
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
    
    phase_message = await phase.run_phase(workflow_message, prev_phase_message)
    
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
    
    phase_message = await phase.run_phase(workflow_message, prev_phase_message)
    
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

    async def run_phase():
        workflow_message = WorkflowMessage(workflow_name="test_workflow")
        return await phase.run_phase(workflow_message, None)

    task = asyncio.create_task(run_phase())

    for _ in range(3):
        await asyncio.sleep(0.1)
        mock_workflow.next_iteration_event.set()
        mock_workflow.next_iteration_event.clear()

    phase_message = await task

    assert agent.run_count == 3
    assert phase_message.summary == "completed_failure"
    assert len(phase_message.agent_messages) == 4  # Initial prompt + 3 agent messages