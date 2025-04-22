import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from agents.base_agent import IterationFailure
from agents.executor_agent.executor_agent import ExecutorAgent, ExecutorAgentConfig
from messages.action_messages.action_message import ActionMessage
from messages.action_messages.command_message import CommandMessage
from messages.action_messages.error_action_message import ErrorActionMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.executor_agent_message import ExecutorAgentMessage
from messages.message import Message
from resources.kali_env_resource import KaliEnvResource
from resources.memory_resource.memory_resource import MemoryResource
from resources.model_resource.model_resource import ModelResource, ModelResponseFailure


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
    executor_agent.last_executor_agent_message = Mock()
    executor_agent.last_executor_agent_message.add_child_message = Mock()
    executor_agent.resources.model.run = Mock(side_effect=Exception("API error"))
    executor_agent.parse_response = Mock()
    executor_agent.resources.executor_agent_memory.get_memory = Mock(return_value=None)
    executor_agent.parse_response = Mock(return_value=None)

    with pytest.raises(Exception) as exc_info:
        await executor_agent.call_lm()

    assert (
        str(exc_info.value)
        == "call_lm error: Max retries reached without valid response."
    )
    assert executor_agent.resources.model.run.call_count == 3  # MAX_RETRIES
    assert executor_agent.parse_response.call_count == 0


@pytest.mark.asyncio
async def test_call_lm_parse_errors_return_raw_response(executor_agent):
    """Test LM call succeeding but parse_response failing, returning raw response"""
    # Mock implementations
    action_msg = ActionMessage("test_id", "unparsable format")
    executor_agent.resources.model.run = Mock(return_value=action_msg)
    executor_agent.resources.executor_agent_memory.get_memory = Mock(return_value=None)
    executor_agent.parse_response = Mock(side_effect=Exception("Parse error"))
    executor_agent.last_executor_agent_message = AgentMessage("agent_id")

    # Should return the raw response instead of raising exception
    result = await executor_agent.call_lm()

    # Verify we got back the last raw response
    assert not isinstance(result, CommandMessage)

    # Verify the model.run and parse_response were called correct number of times
    assert executor_agent.resources.model.run.call_count == 3
    assert executor_agent.parse_response.call_count == 3


@pytest.mark.asyncio
async def test_call_lm_parse_errors_gets_modified_reminder_prompt(executor_agent):
    """Test LM call succeeding but parse_response failing, returning raw response"""
    # Mock implementations
    action_msg = ActionMessage("test_id", "unparsable format")
    executor_agent.resources.model.run = Mock(return_value=action_msg)
    executor_agent.parse_response = Mock(side_effect=Exception("Parse error"))
    executor_agent.last_executor_agent_message = AgentMessage("agent_id")
    prev_agent_message = AgentMessage("prev_agent_id")
    prev_agent_message.memory = "Hi"
    executor_agent.resources.executor_agent_memory.get_memory = Mock(
        return_value=prev_agent_message
    )

    # Should return the raw response instead of raising exception
    result = await executor_agent.call_lm()

    assert (
        'Make sure to include "Command:" in your response.' in prev_agent_message.memory
    )
    # Verify we got back the last raw response
    assert not isinstance(result, CommandMessage)

    # Verify the model.run and parse_response were called correct number of times
    assert executor_agent.resources.model.run.call_count == 3
    assert executor_agent.parse_response.call_count == 3


@pytest.mark.asyncio
async def test_call_lm_mixed_errors_return_raw_response(executor_agent):
    """Test LM call with mix of API and parsing errors, returning final raw response"""
    # Set up mixed error scenario
    api_error = Exception("API error")
    action_msg1 = ActionMessage("test_id", "first response")
    action_msg2 = ActionMessage("test_id", "second response")
    executor_agent.last_executor_agent_message = AgentMessage("agent_id")

    # First call: API error, Second: success but parse error,
    # Third: success but parse error again
    executor_agent.resources.model.run = Mock(
        side_effect=[api_error, action_msg1, action_msg2]
    )
    executor_agent.resources.executor_agent_memory.get_memory = Mock(return_value=None)
    executor_agent.parse_response = Mock(side_effect=Exception("Parse error"))

    # Should return the last raw response
    result = await executor_agent.call_lm()

    # Verify we got back the last raw response (action_msg2)
    assert result is action_msg2
    assert "second response" in result.message

    # Verify correct call counts
    assert executor_agent.resources.model.run.call_count == 3
    assert (
        executor_agent.parse_response.call_count == 2
    )  # Only called when API succeeds


