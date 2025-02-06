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
        """Simple implementation that passes through messages"""
        return messages[-1] if messages else AgentMessage(message="")

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
                    bounty_number="test",
                    volumes={
                        os.path.abspath(tmp_dir): {"bind": "/app/workspace", "mode": "rw"}
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
        if previous_output:
            return previous_output
        return AgentMessage(message="")

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
    
    root_logger.setLevel(logging.INFO)
    null_handler = logging.NullHandler()
    root_logger.addHandler(null_handler)
    
    yield
    
    try:
        for handler in root_logger.handlers[:]:
            handler.flush()
            handler.close()
            root_logger.removeHandler(handler)
            
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
        try:
            current_dir = os.getcwd()
            tmp_dir = os.path.join(current_dir, "tmp")
            if os.path.exists(tmp_dir):
                for item in os.listdir(tmp_dir):
                    path = os.path.join(tmp_dir, item)
                    try:
                        if os.path.isfile(path):
                            os.remove(path)
                        elif os.path.isdir(path):
                            import shutil
                            shutil.rmtree(path)
                    except Exception as e:
                        print(f"Error cleaning up {path}: {e}")
        except Exception as e:
            print(f"Error during cleanup: {e}")

    async def test_basic_io(self, workflow: WorkflowForTest):
        """Test basic input/output functionality"""
        workflow._current_phase = workflow._root_phase
        phase_instance = workflow._current_phase.setup()
        kali = workflow.resource_manager.get_resource("kali_env")

        # Test echo command
        cmd = "Command: cd /app/workspace && echo 'test message'"
        result = kali.run(CommandMessage(resource_id="", message=cmd))
        assert "test message" in result.message, "Basic echo command failed"

        # Test file write and read
        cmd = "Command: cd /app/workspace && echo 'test data' > test.txt && cat test.txt"
        result = kali.run(CommandMessage(resource_id="", message=cmd))
        assert "test data" in result.message, "File write/read failed"

    async def test_error_handling(self, workflow: WorkflowForTest):
        """Test error handling for various scenarios"""
        workflow._current_phase = workflow._root_phase
        phase_instance = workflow._current_phase.setup()
        kali = workflow.resource_manager.get_resource("kali_env")

        # Test nonexistent command
        cmd = "Command: cd /app/workspace && nonexistent_cmd"
        result = kali.run(CommandMessage(resource_id="", message=cmd))
        assert "command not found" in result.message.lower() or "not found" in result.message.lower(), \
            "Command not found error not detected"

    async def test_resource_health(self, workflow: WorkflowForTest):
        """Test resource health and functionality"""
        workflow._current_phase = workflow._root_phase
        phase_instance = workflow._current_phase.setup()
        kali = workflow.resource_manager.get_resource("kali_env")

        # Check workspace accessibility
        cmd = "Command: cd /app/workspace && pwd && touch test_file && ls test_file"
        result = kali.run(CommandMessage(resource_id="", message=cmd))
        assert "/app/workspace" in result.message, "Workspace not accessible"
        assert "test_file" in result.message, "File creation failed"