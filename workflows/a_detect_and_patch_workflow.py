import argparse
import json
import os
from pathlib import Path
import shutil
import uuid

from agents.dataclasses.agent_lm_spec import AgentConfig
from agents.patch_agent.patch_agent import PatchAgent
from agents.executor_agent.prompt import DETECT_AND_PATCH_PROMPT, STOP_TOKEN
from agents.executor_agent.executor_agent import ExecutorAgent
from phases.detect_phase import DetectPhase
from resources.docker_resource import DockerResource
from resources.init_files_resource import InitFilesResource
from resources.kali_env_resource import KaliEnvResource
from resources.setup_resource import SetupResource
from resources.utils import *
from responses.answer_response_interface import AnswerResponseInterface
from utils.logger import get_main_logger
from resources.resource_dict import resource_dict

logger = get_main_logger(__name__)

# Function to save JSON log
def save_run_log(run_data, filename):
    with open(filename, 'w') as f:
        json.dump(run_data, f, indent=4)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the task")
    parser.add_argument(
        "--task_repo_dir", type=str, help="The directory of the task repo"
    )
    parser.add_argument(
        "--bounty_number",
        type=str,
        help="The bounty for the given task; not used in detect_all",
    )
    
    parser.add_argument(
        "--vuln_info",
        action="store_true",
        help="Share the CWE of the vulnerability in the prompt",
        default=False,
    )
    return parser.parse_args()

def main() -> None:
    args = parse_args()

    # Create a Path object for the task repository directory
    task_repo_dir = Path(args.task_repo_dir).resolve()
    task_repo_dir_str = str(task_repo_dir.name)  # Use only the directory name
    bounty_number = str(args.bounty_number)

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    executor_agent_config: AgentConfig = AgentConfig(
        model='openai/gpt-4o-2024-05-13',
        max_output_tokens=2000,
        max_input_tokens=6000,
        max_iterations=7,
        max_iterations_stored_in_memory=3,
        use_helm=True
    )
    
    # Replace slashes with underscores in the model name
    model_name_safe = executor_agent_config.model.replace("/", "_")
    file_id = uuid.uuid4()
    log_filename = logs_dir / f"patch_{task_repo_dir_str}_{bounty_number}_{model_name_safe}_{file_id}.json"

    network_name = "shared_net"

    # Check if the network exists
    if not docker_network_exists(network_name):
        logger.info(f"Creating Docker network: {network_name}")
        run_command(["docker", "network", "create", network_name])

    # Read metadata
    repo_metadata = read_repo_metadata(str(task_repo_dir))
    bounty_metadata = read_bounty_metadata(str(task_repo_dir), bounty_number)

    vuln_information=bounty_metadata["exploit_prompt"]
    detect_prompt = DETECT_AND_PATCH_PROMPT.format(
            additional_information=vuln_information,
            stop_token=STOP_TOKEN,
            target_host=repo_metadata["target_host"],
        )
    
    print(detect_prompt)
    print("==========================")

    files_dir, tmp_dir = "codebase", "tmp"

    # Relative to task_repo_dir

    InitFilesResource(task_repo_dir=task_repo_dir, files_dir_name=files_dir, tmp_dir_name=tmp_dir, exploit_files_dir_name=None, vulnerable_commit=bounty_metadata['vulnerable_commit'])
    if os.path.exists(str(task_repo_dir) + "/setup_repo_env.sh"): 
        SetupResource(task_level_setup=False, task_repo_dir=task_repo_dir, files_dir=files_dir)
    if repo_metadata["target_host"]: 
        SetupResource(task_level_setup=True, task_repo_dir=task_repo_dir, files_dir=files_dir, bounty_number=bounty_number, server_address=repo_metadata["target_host"])

    KaliEnvResource("KaliEnv", task_repo_dir=task_repo_dir, bounty_number=bounty_number, volumes={
                    os.path.join(task_repo_dir, tmp_dir): {"bind": "/app", "mode": "rw"}})
    DockerResource("DockerHelper")



    executor_agent_config: AgentConfig = AgentConfig(
        model='openai/gpt-4o-2024-05-13',
        max_output_tokens=2000,
        max_input_tokens=6000,
        max_iterations=15,
        max_iterations_stored_in_memory=3,
        use_helm=True
    )

    executor_agent = ExecutorAgent(
        executor_agent_config, initial_prompt=detect_prompt)

    bounty_dir=os.path.join("bounties", f"bounty_{bounty_number}")
    exploit_files_dir = os.path.join(bounty_dir, "exploit_files")
    patch_agent = PatchAgent(bounty_dir=bounty_dir, exploit_files_dir)

    # Initialize the log for all iterations
    run_log = {
        "iterations": []
    }

    simple_response = executor_agent.run([])

    

    for iteration in range(executor_agent_config.max_iterations):
        run_data = {}
        run_data["iteration"] = iteration + 1
        if run_data["iteration"] == 1: 
            run_data["executor_agent_input"] = executor_agent.prompt 
        else: 
            run_data["executor_agent_input"] = simple_response.response

        patch_response = patch_agent.run([simple_response])

        run_data["patch_agent_output"] = patch_response.response
        run_log["iterations"].append(run_data)

        if issubclass(patch_response.__class__, AnswerResponseInterface):
            logger.info("Patch Success!")
            break

        simple_response = executor_agent.run([simple_response])

        # If simple agent hallucinates, log and stop
        if issubclass(simple_response.__class__, AnswerResponseInterface):
            logger.info("Simple agent hallucinated an answer!")
            break

    save_run_log(run_log, log_filename)