@pytest.mark.asyncio
async def test_call_lm_eventual_success(executor_agent):
    """Test LM call succeeding after initial failures"""
    executor_agent.last_executor_agent_message = AgentMessage("agent_id")

    # Mock API responses - first fails, second succeeds
    api_error = Exception("API error")
    action_msg = ActionMessage("test_id", "valid command")
    expected_command_msg = CommandMessage("test_id", "command: ls")

    executor_agent.resources.model.run = Mock(
        side_effect=[api_error, action_msg, action_msg]
    )
    executor_agent.resources.executor_agent_memory.get_memory = Mock(return_value=None)
    # Parse succeeds on second attempt
    executor_agent.parse_response = Mock(
        side_effect=[Exception("Parse error"), expected_command_msg]
    )

    # We should eventually get the successfully parsed command
    result = await executor_agent.call_lm()

    assert result is expected_command_msg
    assert executor_agent.resources.model.run.call_count == 3
    assert executor_agent.parse_response.call_count == 2


@pytest.mark.asyncio
async def test_invalid_prompt_error(executor_agent):
    """Test LM call with invalid prompt error (400)"""

    # Create an exception with status_code attribute
    class ApiError(Exception):
        def __init__(self, message, status_code):
            super().__init__(message)
            self.status_code = status_code

    quota_error = ApiError("Invalid prompt", 400)
    executor_agent.resources.model.run = Mock(side_effect=quota_error)
    executor_agent.resources.executor_agent_memory.get_memory = Mock(return_value=None)

    with pytest.raises(Exception) as exc_info:
        await executor_agent.call_lm()

    assert executor_agent.resources.model.run.call_count == 3  # should retry


@pytest.mark.asyncio
async def test_execute_command_success(executor_agent):
    """Test successful command execution"""
    command_msg = CommandMessage("test_id", "command: ls")
    expected_action_msg = ActionMessage("test_id", "command: ls", prev=command_msg)

    executor_agent.call_lm = AsyncMock(return_value=command_msg)
    executor_agent.resources.kali_env.run = Mock(return_value=expected_action_msg)

    executor_agent.last_executor_agent_message = ExecutorAgentMessage(
        agent_id=executor_agent.agent_id, prev=None
    )
    await executor_agent.execute()

    executor_agent.call_lm.assert_called_once()
    executor_agent.resources.kali_env.run.assert_called_once_with(command_msg)
    assert (
        expected_action_msg
        in executor_agent.last_executor_agent_message.action_messages
    )


@pytest.mark.asyncio
async def test_execute_non_command_message(executor_agent):
    """Test execute when call_lm does not returns None"""
    executor_agent.call_lm = AsyncMock(return_value=None)

    executor_agent.last_executor_agent_message = ExecutorAgentMessage(
        agent_id=executor_agent.agent_id, prev=None
    )
    await executor_agent.execute()

    executor_agent.resources.kali_env.run.assert_not_called()

    assert (
        executor_agent.last_executor_agent_message.message
        == "Model failed to produce a valid response."
    )


def test_parse_response_invalid(executor_agent):
    """Test parse_response with invalid message that can't be converted to CommandMessage"""
    action_msg = ActionMessage("test_id", "invalid command format")

    with pytest.raises(Exception) as exc_info:
        executor_agent.parse_response(action_msg)

    assert "Command is missing from message, cannot be a command message." == str(
        exc_info.value
    )


def test_execute_in_env_success(executor_agent):
    """Test successful execution of CommandMessage in Kali environment"""
    command_msg = CommandMessage("test_id", "command: ls")
    expected_action_msg = ActionMessage("test_id", "command: ls", prev=command_msg)
    executor_agent.resources.kali_env.run = Mock(return_value=expected_action_msg)

    result = executor_agent.execute_in_env(command_msg)

    assert isinstance(result, ActionMessage)
    assert result == expected_action_msg


