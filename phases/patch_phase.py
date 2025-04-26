from typing import Any, Dict, List, Optional, Tuple, Type

from agents.base_agent import AgentConfig, BaseAgent
from agents.executor_agent.executor_agent import ExecutorAgent
from agents.patch_agent.patch_agent import PatchAgent, PatchAgentConfig
from messages.message import Message
from messages.phase_messages.phase_message import PhaseMessage
from phases.bounty_phase import BountyPhase
from phases.phase_utils import get_setup_resources
from resources.base_resource import BaseResourceConfig
from resources.docker_resource import DockerResourceConfig
from resources.init_files_resource import InitFilesResourceConfig
from resources.kali_env_resource import KaliEnvResourceConfig
from resources.memory_resource.memory_resource import MemoryResourceConfig
from resources.model_resource.model_resource import ModelResourceConfig
from resources.resource_type import ResourceType
from utils.logger import get_main_logger
from workflows.base_workflow import BaseWorkflow

logger = get_main_logger(__name__)


class PatchPhase(BountyPhase):
    """Phase responsible for patching vulnerabilities."""

    AGENT_CLASSES: List[Type[BaseAgent]] = [PatchAgent, ExecutorAgent]

    def __init__(self, workflow: "BaseWorkflow", **kwargs):
        """
        Initialize the PatchPhase.

        Args:
            workflow (BaseWorkflow): The parent workflow.
            **kwargs: Additional keyword arguments.
        """

        super().__init__(workflow, **kwargs)

    def define_agents(self) -> Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]:
        """
        Define the agents required for the PatchPhase.

        Returns:
            Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]: A dictionary mapping agent names to their types and configurations.
        """
        executor_config = AgentConfig()

        patch_config = PatchAgentConfig(
            bounty_dir=self.bounty_dir,
            task_dir=self.workflow.task_dir,
            submit=self.submit,
            install_command=self.workflow.repo_metadata.get("install_command"),
        )

        return {
            "executor_agent": (ExecutorAgent, executor_config),
            "patch_agent": (PatchAgent, patch_config),
        }

    def define_resources(self) -> List[Tuple[ResourceType, BaseResourceConfig]]:
        """
        Define resource classes and their configurations required by the PatchPhase.

        Returns:
            List[Tuple[DefaultResource, ResourceConfig]].
        """
        logger.debug("Entering define_resources for PatchPhase")

        files_dir_name: str = self.workflow.bounty_metadata.get("files_dir", "codebase")
        vulnerable_commit: str = self.workflow.bounty_metadata.get(
            "vulnerable_commit", "main"
        )

        target_hosts = [self.workflow.repo_metadata["target_host"]]
        target_hosts.extend(self.workflow.bounty_metadata.get("bounty_setup_hosts", []))

        resource_configs: List[Tuple[ResourceType, BaseResourceConfig]] = [
            (
                ResourceType.MODEL,
                ModelResourceConfig.create(
                    model=self.model,
                    use_helm=self.helm,
                    use_mock_model=self.use_mock_model,
                    max_input_tokens=self.params.get("max_input_tokens"),
                    max_output_tokens=self.params.get("max_output_tokens"),
                ),
            ),
            (
                ResourceType.INIT_FILES,
                InitFilesResourceConfig(
                    task_dir=self.workflow.task_dir,
                    files_dir_name=files_dir_name,
                    tmp_dir=self.tmp_dir,
                    bounty_number=self.bounty_number,
                    output_agent_files_name=self.output_agent_files_name,
                    vulnerable_commit=vulnerable_commit,
                ),
            ),
            (
                ResourceType.KALI_ENV,
                KaliEnvResourceConfig(
                    task_dir=self.workflow.task_dir,
                    bounty_number=self.workflow.bounty_number,
                    volumes={
                        str(self.tmp_dir.resolve()): {"bind": "/app", "mode": "rw"},
                    },
                    target_hosts=target_hosts,
                    install_command=self.workflow.repo_metadata.get("install_command"),
                    is_python=self.workflow.repo_metadata.get("is_python"),
                ),
            ),
            (ResourceType.DOCKER, DockerResourceConfig()),
            (ResourceType.MEMORY, MemoryResourceConfig()),
        ]

        resource_configs += get_setup_resources(
            task_dir=self.workflow.task_dir, bounty_number=self.bounty_number
        )

        logger.debug("Exiting define_resources for PatchPhase")
        return resource_configs

    async def run_one_iteration(
        self,
        phase_message: PhaseMessage,
        agent_instance: Any,
        previous_output: Optional[Message],
    ) -> Message:
        """
        Run a single iteration of the PatchPhase.

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

        if isinstance(agent_instance, PatchAgent):
            if message.submission:
                logger.status("Patch submitted!", message.success)
                phase_message.set_summary("patch_submitted")
                phase_message.set_complete()
            if message.success:
                logger.info("Patch Success!")
                phase_message.set_summary("patch_success")
                phase_message.set_complete()
                phase_message.set_success()

        return message
