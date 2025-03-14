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
async def test_call_lm_max_retries_api_error(executor_agent):
    """Test LM call failing with API errors after MAX_RETRIES attempts"""
    # Mock implementation
    executor_agent.resources.model.run = Mock(side_effect=Exception("API error"))
    executor_agent.resources.executor_agent_memory.get_memory = Mock(return_value=None)
    
    # Set MAX_RETRIES for testing
    import agents.executor_agent.executor_agent as executor_module
    original_max_retries = executor_module.MAX_RETRIES
    executor_module.MAX_RETRIES = 3
    
    try:
        with pytest.raises(Exception) as exc_info:
            await executor_agent.call_lm()
        
        # Verify correct exception message contains error history
        assert "Max retries (3) reached without valid response" in str(exc_info.value)
        assert "API error (attempt 1)" in str(exc_info.value)
        assert "API error (attempt 3)" in str(exc_info.value)
        
        # Verify the model.run was called exactly MAX_RETRIES times
        assert executor_agent.resources.model.run.call_count == 3
    finally:
        # Restore original MAX_RETRIES
        executor_module.MAX_RETRIES = original_max_retries


@pytest.mark.asyncio
async def test_call_lm_parse_errors_return_raw_response(executor_agent):
    """Test LM call succeeding but parse_response failing, returning raw response"""
    # Mock implementations
    action_msg = ActionMessage("test_id", "unparsable format")
    executor_agent.resources.model.run = Mock(return_value=action_msg)
    executor_agent.resources.executor_agent_memory.get_memory = Mock(return_value=None)
    executor_agent.parse_response = Mock(side_effect=Exception("Parse error"))
    
    # Set MAX_RETRIES for testing
    import agents.executor_agent.executor_agent as executor_module
    original_max_retries = executor_module.MAX_RETRIES
    executor_module.MAX_RETRIES = 3
    
    try:
        # Should return the raw response instead of raising exception
        result = await executor_agent.call_lm()
        
        # Verify we got back the last raw response
        assert result is action_msg
        assert "unparsable format" in result.message
        assert "Warning: Could not parse as CommandMessage" in result.message
        assert "Parse error (attempt 3)" in result.message
        
        # Verify the model.run and parse_response were called correct number of times
        assert executor_agent.resources.model.run.call_count == 3
        assert executor_agent.parse_response.call_count == 3
    finally:
        # Restore original MAX_RETRIES
        executor_module.MAX_RETRIES = original_max_retries


@pytest.mark.asyncio
async def test_call_lm_mixed_errors_return_raw_response(executor_agent):
    """Test LM call with mix of API and parsing errors, returning final raw response"""
    # Set up mixed error scenario
    api_error = Exception("API error")
    action_msg1 = ActionMessage("test_id", "first response")
    action_msg2 = ActionMessage("test_id", "second response")
    
    # First call: API error, Second: success but parse error, 
    # Third: success but parse error again
    executor_agent.resources.model.run = Mock(side_effect=[
        api_error, 
        action_msg1,
        action_msg2
    ])
    executor_agent.resources.executor_agent_memory.get_memory = Mock(return_value=None)
    executor_agent.parse_response = Mock(side_effect=Exception("Parse error"))
    
    # Set MAX_RETRIES for testing
    import agents.executor_agent.executor_agent as executor_module
    original_max_retries = executor_module.MAX_RETRIES
    executor_module.MAX_RETRIES = 3
    
    try:
        # Should return the last raw response
        result = await executor_agent.call_lm()
        
        # Verify we got back the last raw response (action_msg2)
        assert result is action_msg2
        assert "second response" in result.message
        assert "Warning: Could not parse as CommandMessage" in result.message
        assert "API error (attempt 1)" in result.message
        assert "Parse error (attempt 2)" in result.message
        assert "Parse error (attempt 3)" in result.message
        
        # Verify correct call counts
        assert executor_agent.resources.model.run.call_count == 3
        assert executor_agent.parse_response.call_count == 2  # Only called when API succeeds
    finally:
        # Restore original MAX_RETRIES
        executor_module.MAX_RETRIES = original_max_retries


@pytest.mark.asyncio
async def test_call_lm_eventual_success(executor_agent):
    """Test LM call succeeding after initial failures"""
    # Mock API responses - first fails, second succeeds
    api_error = Exception("API error")
    action_msg = ActionMessage("test_id", "valid command")
    expected_command_msg = CommandMessage("test_id", "command: ls")
    
    executor_agent.resources.model.run = Mock(side_effect=[api_error, action_msg])
    executor_agent.resources.executor_agent_memory.get_memory = Mock(return_value=None)
    # Parse succeeds on second attempt
    executor_agent.parse_response = Mock(side_effect=[Exception("Parse error"), expected_command_msg])
    
    # We should eventually get the successfully parsed command
    result = await executor_agent.call_lm()
    
    assert result is expected_command_msg
    assert executor_agent.resources.model.run.call_count == 2
    assert executor_agent.parse_response.call_count == 1


@pytest.mark.asyncio
async def test_call_lm_success_on_last_retry(executor_agent):
    """Test LM call succeeding on final retry attempt"""
    # First two API calls fail, third succeeds and parses correctly
    api_error = Exception("API error")
    action_msg = ActionMessage("test_id", "valid command")
    expected_command_msg = CommandMessage("test_id", "command: ls")
    
    # Set MAX_RETRIES for testing
    import agents.executor_agent.executor_agent as executor_module
    original_max_retries = executor_module.MAX_RETRIES
    executor_module.MAX_RETRIES = 3
    
    try:
        executor_agent.resources.model.run = Mock(side_effect=[api_error, api_error, action_msg])
        executor_agent.resources.executor_agent_memory.get_memory = Mock(return_value=None)
        executor_agent.parse_response = Mock(return_value=expected_command_msg)
        
        # Should succeed on the last try
        result = await executor_agent.call_lm()
        
        assert result is expected_command_msg
        assert executor_agent.resources.model.run.call_count == 3
        assert executor_agent.parse_response.call_count == 1
    finally:
        # Restore original MAX_RETRIES
        executor_module.MAX_RETRIES = original_max_retries


@pytest.mark.asyncio
async def test_non_retryable_error(executor_agent):
    """Test LM call with non-retryable error (4xx)"""
    # Create an exception with status_code attribute
    class ApiError(Exception):
        def __init__(self, message, status_code):
            super().__init__(message)
            self.status_code = status_code
    
    quota_error = ApiError("Rate limit exceeded", 429)
    executor_agent.resources.model.run = Mock(side_effect=quota_error)
    executor_agent.resources.executor_agent_memory.get_memory = Mock(return_value=None)
    
    with pytest.raises(Exception) as exc_info:
        await executor_agent.call_lm()
    
    # Should fail immediately with the non-retryable error
    assert "Non-retryable API error (HTTP 429)" in str(exc_info.value)
    assert executor_agent.resources.model.run.call_count == 1  # Only called once


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