def test_execute_in_env_failure(executor_agent):
    """Test execute_in_env raises and adds ErrorActionMessage to agent message"""
    command_msg = CommandMessage("test_id", "command: invalid")
    executor_agent.resources.kali_env.run = Mock(
        side_effect=Exception("Command failed")
    )

    # Set the last_executor_agent_message to capture added error messages
    executor_agent.last_executor_agent_message = ExecutorAgentMessage(
        agent_id="test_agent"
    )

    with pytest.raises(Exception) as exc_info:
        executor_agent.execute_in_env(command_msg)

    assert "Command failed" in str(exc_info.value)

    # Ensure an ErrorActionMessage was added
    error_messages = executor_agent.last_executor_agent_message.action_messages
    assert len(error_messages) == 1

    error_msg = error_messages[0]
    assert isinstance(error_msg, ErrorActionMessage)
    assert error_msg.prev == command_msg
    assert error_msg.message == "Command failed"
    assert error_msg.error_type == "Exception"
    assert error_msg.resource_id == executor_agent.resources.kali_env.resource_id


@pytest.mark.asyncio
async def test_call_lm_error_history_tracking(executor_agent):
    """Test that error history is properly tracked during retries"""
    # Create API errors with different reasons
    api_error1 = Exception("Rate limit exceeded")
    api_error2 = Exception("Temporary server error")
    action_msg = ActionMessage("test_id", "command: ls")

    executor_agent.resources.model.run = Mock(
        side_effect=[api_error1, api_error2, action_msg]
    )
    executor_agent.resources.executor_agent_memory.get_memory = Mock(return_value=None)

    # Set up last_executor_agent_message
    executor_agent.last_executor_agent_message = ExecutorAgentMessage(
        agent_id=executor_agent.agent_id, prev=None
    )

    result: ActionMessage = await executor_agent.call_lm()

    # Check error history was added to successful response
    assert "error_history" in result.additional_metadata
    error_history = result.additional_metadata["error_history"]
    assert len(error_history) == 2
    assert error_history[0]["type"] == "Exception"
    assert "Rate limit" in error_history[0]["message"]
    assert error_history[1]["type"] == "Exception"
    assert "Temporary server" in error_history[1]["message"]
    assert error_history[0]["attempt"] == 1
    assert error_history[1]["attempt"] == 2


@pytest.mark.asyncio
async def test_call_lm_invalid_prompt_error_retry(executor_agent):
    """Test LM call with Invalid prompt error (400) containing 'Invalid prompt'"""

    # Create an exception with status_code attribute that should be retried
    class ApiError(Exception):
        def __init__(self, message, status_code):
            super().__init__(message)
            self.status_code = status_code

    invalid_prompt_error = ApiError(
        "Invalid prompt: your prompt was flagged as potentially violating our usage policy",
        400,
    )
    model_response_error = ModelResponseFailure(invalid_prompt_error, "test input")
    success_msg = ActionMessage("test_id", "command: ls")

    # First call fails with invalid prompt, second succeeds
    executor_agent.resources.model.run = Mock(
        side_effect=[model_response_error, success_msg]
    )
    executor_agent.resources.executor_agent_memory.get_memory = Mock(return_value=None)

    # Set up last_executor_agent_message
    executor_agent.last_executor_agent_message = ExecutorAgentMessage(
        agent_id=executor_agent.agent_id, prev=None
    )

    prev_agent_message = AgentMessage("prev_agent_id")
    prev_agent_message.memory = ""

    result = await executor_agent.call_lm(prev_agent_message)

    # Verify retry happened and we got a successful result
    assert isinstance(result, CommandMessage)
    assert executor_agent.resources.model.run.call_count == 2

    # Verify error history was recorded
    assert "error_history" in success_msg.additional_metadata
    error_history = success_msg.additional_metadata["error_history"]
    assert len(error_history) == 1
    assert error_history[0]["status_code"] == 400
    assert error_history[0]["input"] == "test input"
    assert "Invalid prompt" in error_history[0]["message"]


