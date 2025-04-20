from typing import Any, Dict, List, Optional, Tuple, Type

from agents.base_agent import AgentConfig, BaseAgent
from agents.detect_agent.detect_agent import DetectAgent, DetectAgentConfig
from agents.executor_agent.executor_agent import ExecutorAgent
from messages.message import Message
from messages.phase_messages.phase_message import PhaseMessage
from phases.bounty_phase import BountyPhase
from resources.base_resource import BaseResourceConfig
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


class DetectPhase(BountyPhase):
    """
    DetectPhase is responsible for attempting to detect vulnerabilities in the target system.
    """

    AGENT_CLASSES: List[Type[BaseAgent]] = [ExecutorAgent, DetectAgent]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "compatible_patches" not in self.workflow.bounty_metadata:
            raise RuntimeError(
                f"Bounty {self.bounty_number} is missing 'compatible_patches' in its metadata. "
                "DetectPhase requires this field to proceed."
            )

    def define_agents(self) -> Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]:
        """
        Define the agents required for the DetectPhase.

        Returns:
            Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]: A dictionary mapping agent names to their types and configurations.
        """
        executor_config = AgentConfig()

        detect_config = DetectAgentConfig(
            bounty_dir=self.bounty_dir,
            task_dir=self.workflow.task_dir,
            tmp_dir=self.tmp_dir,
            submit=self.submit,
            install_command=self.workflow.repo_metadata.get("install_command"),
        )

        return {
            "executor_agent": (ExecutorAgent, executor_config),
            "detect_agent": (DetectAgent, detect_config),
        }

    def define_resources(self) -> List[Tuple[ResourceType, BaseResourceConfig]]:
        """
        Define resource classes and their configurations required by the DetectPhase.

        Returns:
            List[Tuple[DefaultResource, ResourceConfig]].
        """
        files_dir_name: str = self.workflow.bounty_metadata.get("files_dir", "codebase")
        vulnerable_commit: str = self.workflow.bounty_metadata.get(
            "vulnerable_commit", "main"
        )

        target_hosts = [self.workflow.repo_metadata["target_host"]]

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
                    output_agent_files_name=self.output_agent_files_name,
                    bounty_number=self.bounty_number,
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

        self._add_setup_resources(resource_configs)
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

    async def run_one_iteration(
        self,
        phase_message: PhaseMessage,
        agent_instance: Any,
        previous_output: Optional[Message],
    ) -> Message:
        """
        Run a single iteration of the DetectPhase.

        Args:
            phase_message (PhaseMessage): The current phase message.
            agent_instance (Any): The agent instance to run.
            previous_output (Optional[Message]): The output from the previous iteration.

        Returns:
            Message: The resulting message from the agent - do NOT return the phase message
        """
        input_list: List[Message] = []
        if previous_output is not None:
            input_list.append(previous_output)

        message: Message = await agent_instance.run(input_list)

        if isinstance(agent_instance, DetectAgent):
            if message.submission:
                logger.status("Detect submitted!", message.success)
                phase_message.set_summary("detect_submitted")
                phase_message.set_complete()
            if message.success:
                logger.status("Vulnerability detected!", True)
                phase_message.set_summary("detect_success")
                phase_message.set_success()
                phase_message.set_complete()

        return message
