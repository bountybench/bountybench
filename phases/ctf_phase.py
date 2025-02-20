import os
from typing import Any, Dict, List, Optional, Tuple, Type

from agents.base_agent import AgentConfig, BaseAgent
from agents.executor_agent.executor_agent import ExecutorAgent
from messages.message import Message
from messages.action_messages.answer_message import AnswerMessageInterface
from messages.phase_messages.phase_message import PhaseMessage
from phases.base_phase import BasePhase
from resources.base_resource import BaseResource
from resources.docker_resource import DockerResource, DockerResourceConfig
from resources.init_files_resource import InitFilesResource, InitFilesResourceConfig
from resources.kali_env_resource import KaliEnvResource, KaliEnvResourceConfig
from resources.memory_resource import MemoryResource, MemoryResourceConfig
from resources.model_resource.model_resource import ModelResource, ModelResourceConfig
from resources.setup_resource import SetupResource, SetupResourceConfig
from resources.utils import contains_setup
from utils.logger import get_main_logger
from workflows.base_workflow import BaseWorkflow

logger = get_main_logger(__name__)


class CTFPhase(BasePhase):
    """
    CTFPhase is responsible for attempting to capture the flag in the target system.
    """

    AGENT_CLASSES: List[Type[BaseAgent]] = [ExecutorAgent]

    def __init__(self, workflow: "BaseWorkflow", **kwargs):
        """
        Initialize the CTFPhase.

        Args:
            workflow (BaseWorkflow): The parent workflow.
            **kwargs: Additional keyword arguments.
        """
        self.model: str = kwargs.get("model", "")
        self.helm: Any = kwargs.get("helm")
        self.bounty_number: str = kwargs.get("bounty_number", "")
        self._initial_prompt: str = kwargs.get("initial_prompt", "")
        self.bounty_dir: str = os.path.join("bounties", f"bounty_{self.bounty_number}")
        self.flag = kwargs.get("flag", "")

        super().__init__(workflow, **kwargs)

    def define_agents(self) -> Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]:
        """
        Define the agents required for the CTFPhase.

        Returns:
            Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]: A dictionary mapping agent names to their types and configurations.
        """
        executor_config = AgentConfig()

        return {
            "executor_agent": (ExecutorAgent, executor_config),
        }

    def define_resources(self) -> Dict[str, Tuple[Type[BaseResource], Any]]:
        """
        Define resource classes and their configurations required by the CTFPhase.

        Returns:
            Dict[str, Tuple[Type[BaseResource], Any]]: Mapping of resource_id to (ResourceClass, ResourceConfig).
        """
        files_dir_name: str = self.workflow.bounty_metadata.get("files_dir", "codebase")
        vulnerable_commit: str = self.workflow.bounty_metadata.get(
            "vulnerable_commit", "main"
        )
        tmp_dir_name: str = "tmp"
        tmp_dir: str = os.path.join(self.workflow.task_dir, tmp_dir_name)

        resource_configs: Dict[str, Tuple[Type[BaseResource], Any]] = {
            "model": (ModelResource, ModelResourceConfig.create(model=self.model)),
            "init_files": (
                InitFilesResource,
                InitFilesResourceConfig(
                    task_dir=self.workflow.task_dir,
                    files_dir_name=files_dir_name,
                    tmp_dir_name=tmp_dir_name,
                    bounty_number=self.bounty_number,
                    vulnerable_commit=vulnerable_commit,
                ),
            ),
            "kali_env": (
                KaliEnvResource,
                KaliEnvResourceConfig(
                    task_dir=self.workflow.task_dir,
                    bounty_number=self.workflow.bounty_number,
                    volumes={
                        os.path.abspath(tmp_dir): {"bind": "/app", "mode": "rw"},
                    },
                    target_host=self.workflow.repo_metadata["target_host"],
                ),
            ),
            "docker": (DockerResource, DockerResourceConfig()),
            "executor_agent_memory": (MemoryResource, MemoryResourceConfig()),
        }

        self._add_setup_resources(resource_configs)

        logger.debug(f"Exiting define_resources for ExploitPhase")
        return resource_configs

    def _add_setup_resources(
        self, resource_configs: Dict[str, Tuple[Type[BaseResource], Any]]
    ) -> None:
        """
        Add setup resources to the resource configurations if setup scripts exist.

        Args:
            resource_configs (Dict[str, Tuple[Type[BaseResource], Any]]): The current resource configurations.
        """
        setup_repo_env_script = os.path.join(
            str(self.workflow.task_dir), "setup_repo_env.sh"
        )
        if contains_setup(setup_repo_env_script):
            resource_configs["repo_resource"] = (
                SetupResource,
                SetupResourceConfig(
                    bounty_level_setup=False,
                    task_dir=self.workflow.task_dir,
                ),
            )

        setup_bounty_env_script = os.path.join(
            str(self.workflow.task_dir),
            self.bounty_dir,
            "setup_files",
            "setup_bounty_env.sh",
        )
        if contains_setup(setup_bounty_env_script):
            resource_configs["bounty_resource"] = (
                SetupResource,
                SetupResourceConfig(
                    bounty_level_setup=True,
                    task_dir=self.workflow.task_dir,
                    bounty_number=self.workflow.bounty_number,
                ),
            )

    async def run_one_iteration(
        self,
        phase_message: PhaseMessage,
        agent_instance: Any,
        previous_output: Optional[Message],
    ) -> Message:
        """
        Run a single iteration of the ExploitPhase.

        This method performs the following steps:
        1. Call the agent with the previous_message as input (if any).
        2. If ExecutorAgent produces an AnswerMessageInterface, treat as hallucination -> finalize & done.
        3. If ExploitAgent produces AnswerMessageInterface, treat as exploit success -> finalize & done.
        4. Otherwise continue.

        Args:
            phase_message (PhaseMessage): The current phase message.
            agent_instance (Any): The agent instance to run.
            previous_output (Optional[Message]): The output from the previous iteration.

        Returns:
            Message: The resulting message from the agent.
        """
        input_list: List[Message] = []
        if previous_output is not None:
            input_list.append(previous_output)

        message: Message = await agent_instance.run(input_list)

        if len(message.action_messages) > 0:
            last_action_message = message.action_messages[-1]
            if issubclass(
                last_action_message.__class__, AnswerMessageInterface
            ):
                if last_action_message.answer in self.flag:
                    logger.status("Successfully captured the flag!", True)
                    phase_message.set_summary("exploit_success")
                    phase_message.set_complete()
                    phase_message.set_success()

        return message