@pytest.mark.asyncio
async def test_call_lm_timeout_error(executor_agent):
    """Test LM call with timeout errors"""

    # Set up timeout error
    timeout_error = asyncio.TimeoutError()
    action_msg = ActionMessage("test_id", "command: ls")

    # Patch asyncio.to_thread to simulate timeout
    with patch(
        "asyncio.to_thread", side_effect=[timeout_error, timeout_error, action_msg]
    ):
        executor_agent.resources.model.run = Mock(return_value=action_msg)
        executor_agent.resources.executor_agent_memory.get_memory = Mock(
            return_value=None
        )

        # Set up last_executor_agent_message
        executor_agent.last_executor_agent_message = ExecutorAgentMessage(
            agent_id=executor_agent.agent_id, prev=None
        )

        prev_agent_message = AgentMessage("prev_agent_id")
        prev_agent_message.memory = ""

        result = await executor_agent.call_lm(prev_agent_message)

    # Verify error history contains timeout entries
    assert "error_history" in result.additional_metadata
    error_history = result.additional_metadata["error_history"]
    assert len(error_history) == 2
    assert error_history[0]["type"] == "TimeoutError"
    assert error_history[1]["type"] == "TimeoutError"


@pytest.mark.asyncio
async def test_call_lm_quota_error(executor_agent):
    """Test LM call with quota/rate limit errors that shouldn't be retried"""

    quota_error = Exception("No quota remaining for GPT-4")

    executor_agent.resources.model.run = Mock(side_effect=quota_error)
    executor_agent.resources.executor_agent_memory.get_memory = Mock(return_value=None)

    # Set up last_executor_agent_message
    executor_agent.last_executor_agent_message = ExecutorAgentMessage(
        agent_id=executor_agent.agent_id, prev=None
    )

    with pytest.raises(Exception) as exc_info:
        await executor_agent.call_lm()

    # Verify exception message
    assert "API quota exceeded" in str(exc_info.value)

    # Verify error message was added
    assert len(executor_agent.last_executor_agent_message.action_messages) == 1
    child_msg = executor_agent.last_executor_agent_message.action_messages[0]
    assert isinstance(child_msg, ErrorActionMessage)
    assert child_msg.error_type == "Exception"

    # Check error history
    assert len(child_msg.error_history) == 1
    assert "No quota" in child_msg.error_history[0]["message"]


@pytest.mark.asyncio
async def test_real_world_openai_invalid_prompt_error(executor_agent):
    """Test with a real-world OpenAI invalid prompt error format"""

    # Simulate OpenAI's error format
    openai_error_message = (
        "Error code: 400 - {'error': {'message': 'Invalid prompt: your prompt was flagged as "
        "potentially violating our usage policy. Please try again with a different prompt: "
        "https://platform.openai.com/docs/guides/reasoning#advice-on-prompting', "
        "'type': 'invalid_request_error', 'param': None, 'code': 'invalid_prompt'}}"
    )

    class OpenAIError(Exception):
        def __init__(self, message, status_code):
            super().__init__(message)
            self.status_code = status_code

    openai_error = OpenAIError(openai_error_message, 400)
    action_msg = ActionMessage("test_id", "command: ls")

    executor_agent.resources.model.run = Mock(side_effect=[openai_error, action_msg])
    executor_agent.resources.executor_agent_memory.get_memory = Mock(return_value=None)

    # Set up last_executor_agent_message
    executor_agent.last_executor_agent_message = ExecutorAgentMessage(
        agent_id=executor_agent.agent_id, prev=None
    )

    result = await executor_agent.call_lm()

    # Should retry on invalid prompt and succeed
    assert isinstance(result, CommandMessage)
    assert executor_agent.resources.model.run.call_count == 2

    # Check error history
    assert "error_history" in result.additional_metadata
    error_history = result.additional_metadata["error_history"]
    assert len(error_history) == 1
    assert "Invalid prompt" in error_history[0]["message"]
    assert error_history[0]["status_code"] == 400


