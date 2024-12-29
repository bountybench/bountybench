from pathlib import Path

from agents.chat_agent.chat_agent import ChatAgent, ChatAgentConfig
from agents.dataclasses.agent_lm_spec import AgentLMConfig
from phases.base_phase import PhaseConfig
from phases.chat_phase import ChatPhase
from utils.logger import get_main_logger
from workflows.base_workflow import BaseWorkflow

logger = get_main_logger(__name__)

class ChatWorkflow(BaseWorkflow):
    """Workflow for chatting"""
    
    REQUIRED_PHASES = [ChatPhase]
    # Agents = ChatAgent
    
    exploit_files_path = None
    patch_files_path = None

    def __init__(self, task_repo_dir: Path, bounty_number: str, interactive: bool = False):
        workflow_id = "chat_workflow"
        self.interactive = interactive
        super().__init__(task_repo_dir, bounty_number, workflow_id, interactive)     

    def define_resource_configs(self) -> None:
        """Configure resources"""
        pass

    def define_agent_configs(self) -> None:
        """Configure agents"""
        chat_agent_lm_config = AgentLMConfig(
            model="anthropic/claude-3-5-sonnet-20240620",
            max_output_tokens=4096,
            max_input_tokens=4096,
            max_iterations=25,
            max_iterations_stored_in_memory=3,
            use_helm=True
        )

        chat_agent_config = ChatAgentConfig(
            id="chat_agent",
            lm_config=chat_agent_lm_config
        )
        self.register_agent(ChatAgent, chat_agent_config)

    def define_phase_configs(self) -> None:
        """Define workflow phase configs"""
        if "chat_agent" not in self.agents:
            raise ValueError("Missing required agent: 'chat_agent'.")

        chat_config = PhaseConfig(
            phase_idx=0,
            phase_name=ChatPhase,
            max_iterations=3,
            agents=[
                ("chat_agent", self.agents["chat_agent"])
            ],
            interactive=self.interactive
        )
        self.register_phase(ChatPhase, chat_config)     

    def get_initial_prompt(self):
        return None
    
    def setup_directories(self) -> None:
        """No necessary directories for this workflow."""
        pass

def main() -> None:
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the exploit and patch workflow")
    parser.add_argument("--task_repo_dir", type=str, help="The directory of the task repo")
    parser.add_argument("--bounty_number", type=str, help="The bounty number")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    args = parser.parse_args()
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Run workflow
    workflow = ChatWorkflow(Path(args.task_repo_dir), args.bounty_number, args.interactive)
    workflow.run()

if __name__ == "__main__":
    main()
