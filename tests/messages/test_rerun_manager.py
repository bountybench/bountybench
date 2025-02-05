import pytest
from pytest_asyncio import fixture
import os
import logging
from typing import Any, List, Dict, Tuple, Type, Optional
from agents.base_agent import AgentConfig, BaseAgent
from messages.action_messages.command_message import CommandMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.message import Message
from messages.phase_messages.phase_message import PhaseMessage
from phases.base_phase import BasePhase
from resources.base_resource import BaseResource
from resources.kali_env_resource import KaliEnvResource, KaliEnvResourceConfig
from utils.logger import get_main_logger
from workflows.base_workflow import BaseWorkflow

logger = get_main_logger(__name__)

class KaliAgent(BaseAgent):
    REQUIRED_RESOURCES = [(KaliEnvResource, "kali_env")]
    ACCESSIBLE_RESOURCES = [(KaliEnvResource, "kali_env")]

    async def run(self, messages: List[AgentMessage]) -> AgentMessage:
        pass

class KaliPhase(BasePhase):
    AGENT_CLASSES = [KaliAgent]

    def define_agents(self) -> Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]:
        kali_config = AgentConfig()
        return {"kali_agent": (KaliAgent, kali_config)}
    
    def define_resources(self) -> Dict[str, Tuple[Type['BaseResource'], Any]]:
        current_dir = os.getcwd()
        tmp_dir = os.path.join(current_dir, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        
        return {
            "kali_env": (
                KaliEnvResource,
                KaliEnvResourceConfig(
                    task_dir=tmp_dir,
                    bounty_number="0",
                    volumes={
                        os.path.abspath(tmp_dir): {"bind": "/app", "mode": "rw"},
                    }
                )
            )
        }

    async def run_one_iteration(
        self,
        phase_message: PhaseMessage,
        agent_instance: Any,
        previous_output: Optional[Message]
    ) -> Message:
        pass

class WorkflowForTest(BaseWorkflow):
    def _create_phases(self):
        kali_phase = KaliPhase(workflow=self)
        self._register_root_phase(kali_phase)

    def _get_initial_prompt(self):
        return ""

    def _get_task(self):
        return {}

@pytest.fixture(scope="session", autouse=True)
def manage_logging():
    """Configure logging for tests"""
    root_logger = logging.getLogger()
    original_level = root_logger.level
    original_handlers = root_logger.handlers.copy()
    
    # Configure test logging
    root_logger.setLevel(logging.INFO)
    
    # Use null handler during tests to suppress logs
    null_handler = logging.NullHandler()
    root_logger.addHandler(null_handler)
    
    yield
    
    try:
        # Clean up handlers
        for handler in root_logger.handlers[:]:
            try:
                handler.flush()
                handler.close()
            except:
                pass
            root_logger.removeHandler(handler)
            
        # Restore original config
        root_logger.setLevel(original_level)
        for handler in original_handlers:
            root_logger.addHandler(handler)
    except:
        pass

@pytest.mark.asyncio
class TestRerunManager:
    @fixture
    async def workflow(self) -> WorkflowForTest:
        """Create and setup a workflow instance for testing"""
        test_workflow = WorkflowForTest()
        try:
            yield test_workflow
        finally:
            self._cleanup_tmp_directory()

    def _cleanup_tmp_directory(self):
        """Helper to clean up the temporary directory"""
        if os.path.exists("tmp"):
            try:
                for file in os.listdir("tmp"):
                    os.remove(os.path.join("tmp", file))
                os.rmdir("tmp")
            except Exception:
                pass

    async def test_rerun(self, workflow: WorkflowForTest):
        """Test the rerun functionality of the workflow"""
        # Setup
        workflow._current_phase = workflow._root_phase
        phase_instance = workflow._current_phase.setup()
        kali = workflow.resource_manager.get_resource("kali_env")

        # Test initial command and verify
        command = "Command: echo \"line\" >> file.txt"
        command_message = CommandMessage(resource_id="", message=command)
        message = kali.run(command_message)

        read_command = "Command: cat file.txt"
        read_message = kali.run(CommandMessage(resource_id="", message=read_command))
        assert "line" in read_message.message

        # Test message editing and verify
        new_command = "Command: echo \"edited-line\" >> file.txt"
        edited_message = await workflow.edit_message(command_message, new_command)
        edited_message_id = str(id(edited_message))
        message = await workflow.edit_one_message(edited_message_id, new_command)

        read_message = kali.run(CommandMessage(resource_id="", message=read_command))
        assert "edited-line" in read_message.message

        # Test message rerun and verify
        message_id = str(id(message))
        message = await workflow.rerun_message(message_id)
        read_message = kali.run(CommandMessage(resource_id="", message=read_command))
        assert "edited-line" in read_message.message