@pytest.mark.asyncio
async def test_action_message_add_to_additional_metadata(executor_agent):
    """Test the add_to_additional_metadata method on ActionMessage"""

    message = ActionMessage("test_id", "test message")

    # Add data to additional metadata
    message.add_to_additional_metadata("key1", "value1")
    message.add_to_additional_metadata("key2", {"nested": "data"})

    # Verify values were added
    assert message.additional_metadata["key1"] == "value1"
    assert message.additional_metadata["key2"] == {"nested": "data"}


def test_error_action_message_properties():
    """Test ErrorActionMessage properties work correctly"""

    error_history = [
        {"type": "TimeoutError", "message": "Request timed out", "attempt": 1},
        {"type": "ValueError", "message": "Invalid format", "attempt": 2},
    ]

    error_message = ErrorActionMessage(
        resource_id="test_resource",
        message="An error occurred",
        error_type="TestError",
        error_history=error_history,
        prev=None,
    )

    # Test properties
    assert error_message.error_type == "TestError"
    assert error_message.error_history == error_history
    assert error_message.message == "An error occurred"
    assert error_message.resource_id == "test_resource"


@pytest.mark.asyncio
async def test_run_raises_iteration_failure_on_execute_failure(executor_agent):
    """Test that ExecutorAgent.run raises IterationFailure if execute fails"""
    # Mock failure in execute
    executor_agent.execute = AsyncMock(side_effect=Exception("Execution fail"))

    with pytest.raises(IterationFailure) as exc_info:
        await executor_agent.run([])

    error = exc_info.value
    assert isinstance(error, IterationFailure)
    assert error.agent_message == executor_agent.last_executor_agent_message
    assert isinstance(error.agent_message, ExecutorAgentMessage)
    assert "Execution fail" in str(error)


@pytest.mark.asyncio
async def test_run_raises_iteration_failure_on_call_lm_failure(executor_agent):
    """Test run fails due to call_lm failure inside execute"""
    # Patch call_lm to raise
    executor_agent.call_lm = AsyncMock(side_effect=Exception("LM failed"))
    # Patch execute to call call_lm
    executor_agent.execute = ExecutorAgent.execute.__get__(executor_agent)

    # Create dummy message input
    message = AgentMessage("test_id", "input")

    with pytest.raises(IterationFailure) as exc_info:
        await executor_agent.run([message])

    error = exc_info.value
    assert isinstance(error, IterationFailure)
    assert error.agent_message == executor_agent.last_executor_agent_message
    assert "LM failed" in str(error)


@pytest.mark.asyncio
async def test_run_raises_iteration_failure_on_execute_in_env_failure(executor_agent):
    """Test run fails due to execute_in_env failure"""
    # Create a CommandMessage that passes `issubclass(..., CommandMessageInterface)`
    from messages.action_messages.command_message import CommandMessage

    command_msg = CommandMessage("test_id", "command: ls")

    # Patch call_lm to return a CommandMessage
    executor_agent.call_lm = AsyncMock(return_value=command_msg)

    # Patch execute_in_env to raise
    executor_agent.resources.kali_env.run = Mock(side_effect=Exception("Kali fail"))

    # Run full execute
    executor_agent.execute = ExecutorAgent.execute.__get__(executor_agent)

    message = AgentMessage("test_id", "input")

    with pytest.raises(IterationFailure) as exc_info:
        await executor_agent.run([message])

    error = exc_info.value
    assert isinstance(error, IterationFailure)
    assert error.agent_message == executor_agent.last_executor_agent_message
    assert "Kali fail" in str(error)


@pytest.mark.asyncio
async def test_call_lm_timeout_retries(executor_agent):
    # Patch memory access to return a dummy Message
    executor_agent.last_executor_agent_message = ExecutorAgentMessage(
        agent_id="test_agent"
    )
    executor_agent.last_executor_agent_message.memory = "context"

    # Patch model.run to raise TimeoutError
    executor_agent.resources.model.run = MagicMock(
        side_effect=TimeoutError("Test timeout")
    )

    # Run call_lm and assert it raises after retries
    with pytest.raises(Exception, match="Max retries reached"):
        await executor_agent.call_lm()
