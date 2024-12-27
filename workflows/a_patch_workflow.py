import os
from pathlib import Path
from agents.dataclasses.agent_lm_spec import AgentLMConfig
from agents.executor_agent.executor_agent import ExecutorAgent
from agents.executor_agent.prompt import PATCH_PROMPT
from phases.base_phase import PhaseConfig
from phases.patch_phase import PatchPhase
from resources.docker_resource import DockerResource, DockerResourceConfig
from resources.kali_env_resource import KaliEnvResource, KaliEnvResourceConfig
from responses.command_response import STOP_TOKEN
from workflows.base_workflow import BaseWorkflow, WorkflowConfig

#handling of optional resources todo

class PatchWorkflow(BaseWorkflow):
    """Workflow for patching vulnerabilities"""
    
    PHASES = [PatchPhase]
    # Agents = ExecutorAgent, PatchAgent
    # Resource =  KaliEnvResource, DockerResource (InitFilesResource, (maybe SetupFilesResource (2x)) handled in super)
    
    def __init__(self, task_repo_dir: Path, bounty_number: str, interactive: bool=False):
        workflow_id = "exploit_and_patch_workflow"
        super().__init__(task_repo_dir, bounty_number, workflow_id, interactive)

    def define_resources(self):
        super().__init__(self)
        
        # Setup Kali environment and Docker
        kali_env_config = KaliEnvResourceConfig(
            task_repo_dir=self.task_repo_dir,
            bounty_number=self.bounty_number,
            volumes={
                os.path.join(str(self.task_repo_dir.absolute()), tmp_dir): {"bind": "/app", "mode": "rw"}
                }
        )
        self.register_resource("KaliEnv", KaliEnvResource, kali_env_config)

        docker_config = DockerResourceConfig()
        self.register_resource("DockerHelper", DockerResource, docker_config)


    def get_initial_prompt(self):
        prompt = PATCH_PROMPT.format(
            task_description=self.exploit_description,
            stop_token=STOP_TOKEN,
            target_host=self.repo_metadata["target_host"],
        )
    
        return prompt
    
    def define_agents(self) -> None:
        """Configure agents"""
        # Format exploit description
        vulnerable_files_formatted = ", ".join(f"`{file}`" for file in self.vulnerable_files)
        self.exploit_description = f"""
        {self.bounty_metadata["exploit_prompt"]} 
        The path to the vulnerable file(s) is {vulnerable_files_formatted}. 
        """
        
        # Configure and create agents
        executor_lm_agent_config = AgentLMConfig(
            model='openai/o3-mini-2024-12-17',
            max_output_tokens=25000,
            max_input_tokens=25000,
            max_iterations=25,
            max_iterations_stored_in_memory=3,
            use_helm=False
        )

        executor_agent_config = ExecutorAgentConfig(
            config=executor_lm_agent_config,
            logger=self.workflow_logger,
            target_host=self.repo_metadata["target_host"]
        )
        self.register_agent("ExecutorAgent", ExecutorAgent, executor_agent_config)
        
        patch_agent_config = PatchAgentConfig(
            bounty_dir=os.path.join("bounties", f"bounty_{self.bounty_number}")
            )
        self.register_agent("PatchAgent", patch_agent_config)

    def define_phases(self) -> None:
        super().define_phases()

        # Configure patch phase
        phase_config = PhaseConfig(
            phase_idx=0,
            phase_name="patch",
            max_iterations=25,
            agents=[
                ("executor_agent", self.executor_agent),
                ("patch_agent", self.patch_agent)
            ]
        )
        self.register_phase(PatchPhase, phase_config)

def main() -> None:
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the patch workflow")
    parser.add_argument("--task_repo_dir", type=str, help="The directory of the task repo")
    parser.add_argument("--bounty_number", type=str, help="The bounty number")
    args = parser.parse_args()
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Run workflow
    workflow = PatchWorkflow(Path(args.task_repo_dir), args.bounty_number)
    workflow.run()

if __name__ == "__main__":
    main()
