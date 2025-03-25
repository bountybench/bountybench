from typing import Any, Dict, List, Optional, Tuple, Type

from agents.base_agent import AgentConfig, BaseAgent
from agents.executor_agent.executor_agent import ExecutorAgent
from agents.patch_agent.patch_agent import PatchAgent, PatchAgentConfig
from messages.message import Message
from messages.phase_messages.phase_message import PhaseMessage
from phases.bounty_phase import BountyPhase
from resources.base_resource import BaseResourceConfig
from resources.bounty_setup_resource import BountySetupResourceConfig
from resources.docker_resource import DockerResourceConfig
from resources.init_files_resource import InitFilesResourceConfig
from resources.kali_env_resource import KaliEnvResourceConfig
from resources.memory_resource.memory_resource import MemoryResourceConfig
from resources.model_resource.model_resource import ModelResourceConfig
from resources.repo_setup_resource import RepoSetupResourceConfig
from resources.resource_type import ResourceType
from resources.utils import contains_setup
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
        self.use_agent_exploit: bool = kwargs.get("use_agent_exploit", False)

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
            use_agent_exploit=self.use_agent_exploit,
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

        exploit_files_dir_name = None if self.use_agent_exploit else "exploit_files"

        files_dir_name: str = self.workflow.bounty_metadata.get("files_dir", "codebase")
        vulnerable_commit: str = self.workflow.bounty_metadata.get(
            "vulnerable_commit", "main"
        )

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
                    exploit_files_dir_name=exploit_files_dir_name,
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
                    target_host=self.workflow.repo_metadata["target_host"],
                ),
            ),
            (ResourceType.DOCKER, DockerResourceConfig()),
            (ResourceType.MEMORY, MemoryResourceConfig()),
        ]

        self._add_setup_resources(resource_configs)

        logger.debug("Exiting define_resources for PatchPhase")
        return resource_configs

    def _add_setup_resources(
        self, resource_configs: List[Tuple[ResourceType, BaseResourceConfig]]
    ) -> None:
        """
        Add setup resources to the resource configurations if setup scripts exist.

        Args:
            resource_configs (List[Tuple[DefaultResource, BaseResourceConfig]]): The current resource configurations.
        """
        setup_repo_env_script = self.workflow.task_dir / "setup_repo_env.sh"
        if contains_setup(setup_repo_env_script):
            resource_configs.append(
                (
                    ResourceType.REPO_SETUP,
                    RepoSetupResourceConfig(
                        task_dir=self.workflow.task_dir,
                    ),
                )
            )

        setup_bounty_env_script = (
            self.bounty_dir / "setup_files" / "setup_bounty_env.sh"
        )
        if contains_setup(setup_bounty_env_script):
            resource_configs.append(
                (
                    ResourceType.BOUNTY_SETUP,
                    BountySetupResourceConfig(
                        task_dir=self.workflow.task_dir,
                        bounty_number=self.workflow.bounty_number,
                    ),
                )
            )

    async def run_one_iteration(
        self,
        phase_message: PhaseMessage,
        agent_instance: Any,
        previous_output: Optional[Message],
    ) -> Message:
        """
        Run a single iteration of the PatchPhase.

        This method performs the following steps:
        1. Call the agent with previous_output as input.
        2. If ExecutorAgent produces an AnswerMessageInterface -> hallucination -> finalize & done.
        3. If PatchAgent produces an AnswerMessageInterface -> patch success -> finalize & done.
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
        if self._phase_message:
            message.set_parent(self._phase_message.id)
        if isinstance(agent_instance, PatchAgent):
            if message.success:
                logger.info("Patch Success!")
                phase_message.set_summary("patch_success")
                phase_message.set_complete()
                phase_message.set_success()

        return message
