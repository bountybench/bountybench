from agents.base_agent import AgentConfig, BaseAgent
from phase_messages.phase_message import PhaseMessage
from phases.base_phase import BasePhase
from agents.patch_agent.patch_agent import PatchAgent, PatchAgentConfig
from agents.executor_agent.executor_agent import ExecutorAgent, ExecutorAgentConfig
from resources.model_resource import ModelResource, ModelResourceConfig
from resources.base_resource import BaseResource
from resources.init_files_resource import InitFilesResource, InitFilesResourceConfig
from resources.utils import contains_setup
from messages.answer_message import AnswerMessageInterface
from messages.message import Message
from resources.kali_env_resource import KaliEnvResource, KaliEnvResourceConfig
from resources.docker_resource import DockerResource, DockerResourceConfig
from typing import Any, Dict, List, Optional, Tuple, Type
from resources.setup_resource import SetupResource, SetupResourceConfig
import os

from workflows.base_workflow import BaseWorkflow

from utils.logger import get_main_logger

logger = get_main_logger(__name__)

class PatchPhase(BasePhase):
    """Phase responsible for patching vulnerabilities."""
    
    AGENT_CLASSES = [PatchAgent, ExecutorAgent]

    def __init__(self, workflow: 'BaseWorkflow', **kwargs):
        self.model = kwargs.get('model')
        self.bounty_number = kwargs.get('bounty_number')
        self.use_agent_exploit = kwargs.get('use_agent_exploit')
        self.use_verify_script = kwargs.get('use_verify_script')

        super().__init__(workflow, **kwargs)
   
    def define_agents(self) -> Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]:
        # assume we get model through some kwargs situation with the Message
        executor_config = ExecutorAgentConfig()

        patch_config = PatchAgentConfig(
            bounty_dir=os.path.join("bounties", f"bounty_{self.bounty_number}"),
            task_dir=self.workflow.task_dir,
            use_verify_script=self.use_verify_script
        )

        return {"executor_agent": (ExecutorAgent, executor_config),
                "patch_agent": (PatchAgent, patch_config)
        }
    
    def define_resources(self) -> Dict[str, Tuple[Type['BaseResource'], Any]]:
        """
        Define resource classes and their configurations required by the PatchPhase.

        Returns:
            Dict[str, Tuple[Type[BaseResource], Any]]: Mapping of resource_id to (ResourceClass, ResourceConfig).
        """
        logger.debug(f"Entering define_resources for PatchPhase")

        if self.use_agent_exploit: 
            exploit_files_dir_name = None
        else: 
            exploit_files_dir_name = "exploit_files"

        files_dir_name = self.workflow.bounty_metadata.get('files_dir', 'codebase')
        vulnerable_commit = self.workflow.bounty_metadata.get('vulnerable_commit', 'main')
        tmp_dir_name = "tmp"
        tmp_dir = os.path.join(self.workflow.task_dir, tmp_dir_name)

        resource_configs = {
            "model": (
                ModelResource,
                ModelResourceConfig.create(model=self.model)
            ),
            "init_files": (
                InitFilesResource,
                InitFilesResourceConfig(
                    task_dir=self.workflow.task_dir,
                    files_dir_name=files_dir_name,
                    tmp_dir_name=tmp_dir_name,
                    bounty_number=self.bounty_number,
                    exploit_files_dir_name=exploit_files_dir_name,
                    vulnerable_commit=vulnerable_commit
                )
            ),
            "kali_env": (
                KaliEnvResource,
                KaliEnvResourceConfig(
                    task_dir=self.workflow.task_dir,
                    bounty_number=self.workflow.bounty_number,
                    volumes={
                        os.path.abspath(tmp_dir): {"bind": "/app", "mode": "rw"},
                    }, 
                    target_host=self.workflow.repo_metadata["target_host"]
                )
            ),
            "docker": (
                DockerResource,
                DockerResourceConfig()
            )
        }

        setup_repo_env_script = os.path.join(str(self.workflow.task_dir), "setup_repo_env.sh")
        if contains_setup(setup_repo_env_script):
            resource_configs["repo_resource"] = (
                SetupResource,
                SetupResourceConfig(
                    bounty_level_setup=False,
                    task_dir=self.workflow.task_dir,
                )
            )

        setup_bounty_env_script = os.path.join(str(self.workflow.task_dir), "setup_bounty_env.sh")
        if contains_setup(setup_bounty_env_script):
            resource_configs["bounty_resource"] = (
                SetupResource,
                SetupResourceConfig(
                    bounty_level_setup=True,
                    task_dir=self.workflow.task_dir,
                    bounty_number=self.workflow.bounty_number,
                )
            )
            
        logger.debug(f"Exiting define_resources for ExploitPhase")
        return resource_configs


    async def run_one_iteration(
        self,
        phase_message: PhaseMessage,
        agent_instance: Any,
        previous_output: Optional[Message],
    ) -> Message:
        """
        1) Call the agent with previous_output as input.
        2) If ExecutorAgent produces an AnswerMessageInterface -> hallucination -> finalize & done.
        3) If PatchAgent produces an AnswerMessageInterface -> patch success -> finalize & done.
        4) Otherwise continue.
        """
        # Prepare input message list for agent
        input_list = []
        if previous_output is not None:
            input_list.append(previous_output)

        message = await agent_instance.run(input_list)
        phase_message.add_agent_message(message)

        # Determine which agent name was used in this iteration
        _, agent_instance = self._get_current_agent()

        # Check for hallucination (ExecutorAgent)
        if isinstance(agent_instance, ExecutorAgent):
            if isinstance(message, AnswerMessageInterface):
                logger.status("Executor agent hallucinated an answer!")
                self._set_phase_summary("completed_with_hallucination")
                phase_message.set_complete()
                return message

        # Check for exploit success (PatchAgent)
        elif isinstance(agent_instance, PatchAgent):
            if isinstance(message, AnswerMessageInterface):
                logger.info("Patch Success!")
                self._set_phase_summary("patch_success")
                phase_message.set_complete()
                phase_message.set_success()
                return message
        return message
