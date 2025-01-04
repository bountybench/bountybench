from agents.base_agent import AgentConfig
from agents.dataclasses.agent_lm_spec import AgentLMConfig
from phases.base_phase import BasePhase
from agents.patch_agent.patch_agent import PatchAgent, PatchAgentConfig
from agents.executor_agent.executor_agent import ExecutorAgent, ExecutorAgentConfig
from resources.base_resource import BaseResource
from resources.init_files_resource import InitFilesResource, InitFilesResourceConfig
from responses.answer_response import AnswerResponseInterface
from responses.response import Response
from resources.kali_env_resource import KaliEnvResource, KaliEnvResourceConfig
from resources.docker_resource import DockerResource, DockerResourceConfig
from typing import Any, Dict, List, Optional, Tuple, Type
from resources.setup_resource import SetupResource, SetupResourceConfig
import os
import logging

logger = logging.getLogger(__name__)

class PatchPhase(BasePhase):
    """Phase responsible for patching vulnerabilities."""
    
    AGENT_CLASSES = [PatchAgent, ExecutorAgent]


    def define_agents(self) -> List[Tuple[str, AgentConfig]]:
        executor_lm_config = AgentLMConfig(
            model='openai/o3-mini-2024-12-17',
            max_output_tokens=5000,
            max_input_tokens=5000,
            max_iterations_stored_in_memory=3,
            use_helm=False
        )
        
        executor_config = ExecutorAgentConfig(
            id="ExecutorAgent",
            lm_config=executor_lm_config,
            target_host=self.workflow.repo_metadata["target_host"],
            initial_prompt=self.workflow._get_initial_prompt()

        )

        patch_config = PatchAgentConfig(
            id="PatchAgent",
            bounty_dir=os.path.join("bounties", f"bounty_{self.workflow.bounty_number}")
        )

        return [
            ("ExecutorAgent", executor_config),
            ("PatchAgent", patch_config),
        ]
    

   
    def define_resources(self) -> Dict[str, Tuple[Type['BaseResource'], Any]]:
        """
        Define resource classes and their configurations required by the PatchPhase.

        Returns:
            Dict[str, Tuple[Type[BaseResource], Any]]: Mapping of resource_id to (ResourceClass, ResourceConfig).
        """
        logger.debug(f"Entering define_resources for PatchPhase")

        tmp_dir = os.path.join("tmp")  # Assuming a default tmp directory
        patch_files_path = os.path.join(tmp_dir, "patch_files")
        os.makedirs(patch_files_path, exist_ok=True)

        files_dir = self.workflow.bounty_metadata.get('files_dir', 'codebase')
        exploit_files_dir = self.workflow.bounty_metadata.get('exploit_files_dir', f'bounties/bounty_{self.workflow.bounty_number}/exploit_files')
        vulnerable_commit = self.workflow.bounty_metadata.get('vulnerable_commit', 'main')

        resource_configs = {
            "kali_env": (
                KaliEnvResource,
                KaliEnvResourceConfig(
                    task_dir=self.workflow.task_dir,
                    bounty_number=self.workflow.bounty_number,
                    volumes={
                        os.path.abspath(tmp_dir): {"bind": "/app", "mode": "rw"},
                        os.path.abspath(patch_files_path): {"bind": "/app/patch_files", "mode": "rw"},
                        "/tmp": {"bind": "/tmp", "mode": "rw"}
                    }
                )
            ),
            "docker": (
                DockerResource,
                DockerResourceConfig()
            ),
            "init_files": (
                InitFilesResource,
                InitFilesResourceConfig(
                    task_dir=self.workflow.task_dir,
                    files_dir_name=files_dir,
                    tmp_dir_name=tmp_dir,
                    exploit_files_dir_name=exploit_files_dir,
                    vulnerable_commit=vulnerable_commit
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
                    files_dir=files_dir
                )
            )

        target_host = self.workflow.repo_metadata.get("target_host")
        if target_host:
            task_server_config = SetupResourceConfig(
                task_level_setup=True,
                task_dir=self.workflow.task_dir,
                files_dir=files_dir,
                bounty_number=self.workflow.bounty_number,
                server_address=target_host
            )
            resource_configs["task_server"] = (SetupResource, SetupResourceConfig)

        logger.debug(f"Exiting define_resources for PatchPhase")
        return resource_configs


    def run_one_iteration(
        self,
        agent_instance: Any,
        previous_output: Optional[Response],
    ) -> Tuple[Response, bool]:
        """
        1) Call the agent with previous_output as input.
        2) If ExecutorAgent produces an AnswerResponseInterface -> hallucination -> finalize & done.
        3) If PatchAgent produces an AnswerResponseInterface -> patch success -> finalize & done.
        4) Otherwise continue.
        """
        input_list = []
        if previous_output is not None:
            input_list.append(previous_output)

        response = agent_instance.run(input_list)

        # Determine which agent name was used in this iteration
        agent_name, _ = self._get_current_agent()

        if agent_name == "ExecutorAgent":
            if isinstance(response, AnswerResponseInterface):
                logger.info("Executor agent hallucinated an answer!")
                self._set_phase_summary("completed_with_hallucination")
                return response, True

        elif agent_name == "PatchAgent":
            if isinstance(response, AnswerResponseInterface):
                logger.info("Patch Success!")
                self._set_phase_summary("patch_success")
                return response, True

        return response, False