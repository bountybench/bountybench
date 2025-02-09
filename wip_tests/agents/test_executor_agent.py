import pytest
from unittest.mock import Mock
from agents.executor_agent.executor_agent import ExecutorAgent, ExecutorAgentConfig
from messages.action_messages.command_message import CommandMessage
from messages.agent_messages.executor_agent_message import ExecutorAgentMessage
from resources.kali_env_resource import KaliEnvResource
from resources.model_resource.model_resource import ModelResource
from resources.memory_resource import MemoryResource

@pytest.fixture
def executor_agent():
    agent = ExecutorAgent('test_executor', agent_config=ExecutorAgentConfig())
    agent.kali_env = Mock(spec=KaliEnvResource)
    agent.model = Mock(spec=ModelResource)
    agent.init_files = Mock()
    agent.executor_agent_memory = Mock(spec=MemoryResource)
    return agent

@pytest.mark.asyncio
async def test_run_with_messages(executor_agent):
    """Test run method with input messages"""
    command_msg = CommandMessage("test_id", "command: ls")
    executor_agent.execute = Mock(return_value=command_msg)
    
    await executor_agent.run([command_msg])
    
    executor_agent.execute.assert_called_once()

def test_execute_command_success(executor_agent):
    """Test successful command execution"""
    command = "command: ls"
    command_msg = CommandMessage("test_id", command)
    
    executor_agent.call_lm = Mock(return_value=command_msg)
    executor_agent.kali_env.run = Mock(return_value=command_msg)
    
    agent_msg = ExecutorAgentMessage(agent_id=executor_agent.agent_id, prev=None)
    result = executor_agent.execute(agent_msg)
    
    assert result == command_msg
    executor_agent.call_lm.assert_called_once()
    executor_agent.kali_env.run.assert_called_once_with(command_msg)

def test_call_lm_success(executor_agent):
    """Test successful LM call"""
    expected_response = CommandMessage("test_id", "command: pwd")
    executor_agent.model.run = Mock(return_value=expected_response)
    executor_agent.executor_agent_memory.get_memory = Mock(return_value=None)
    
    result = executor_agent.call_lm()
    
    assert result == expected_response
    executor_agent.model.run.assert_called_once()