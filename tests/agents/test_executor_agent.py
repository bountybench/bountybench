from unittest.mock import AsyncMock, Mock

import pytest

from agents.executor_agent.executor_agent import ExecutorAgent, ExecutorAgentConfig
from messages.action_messages.action_message import ActionMessage
from messages.action_messages.command_message import CommandMessage
from messages.agent_messages.executor_agent_message import ExecutorAgentMessage
from resources.kali_env_resource import KaliEnvResource
from resources.memory_resource import MemoryResource
from resources.model_resource.model_resource import ModelResource


@pytest.fixture
def executor_agent():
    agent = ExecutorAgent("test_executor", agent_config=ExecutorAgentConfig())
    agent.resources.kali_env = Mock(spec=KaliEnvResource)
    agent.resources.model = Mock(spec=ModelResource)
    agent.resources.init_files = Mock()
    agent.resources.executor_agent_memory = Mock(spec=MemoryResource)
    return agent


@pytest.mark.asyncio
async def test_run_with_input_message(executor_agent):
    """Test run method with an input CommandMessage"""
    action_msg = ActionMessage("test_id", "command: ls")
    executor_agent.execute = AsyncMock(return_value=action_msg)

    command_msg = CommandMessage("test_id", "command: ls")
    await executor_agent.run([command_msg])

    executor_agent.execute.assert_called_once()


@pytest.mark.asyncio
async def test_call_lm_success(executor_agent):
    """Test successful LM call that outputs a CommandMessage"""
    action_msg = ActionMessage("test_id", "command: pwd")
    expected_response = CommandMessage("test_id", "command: pwd")

    executor_agent.resources.model.run = Mock(return_value=action_msg)
    executor_agent.resources.executor_agent_memory.get_memory = Mock(return_value=None)
    executor_agent.parse_response = Mock(return_value=expected_response)

    result = await executor_agent.call_lm()

    assert result == expected_response
    executor_agent.resources.model.run.assert_called_once()
    executor_agent.parse_response.assert_called_once_with(action_msg)


@pytest.mark.asyncio
async def test_call_lm_failure(executor_agent):
    """Test failure of LM call after max retries"""
    executor_agent.resources.model.run = Mock(side_effect=Exception("Parse error"))
    executor_agent.resources.executor_agent_memory.get_memory = Mock(return_value=None)
    executor_agent.parse_response = Mock(return_value=None)

    with pytest.raises(Exception) as exc_info:
        await executor_agent.call_lm()

    assert (
        str(exc_info.value)
        == "call_lm error: Max retries reached without valid response."
    )
    assert executor_agent.resources.model.run.call_count == 3  # MAX_RETRIES


@pytest.mark.asyncio
async def test_execute_command_success(executor_agent):
    """Test successful command execution"""
    command_msg = CommandMessage("test_id", "command: ls")
    expected_action_msg = ActionMessage("test_id", "command: ls", prev=command_msg)

    executor_agent.call_lm = AsyncMock(return_value=command_msg)
    executor_agent.resources.kali_env.run = Mock(return_value=expected_action_msg)

    agent_msg = ExecutorAgentMessage(agent_id=executor_agent.agent_id, prev=None)
    result = await executor_agent.execute(agent_msg)

    assert result == expected_action_msg
    executor_agent.call_lm.assert_called_once()
    executor_agent.resources.kali_env.run.assert_called_once_with(command_msg)


@pytest.mark.asyncio
async def test_execute_non_command_message(executor_agent):
    """Test execute when call_lm does not returns None"""
    executor_agent.call_lm = AsyncMock(return_value=None)

    agent_msg = ExecutorAgentMessage(agent_id=executor_agent.agent_id, prev=None)
    result_executor_agent_message = await executor_agent.execute(agent_msg)

    executor_agent.resources.kali_env.run.assert_not_called()

    assert (
        result_executor_agent_message.message
        == "Model failed to produce a valid response."
    )


def test_parse_response_invalid(executor_agent):
    """Test parse_response with invalid message that can't be converted to CommandMessage"""
    action_msg = ActionMessage("test_id", "invalid command format")

    result = executor_agent.parse_response(action_msg)

    assert isinstance(result, ActionMessage)
    assert "Could not parse response as CommandMessage" in result.message


def test_execute_in_env_success(executor_agent):
    """Test successful execution of CommandMessage in Kali environment"""
    command_msg = CommandMessage("test_id", "command: ls")
    expected_action_msg = ActionMessage("test_id", "command: ls", prev=command_msg)
    executor_agent.resources.kali_env.run = Mock(return_value=expected_action_msg)

    result = executor_agent.execute_in_env(command_msg)

    assert isinstance(result, ActionMessage)
    assert result == expected_action_msg


def test_execute_in_env_failure(executor_agent):
    """Test execute_in_env when command execution fails"""
    command_msg = CommandMessage("test_id", "command: invalid")
    executor_agent.resources.kali_env.run = Mock(
        side_effect=Exception("Command failed")
    )

    result = executor_agent.execute_in_env(command_msg)

    assert isinstance(result, ActionMessage)
    assert "Command failed" in result.message
    assert result.prev == command_msg
