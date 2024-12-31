from agents.base_agent import AgentConfig
from agents.dataclasses.agent_lm_spec import AgentLMConfig
from phases.base_phase import BasePhase, PhaseConfig
from agents.patch_agent.patch_agent import PatchAgent, PatchAgentConfig
from agents.executor_agent.executor_agent import ExecutorAgent, ExecutorAgentConfig
from resources.init_files_resource import InitFilesResource, InitFilesResourceConfig
from responses.answer_response import AnswerResponseInterface
from responses.response import Response
from responses.edit_response import EditResponse
from resources.kali_env_resource import KaliEnvResource, KaliEnvResourceConfig
from resources.docker_resource import DockerResource, DockerResourceConfig
from typing import Any, List, Optional, Tuple, Type
from resources.setup_resource import SetupResource, SetupResourceConfig
import os
import logging

logger = logging.getLogger(__name__)

class PatchPhase(BasePhase):
    """Phase responsible for patching vulnerabilities."""
    
    AGENT_CLASSES = [PatchAgent, ExecutorAgent]


    def get_agent_configs(self) -> List[Tuple[str, AgentConfig]]:
        executor_lm_config = AgentLMConfig(
            model='openai/o3-mini-2024-12-17',
            max_output_tokens=25000,
            max_input_tokens=25000,
            max_iterations=25,
            max_iterations_stored_in_memory=3,
            use_helm=False
        )
        
        executor_config = ExecutorAgentConfig(
            id="executor_agent",
            lm_config=executor_lm_config,
            target_host=self.workflow.repo_metadata["target_host"]
        )

        patch_config = PatchAgentConfig(
            id="patch_agent",
            bounty_dir=os.path.join("bounties", f"bounty_{self.workflow.bounty_number}")
        )

        return [
            ("executor_agent", executor_config),
            ("patch_agent", patch_config)
        ]
    

    def register_resources(self):
        """Register resources required by the PatchPhase."""
        # Access the ResourceManager via the agent manager
        resource_manager = self.agent_manager.resource_manager

        # Define KaliEnvResource configuration
        tmp_dir = os.path.join(str(resource_manager.resources.get("init_files", {}).get("tmp_dir", "tmp")))
        patch_files_path = os.path.join(tmp_dir, "patch_files")
        os.makedirs(patch_files_path, exist_ok=True)
        kali_env_config = KaliEnvResourceConfig(
            task_repo_dir=self.workflow.task_repo_dir,
            bounty_number=self.workflow.bounty_number,
            volumes={
                os.path.abspath(tmp_dir): {"bind": "/app", "mode": "rw"},
                os.path.abspath(patch_files_path): {"bind": "/app/patch_files", "mode": "rw"},
                "/tmp": {"bind": "/tmp", "mode": "rw"}
            }
        )
        resource_manager.register_resource("kali_env", KaliEnvResource, kali_env_config)
        logger.info("Registered 'kali_env' resource for PatchPhase.")

        # Define DockerResource configuration
        docker_config = DockerResourceConfig()
        resource_manager.register_resource("docker", DockerResource, docker_config)
        logger.info("Registered 'docker' resource for PatchPhase.")


        files_dir = self.workflow.bounty_metadata.get('files_dir', 'codebase')
        exploit_files_dir = self.workflow.bounty_metadata.get('exploit_files_dir', f'bounties/bounty_{self.workflow.bounty_number}/exploit_files')
        vulnerable_commit = self.workflow.bounty_metadata.get('vulnerable_commit', 'main')

        init_files_config = InitFilesResourceConfig(
            task_repo_dir=self.workflow.task_repo_dir,
            files_dir_name=files_dir,
            tmp_dir_name=tmp_dir,
            exploit_files_dir_name=exploit_files_dir,
            vulnerable_commit=vulnerable_commit
        )

        resource_manager.register_resource("init_files", InitFilesResource, init_files_config)
        logger.info("Registered 'init_files' resource.")

        setup_repo_env_script = os.path.join(str(self.workflow.task_repo_dir), "setup_repo_env.sh")
        if os.path.exists(setup_repo_env_script):
            repo_env_config = SetupResourceConfig(
                task_level_setup=False,
                task_repo_dir=self.workflow.task_repo_dir,
                files_dir=files_dir
            )
            self.register_resource("repo_resource", SetupResource, repo_env_config)
            logger.info("Registered 'repo_resource' for repository environment.")

        else:
            logger.debug("No repository environment setup script found.")


    def run_one_iteration(
        self,
        agent_instance: Any,
        previous_output: Optional[Response],
        iteration_num: int
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
        agent_name, _ = self._get_agent()

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


    @property
    def name(self):
        return "PatchPhase" 