import asyncio
from pathlib import Path
from agents.prompts import CTF_PROMPT, STOP_TOKEN # Add CTF prompt
from phases.ctf_phase import CTFPhase
from resources.utils import read_writeup
from utils.logger import get_main_logger
from workflows.bounty_workflow import BountyWorkflow

logger = get_main_logger(__name__)

class CTFWorkflow(BountyWorkflow):
    """Workflow for CTF tasks"""
    
    def _create_phases(self):
        """Define and create phases specific to ExploitPatchWorkflow."""

        phase_kwargs = {
            'model': self.params.get('model'),
            'helm': self.params.get('helm'),
            'task_dir': self.task_dir,
            'bounty_number': self.bounty_number,
            'use_agent_exploit': True, 
            'use_verify_script': False,
            'task_description': read_writeup(self.task_dir, self.bounty_number),
            'additional_prompt_information': self.bounty_metadata.get("additional_prompt_information", ""),
            'stop_token': STOP_TOKEN,
            'target_host': self.repo_metadata["target_host"],
            'initial_prompt': self.initial_prompt,
            'info': self.repo_metadata.get("info", "") + "\n" + self.bounty_metadata.get("info", ""),
            'flag': self.bounty_metadata.get("flag", "")
        }
        if hasattr(self, "phase_iterations"):
            phase_kwargs["max_iterations"] = self.phase_iterations

        phase_kwargs["interactive"] = self.interactive
        
        ctf_phase = CTFPhase(workflow=self, **phase_kwargs)
        
        self._register_root_phase(ctf_phase)


    def _get_initial_prompt(self):
        """
        Provide the initial prompt for the workflow by reading the exploit report.

        Returns:
            str: The formatted initial prompt.
        """
        return CTF_PROMPT if self.repo_metadata["target_host"] else CTF_PROMPT

async def main() -> None:
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the CTF workflow")
    parser.add_argument("--task_dir", type=str, help="The directory of the task repo")
    parser.add_argument("--bounty_number", type=str, help="The bounty number")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    
    parser.add_argument("--model", type=str, help="The LM model to query")
    parser.add_argument("--helm", action="store_true", help="Use HelmModels")
    # parser.add_argument("--max_input_tokens", action="store_true", help="Max input tokens to pass into model")
    
    parser.add_argument("--phase_iterations", type=int, help="max iteractions to run of ExploitPhase and PatchPhase each")
    args = parser.parse_args()
    logger.info("Parsed command line args")
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    logger.info(f"Created logs directory at: {logs_dir}")
    
    # Run workflow
    workflow = CTFWorkflow(task_dir=Path(args.task_dir), bounty_number=args.bounty_number, interactive=args.interactive, model=args.model, phase_iterations=args.phase_iterations)
    await workflow.run()

if __name__ == "__main__":
    asyncio.run(main())
