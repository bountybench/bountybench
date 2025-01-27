from abc import ABC, abstractmethod
import asyncio
import os
from typing import Any, List, Dict, Tuple, Type, Optional
from agents.base_agent import AgentConfig, BaseAgent
from messages.action_messages.command_message import CommandMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.message import Message
from messages.message_utils import edit_message
from messages.phase_messages.phase_message import PhaseMessage
from messages.rerun_manager import RerunManager
from messages.workflow_message import WorkflowMessage
from phases.base_phase import BasePhase
from resources.base_resource import BaseResource
from resources.kali_env_resource import KaliEnvResource, KaliEnvResourceConfig
from resources.resource_manager import ResourceManager
from agents.agent_manager import AgentManager

from utils.logger import logger
from workflows.base_workflow import BaseWorkflow

class TestKaliAgent(BaseAgent):
    REQUIRED_RESOURCES = [
        (KaliEnvResource, "kali_env"),
    ]
    ACCESSIBLE_RESOURCES = [
        (KaliEnvResource, "kali_env"),
    ]

    async def run(self, messages: List[AgentMessage]) -> AgentMessage:
        pass

class KaliPhase(BasePhase):
    AGENT_CLASSES = [TestKaliAgent]

    def define_agents(self) -> Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]:
        # Create the executor_config
        kali_config = AgentConfig()

        return {"kali_agent": (TestKaliAgent, kali_config)
        }
    
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
                    }, 
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
    
class TestWorkflow(BaseWorkflow):
    def __init__(self, **kwargs):
        logger.info(f"Initializing workflow {self.name}")
        self.workflow_id = self.name
        self.params = kwargs
        self.interactive = kwargs.get('interactive', False)
        if kwargs.get("phase_iterations"):
            self.phase_iterations = kwargs.get("phase_iterations")
            
        self.max_iterations = 25
        self._current_phase_idx = 0
        self._workflow_iteration_count = 0
        self._phase_graph = {}  # Stores phase relationships
        self._root_phase = None
        self._current_phase = None
        
        # self.initial_prompt=self._get_initial_prompt()

        self.workflow_message = WorkflowMessage.initialize(
            workflow_name=self.name,
            task={},
            additional_metadata={}
        )

        self._setup_resource_manager()
        self._setup_agent_manager()
        self._setup_rerun_manager()
        self._create_phases()
        self._compute_resource_schedule()
        logger.info(f"Finished initializing workflow {self.name}")
        
    def _create_phases(self):
        kali_phase = KaliPhase(workflow=self)
        self._register_root_phase(kali_phase)


    def _get_initial_prompt(self):
        pass

    def _setup_agent_manager(self):
        self.agent_manager = AgentManager()
        logger.info("Setup agent manager")

    def _setup_resource_manager(self):
        self.resource_manager = ResourceManager()
        logger.info("Setup resource manager")

    def _setup_rerun_manager(self):
        self.rerun_manager = RerunManager(self.agent_manager, self.resource_manager)
        logger.info("Setup rerun manager")
        

    async def test_rerun(self):
        self._current_phase = self._root_phase
        phase = self._current_phase

        phase_instance = phase.setup()

        kali = self.resource_manager.get_resource("kali_env")
        command = "Command: echo \"line\" >> file.txt"
        command_message = CommandMessage(resource_id="", message=command)
        message = kali.run(command_message)

        # Read and print file contents
        read_command = "Command: cat file.txt"
        read_message = kali.run(CommandMessage(resource_id="", message=read_command))
        
        print("================================")
        print("Contents of file.txt:")
        print(read_message.message)
        print("================================")

        new_command = "Command: echo \"edited-line\" >> file.txt"
        edited_message = await self.edit_message(command_message, new_command)  # await here
        message = await self.run_edited_message(edited_message)
        print(message.message)

        # Read and print file contents
        read_command = "Command: cat file.txt"
        read_message = kali.run(CommandMessage(resource_id="", message=read_command))
        
        print("================================")
        print("Contents of file.txt:")
        print(read_message.message)
        print("================================")
        message = await self.rerun_message(message)
        
        # Read and print file contents
        read_command = "Command: cat file.txt"
        read_message = kali.run(CommandMessage(resource_id="", message=read_command))
        
        print("================================")
        print("Contents of file.txt:")
        print(read_message.message)
        print("================================")

    async def rerun_message(self, message):
        message = await self.rerun_manager.rerun(message)
        return message
    
    async def run_edited_message(self, message):
        message = await self.rerun_manager.run_edited(message)
        return message
    
if __name__ == "__main__":
    test_workflow = TestWorkflow()
    asyncio.run(test_workflow.test_rerun())
    