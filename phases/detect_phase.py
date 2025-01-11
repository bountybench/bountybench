from typing import Dict, List, Optional, Tuple, Any, Type
from agents.base_agent import AgentConfig
from agents.dataclasses.agent_lm_spec import AgentLMConfig
from phases.base_phase import BasePhase
from phases.exploit_phase import ExecutorAgentConfig
from messages.message import Message
from messages.answer_message import AnswerMessageInterface
from agents.executor_agent.executor_agent import ExecutorAgent
from utils.logger import get_main_logger
from workflows.base_workflow import BaseWorkflow
from resources.base_resource import BaseResource
from resources.setup_resource import SetupResourceConfig, SetupResource
from resources.init_files_resource import InitFilesResource, InitFilesResourceConfig
from resources.kali_env_resource import KaliEnvResourceConfig, KaliEnvResource
from resources.docker_resource import DockerResourceConfig, DockerResource
import os




logger = get_main_logger(__name__)

class DetectPhase(BasePhase):
    """
    Phase that cycles through:
      - ExecutorAgent
    Checks for answer submission (Executor) to end early.
    """
    AGENT_CLASSES = [ExecutorAgent]

    def __init__(self, workflow: 'BaseWorkflow', **kwargs):
        self.model = kwargs.get('model')
        self.bounty_number = kwargs.get('bounty_number')
        self.initial_prompt = kwargs.get('initial_prompt')
        super().__init__(workflow, **kwargs)

    def define_agents(self) -> List[Tuple[str, AgentConfig]]:
        # assume we get model through some kwargs situation with the Message
        executor_lm_config = AgentLMConfig.create(model=self.model)
        # Create the executor_config
        executor_config = ExecutorAgentConfig(
            lm_config=executor_lm_config,
            target_host=self.workflow.repo_metadata["target_host"],
            initial_prompt=self.initial_prompt 
        )

        return [
            ("ExecutorAgent", executor_config)
        ]
    
    def define_resources(self) -> Dict[str, Tuple[Type['BaseResource'], Any]]:
        """
        Define resource classes and their configurations required by the ExploitPhase.

        Returns:
            Dict[str, Tuple[Type[BaseResource], Any]]: Mapping of resource_id to (ResourceClass, ResourceConfig).
        """
        logger.debug(f"Entering define_resources for ExploitPhase")

        files_dir_name = self.workflow.bounty_metadata.get('files_dir', 'codebase')
        vulnerable_commit = self.workflow.bounty_metadata.get('vulnerable_commit', 'main')
        tmp_dir_name = "tmp"
        tmp_dir = os.path.join(self.workflow.task_dir, tmp_dir_name)

        resource_configs = {
            "init_files": (
                InitFilesResource,
                InitFilesResourceConfig(
                    task_dir=self.workflow.task_dir,
                    files_dir_name=files_dir_name,
                    tmp_dir_name=tmp_dir_name,
                    bounty_number=self.bounty_number,
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
                    }
                )
            )
        }

        setup_repo_env_script = os.path.join(str(self.workflow.task_dir), "setup_repo_env.sh")
        if os.path.exists(setup_repo_env_script):
            resource_configs["repo_resource"] = (
                SetupResource,
                SetupResourceConfig(
                    task_level_setup=False,
                    task_dir=self.workflow.task_dir,
                )
            )

        target_host = self.workflow.repo_metadata.get("target_host")
        if target_host:
            task_server_config = SetupResourceConfig(
                task_level_setup=True,
                task_dir=self.workflow.task_dir,
                bounty_number=self.workflow.bounty_number,
                server_address=target_host
            )
            resource_configs["task_server"] = (SetupResource, task_server_config)

        logger.debug(f"Exiting define_resources for ExploitPhase")
        return resource_configs

    def run_one_iteration(
        self,
        agent_instance: Any,
        previous_output: Optional[Message]
    ) -> Tuple[Message, bool]:
        """
        1) Call the agent with the previous_message as input (if any).
        2) If ExecutorAgent produces an AnswerMessageInterface, treat as answer submission -> finalize & done.
        4) Otherwise continue.
        """
        # Prepare input message list for agent
        input_list = []
        if previous_output is not None:
            input_list.append(previous_output)

        message = agent_instance.run(input_list)

        # Check for answer submission (ExecutorAgent)
        if isinstance(message, AnswerMessageInterface):
            logger.status("Detect successful!", True)
            self._set_phase_summary("detect_success")
            return message, True
            
        # Otherwise, continue looping
        return message, False        