import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from agents.agent_manager import AgentManager
from messages.action_messages.action_message import ActionMessage
from messages.action_messages.command_message import CommandMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.message import Message
from messages.phase_messages.phase_message import PhaseMessage
from messages.rerun_manager import MessageHandler
from messages.workflow_message import WorkflowMessage
from phases.exploit_phase import ExploitPhase
from resources.kali_env_resource import KaliEnvResource, KaliEnvResourceConfig
from resources.resource_manager import ResourceManager
from workflows.exploit_patch_workflow import ExploitPatchWorkflow


@pytest.fixture
def mock_phase_message():
    message = PhaseMessage("test_phase")
    return message


@pytest.fixture
def mock_workflow(rerun_manager):
    workflow = Mock(spec=ExploitPatchWorkflow)
    workflow.name = "TestWorkflow"
    workflow.task = {}
    workflow.workflow_message = WorkflowMessage(workflow_name="TestWorkflow", task={})
    workflow.rerun_manager = rerun_manager

    # Configure mock methods to delegate to rerun_manager
    async def mock_rerun_message(message_id):
        messages = {msg.id: msg for msg in workflow.messages}
        message = messages[message_id]
        return await rerun_manager.rerun(message)

    async def mock_edit_and_rerun(message_id, new_data):
        messages = {msg.id: msg for msg in workflow.messages}
        message = messages[message_id]
        edited = await rerun_manager.edit_message(message, new_data)
        if edited.next:
            rerun_result = await rerun_manager.rerun(edited)
            rerun_result.set_version_prev(edited)
            rerun_result.set_next(edited.next)
            return rerun_result
        return edited

    workflow.rerun_message = AsyncMock(side_effect=mock_rerun_message)
    workflow.edit_and_rerun_message = AsyncMock(side_effect=mock_edit_and_rerun)
    workflow.messages = []

    return workflow


@pytest.fixture
def mock_agent_manager():
    agent_manager = AgentManager()
    agent = AsyncMock()
    agent.run = AsyncMock(return_value=AgentMessage("test_agent", "new agent message"))
    agent_manager.get_agent = Mock(return_value=agent)
    return agent_manager


@pytest.fixture
def test_dir(tmp_path):
    """Create a temporary directory for testing"""
    return tmp_path


@pytest.fixture
def kali_env(test_dir):
    """Setup real KaliEnv resource"""
    config = KaliEnvResourceConfig(
        task_dir=str(test_dir),
        bounty_number="0",
        volumes={
            str(test_dir): {"bind": "/app", "mode": "rw"},
        },
    )
    return KaliEnvResource("kali_env", config)


@pytest.fixture
def resource_manager(kali_env):
    """Setup resource manager with mixed mock and real resources"""
    manager = ResourceManager()
    # Add the kali_env resource
    manager._resources.id_to_resource["kali_env"] = kali_env
    # Setup mock for other resources
    mock_resource = Mock()
    mock_resource.run = Mock(return_value=ActionMessage("test_resource", "new message"))
    manager.get_resource = Mock(
        side_effect=lambda rid: kali_env if rid == "kali_env" else mock_resource
    )
    return manager


@pytest.fixture
def rerun_manager(mock_agent_manager, resource_manager):
    return MessageHandler(mock_agent_manager, resource_manager)


class TestMessageHandler:

    @pytest.mark.asyncio
    async def test_rerun_action_message(self, rerun_manager):
        """Test direct rerun of action message"""
        action_msg = ActionMessage("test_resource", "test message")
        next_msg = ActionMessage("test_resource", "next message")
        action_msg.set_next(next_msg)

        result = await rerun_manager.rerun(action_msg)
        assert isinstance(result, ActionMessage)
        assert result.message == "new message"

    @pytest.mark.asyncio
    async def test_edit_message_version_chain(self, rerun_manager):
        """Test version chain is maintained after edit"""
        msg = ActionMessage("test_resource", "original")
        edited = await rerun_manager.edit_message(msg, "edited")

        assert edited.version_prev == msg
        assert edited.message == "edited"
        assert msg.version_next == edited

    @pytest.mark.asyncio
    async def test_real_command_rerun(self, rerun_manager, test_dir):
        """Test rerunning real commands with file system effects"""
        # Initial command to create a file
        cmd1 = CommandMessage("kali_env", "Command: echo 'line1' > test.txt")
        result = rerun_manager.resource_manager.get_resource("kali_env").run(cmd1)

        # Verify file was created
        file_path = test_dir / "test.txt"
        assert file_path.exists()
        assert file_path.read_text().strip() == "line1"

        # Edit the command and rerun
        new_cmd = "Command: echo 'edited' >> test.txt"
        edited_msg = await rerun_manager.edit_message(cmd1, new_cmd)
        result = await rerun_manager.rerun(edited_msg)

        # Verify file content includes both lines
        content = file_path.read_text().splitlines()
        assert len(content) == 2
        assert content[0].strip() == "line1"
        assert content[1].strip() == "edited"

    @pytest.mark.asyncio
    async def test_command_chain_rerun(self, rerun_manager, test_dir):
        """Test rerunning a chain of dependent commands"""
        # Setup command chain
        cmd1 = CommandMessage("kali_env", "Command: mkdir -p test_dir")
        cmd2 = CommandMessage("kali_env", "Command: echo 'content' > test_dir/file.txt")
        cmd1.set_next(cmd2)

        # Run initial chain
        kali = rerun_manager.resource_manager.get_resource("kali_env")
        result1 = kali.run(cmd1)
        result2 = kali.run(cmd2)

        # Edit first command and rerun chain
        edit_cmd = "Command: mkdir -p new_dir"
        edited = await rerun_manager.edit_message(cmd1, edit_cmd)
        rerun_result = await rerun_manager.rerun(edited)

        # Verify both directories exist
        assert (test_dir / "test_dir").exists()
        assert (test_dir / "new_dir").exists()
        assert (test_dir / "test_dir" / "file.txt").exists()

    @pytest.mark.asyncio
    async def test_rerun_no_next_message(self, rerun_manager):
        """Test error when rerunning message with no next"""
        msg = ActionMessage("test_resource", "test")  # No next message set

        with pytest.raises(ValueError, match="No defined next actions to run"):
            await rerun_manager.rerun(msg)