if __name__ == "__main__":
    main()

import os
from pathlib import Path

from agents.dataclasses.agent_lm_spec import AgentLMConfig
from agents.patch_agent.patch_agent import PatchAgent, PatchAgentConfig
from agents.exploit_agent.exploit_agent import ExploitAgent, ExploitAgentConfig
from agents.executor_agent.prompt import EXPLOIT_AND_PATCH_PROMPT, STOP_TOKEN
from agents.executor_agent.executor_agent import ExecutorAgent, ExecutorAgentConfig
from phases.base_phase import PhaseConfig
from phases.exploit_phase import ExploitPhase
from phases.patch_phase import PatchPhase
from resources.docker_resource import DockerResource, DockerResourceConfig
from resources.kali_env_resource import KaliEnvResource, KaliEnvResourceConfig
from resources.utils import read_exploit_report
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

class ExploitAndPatchWorkflow(BaseWorkflow):
    """Workflow for exploiting and patching vulnerabilities"""
    
    PHASES = [DetectPhase, ExploitPhase, PatchPhase]
    # Agents = ExecutorAgent, ExploitAgent, PatchAgent
    # Resource =  KaliEnvResource, DockerResource (InitFilesResource, (maybe SetupFilesResource (2x)) handled in super)
    exploit_files_path = None
    patch_files_path = None

    def __init__(self, task_repo_dir: Path, bounty_number: str, ref_task_repo_dir: Path, ref_bounty_number: str, interactive: bool = False):
        workflow_id = "exploit_and_patch_workflow"
        super().__init__(task_repo_dir, bounty_number, workflow_id, interactive)
        self.ref_task_repo_dir = ref_task_repo_dir
        self.ref_bounty_number = ref_bounty_number
        
    ######################################################
    def define_phases(self) -> None:
        """Define workflow phase configs"""
        detect_config = PhaseConfig(
            phase_idx=0,
            phase_name="detect",
            max_iterations=5,
            agents=[
                ("executor_agent", None)
            ],
            interactive=self.interactive
        )
        self.register_phase(DetectPhase, detect_config)

        exploit_config = PhaseConfig(
            phase_idx=0,
            phase_name="exploit",
            max_iterations=5,
            agents=[
                ("executor_agent", None),
                ("exploit_agent", None)
            ],
            interactive=self.interactive
        )
        self.register_phase(ExploitPhase, exploit_config)

        phase_config = PhaseConfig(
            phase_idx=1,
            phase_name="patch",
            max_iterations=3,
            agents=[
                ("executor_agent", self.executor_agent),
                ("patch_agent", self.patch_agent)
            ],
            interactive=self.interactive
        )
        self.register_phase(PatchPhase, phase_config)
    
    def define_agents(self) -> None:
        """Configure agents"""
        executor_agent_lm_config = AgentLMConfig(
            model='openai/o3-mini-2024-12-17',
            max_output_tokens=25000,
            max_input_tokens=25000,
            max_iterations=25,
            max_iterations_stored_in_memory=3,
            use_helm=False
        )
        executor_agent_config = ExecutorAgentConfig(
            config=executor_agent_lm_config,
            logger=self.workflow_logger,
            target_host=self.repo_metadata["target_host"]
        )
        self.register_agent("ExecutorAgent", ExecutorAgent, executor_agent_config)
                
        exploit_agent_config = ExploitAgentConfig(
            bounty_dir=os.path.join("bounties", f"bounty_{self.bounty_number}")
            )
        self.register_agent("ExploitAgent", ExploitAgent, exploit_agent_config)

        patch_agent_config = PatchAgentConfig(
            bounty_dir=os.path.join("bounties", f"bounty_{self.bounty_number}")
            )
        self.register_agent("PatchAgent", PatchAgent, patch_agent_config)

    def define_resources(self) -> None:
        super().__init__(self)
                
        # Setup Kali environment and Docker
        kali_env_config = KaliEnvResourceConfig(
            task_repo_dir=self.task_repo_dir,
            bounty_number=self.bounty_number,
            volumes={
                os.path.abspath(os.path.join(str(self.task_repo_dir), tmp_dir)): {"bind": "/app", "mode": "rw"},
                os.path.abspath(self.exploit_files_path): {"bind": "/app/exploit_files", "mode": "rw"},
                os.path.abspath(self.patch_files_path): {"bind": "/app/patch_files", "mode": "rw"},
                "/tmp": {"bind": "/tmp", "mode": "rw"}
            }
        )
        self.register_resource("KaliEnv", KaliEnvResource, kali_env_config)

        docker_config = DockerResourceConfig()
        self.register_resource("DockerHelper", DockerResource, docker_config)
    ######################################################

    def get_initial_prompt(self):
        ref_exploit_report = read_exploit_report(self.ref_task_repo_dir, self.ref_bounty_number)
        prompt = DETECT_AND_PATCH_PROMPT.format(
            task_description=ref_exploit_report,
            stop_token=STOP_TOKEN,
            target_host=self.repo_metadata["target_host"],
        )
        return prompt

    # def setup_directories(self):
    #     tmp_dir = os.path.join(str(self.task_repo_dir), "tmp")
    #     self.exploit_files_path = os.path.join(tmp_dir, "exploit_files")

    #     os.makedirs(self.exploit_files_path, exist_ok=True)
        
    #     logger.info(f"Created exploit_files directory at: {self.exploit_files_path}")

def main() -> None:
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the exploit and patch workflow")
    parser.add_argument("--task_repo_dir", type=str, help="The directory of the task repo")
    parser.add_argument("--bounty_number", type=str, help="The bounty number")

    parser.add_argument("--ref_task_repo_dir", type=str, help="The directory of the reference task repo")
    parser.add_argument("--ref_bounty_number", type=str, help="The reference task bounty number")

    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    args = parser.parse_args()
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Run workflow
    workflow = ExploitAndPatchWorkflow(Path(args.task_repo_dir), args.bounty_number, Path(args.ref_task_repo_dir), args.ref_bounty_number, args.interactive)
    workflow.run()

if __name__ == "__main__":
    main()
