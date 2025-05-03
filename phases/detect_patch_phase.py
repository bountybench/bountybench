from typing import Any, Dict, List, Optional, Tuple, Type

from agents.base_agent import AgentConfig, BaseAgent
from agents.claude_code_agent.claude_code_agent import (
    ClaudeCodeAgent,
    ClaudeCodeAgentConfig,
)
from agents.detect_patch_agent.detect_patch_agent import (
    DetectPatchAgent,
    DetectPatchAgentConfig,
)
from agents.executor_agent.executor_agent import ExecutorAgent
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


class DetectPatchPhase(BountyPhase):
    """Phase responsible for patching vulnerabilities."""

    AGENT_CLASSES: List[Type[BaseAgent]] = [DetectPatchAgent, ExecutorAgent]

    def __init__(self, workflow: "BaseWorkflow", **kwargs):
        """
        Initialize the DetectPatchPhase.

        Args:
            workflow (BaseWorkflow): The parent workflow.
            **kwargs: Additional keyword arguments.
        """

        self.use_cwe = kwargs.get("use_cwe", False)

        super().__init__(workflow, **kwargs)
        if "compatible_patches" not in self.workflow.bounty_metadata:
            raise RuntimeError(
                f"Bounty {self.bounty_number} is missing 'compatible_patches' in its metadata. "
                "DetectPatchPhase requires this field to proceed."
            )

    def define_agents(self) -> Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]:
        """
        Define the agents required for the DetectPatchPhase.

        Returns:
            Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]: A dictionary mapping agent names to their types and configurations.
        """
        agents = {}

        agent_type = self.workflow.params.get("custom_agent", "executor_agent")

        if agent_type == "executor_agent":
            agents["executor_agent"] = (ExecutorAgent, AgentConfig())

        if agent_type == "claude_code":
            agents["claude_code"] = (ClaudeCodeAgent, ClaudeCodeAgentConfig())

        patch_config = DetectPatchAgentConfig(
            bounty_dir=self.bounty_dir,
            task_dir=self.workflow.task_dir,
            submit=self.submit,
            include_cwe=self.use_cwe,
        )
        agents["patch_agent"] = (DetectPatchAgent, patch_config)

        return agents

    def define_resources(self) -> List[Tuple[ResourceType, BaseResourceConfig]]:
        """
        Define resource classes and their configurations required by the DetectPatchPhase.
        """
        logger.debug("Entering define_resources for DetectPatchPhase")

        agent_type = self.workflow.params.get("custom_agent", "executor_agent")

        files_dir_name = self.workflow.bounty_metadata.get("files_dir", "codebase")
        vulnerable_commit = self.workflow.bounty_metadata.get(
            "vulnerable_commit", "main"
        )

        target_hosts = [self.workflow.repo_metadata["target_host"]]

        resource_configs: List[Tuple[ResourceType, BaseResourceConfig]] = []

        if agent_type != "claude_code":
            resource_configs.append(
                (
                    ResourceType.MODEL,
                    ModelResourceConfig.create(
                        model=self.model,
                        use_helm=self.helm,
                        use_mock_model=self.use_mock_model,
                        max_input_tokens=self.params.get("max_input_tokens"),
                        max_output_tokens=self.params.get("max_output_tokens"),
                    ),
                )
            )

        resource_configs.append(
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
            )
        )

        resource_configs.append(
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
                    install_claude_code=(agent_type == "claude_code"),
                ),
            )
        )

        resource_configs.append((ResourceType.DOCKER, DockerResourceConfig()))

        if agent_type != "claude_code":
            resource_configs.append((ResourceType.MEMORY, MemoryResourceConfig()))

        resource_configs += get_setup_resources(
            task_dir=self.workflow.task_dir,
            bounty_number=self.bounty_number,
            skip_bounty_setup=True,
        )

        logger.debug("Exiting define_resources for DetectPatchPhase")
        return resource_configs

    async def run_one_iteration(
        self,
        phase_message: PhaseMessage,
        agent_instance: Any,
        previous_output: Optional[Message],
    ) -> Message:
        """
        Run a single iteration of the DetectPatchPhase.

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

        if isinstance(agent_instance, DetectPatchAgent):
            summary = ""
            phase_message.set_summary("")
            if message.submission:
                logger.status("Patch submitted!", message.success)
                summary += "receive_submission"
                phase_message.set_complete()
            else:
                summary += "no_submission"

            if message.success:
                logger.info("Patch Success!")
                summary += "/success"
                phase_message.set_complete()
                phase_message.set_success()
            else:
                summary += "/failure"
            phase_message.set_summary(summary)

        return message
