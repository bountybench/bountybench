from agents.base_agent import AgentConfig
from agents.dataclasses.agent_lm_spec import AgentLMConfig
from phase_responses.phase_response import PhaseResponse
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

from workflows.base_workflow import BaseWorkflow

from utils.logger import get_main_logger

logger = get_main_logger(__name__)

class PatchPhase(BasePhase):
    """Phase responsible for patching vulnerabilities."""
    
    AGENT_CLASSES = [PatchAgent, ExecutorAgent]

    def __init__(self, workflow: 'BaseWorkflow', **kwargs):
        self.model = kwargs.get('model')
        self.bounty_number = kwargs.get('bounty_number')
        self.initial_prompt = kwargs.get('initial_prompt')
        super().__init__(workflow, **kwargs)

    def define_agents(self) -> List[Tuple[str, AgentConfig]]:
        # assume we get model through some kwargs situation with the Message
        executor_lm_config = AgentLMConfig.create(model=self.model)
        exploit_files_dir = os.path.join(self.workflow.task_dir, f'bounties/bounty_{self.workflow.bounty_number}/exploit_files')
        
        # Create the executor_config
        executor_config = ExecutorAgentConfig(
            lm_config=executor_lm_config,
            target_host=self.workflow.repo_metadata["target_host"],
            initial_prompt=self.initial_prompt 
        )

        patch_config = PatchAgentConfig(
            bounty_dir=os.path.join("bounties", f"bounty_{self.bounty_number}"),
            task_dir=self.workflow.task_dir,
            exploit_files_dir=exploit_files_dir
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

        tmp_dir = os.path.abspath(os.path.join(self.workflow.task_dir, "tmp"))
        patch_files_path = os.path.join(tmp_dir, "patch_files")
        os.makedirs(patch_files_path, exist_ok=True)

        files_dir = self.workflow.bounty_metadata.get('files_dir', 'codebase')
        exploit_files_dir = f'bounties/bounty_{self.workflow.bounty_number}/exploit_files'
        vulnerable_commit = self.workflow.bounty_metadata.get('vulnerable_commit', 'main')

        resource_configs = {
            "init_files": (
                InitFilesResource,
                InitFilesResourceConfig(
                    task_dir=self.workflow.task_dir,
                    files_dir_name=files_dir,
                    tmp_dir_name="tmp",  
                    exploit_files_dir_name=exploit_files_dir,
                    vulnerable_commit=vulnerable_commit
                )
            ),
            "kali_env": (
                KaliEnvResource,
                KaliEnvResourceConfig(
                    task_dir=self.workflow.task_dir,
                    bounty_number=self.workflow.bounty_number,
                    volumes={
                        tmp_dir: {"bind": "/app", "mode": "rw"},  
                        os.path.join(tmp_dir, "patch_files"): {"bind": "/app/patch_files", "mode": "rw"},
                        "/tmp": {"bind": "/tmp", "mode": "rw"}
                    }
                )
            ),
            "docker": (
                DockerResource,
                DockerResourceConfig()
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
            resource_configs["task_server"] = (SetupResource, task_server_config)

        logger.debug(f"Exiting define_resources for PatchPhase")
        return resource_configs


    def run_one_iteration(
        self,
        phase_response: PhaseResponse,
        agent_instance: Any,
        previous_output: Optional[Response],
    ) -> Response:
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
        phase_response.add_agent_response(response)

        # Determine which agent name was used in this iteration
        agent_name, _ = self._get_current_agent()

        if agent_name == "ExecutorAgent":
            if isinstance(response, AnswerResponseInterface):
                logger.status("Executor agent hallucinated an answer!")
                self._set_phase_summary("completed_with_hallucination")
                phase_response.set_complete()
                return response

        elif agent_name == "PatchAgent":
            if isinstance(response, AnswerResponseInterface):
                logger.info("Patch Success!")
                self._set_phase_summary("patch_success")
                phase_response.set_complete()
                phase_response.set_success()
                return response

        return response