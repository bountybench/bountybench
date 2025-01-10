from pathlib import Path
from agents.executor_agent.prompt import DETECT_PROMPT, STOP_TOKEN
from phases.exploit_phase import ExploitPhase
from phases.patch_phase import PatchPhase
from resources.utils import read_exploit_report
from utils.logger import get_main_logger
from workflows.bounty_workflow import BountyWorkflow

logger = get_main_logger(__name__)

class DetectWorkflow(BountyWorkflow):
    """Workflow for detecting vulnerabilities"""

    def __init__(self, task_dir: Path, bounty_number: str, ref_task_dir: Path, ref_bounty_number: str, model: str, phase_iterations: int, interactive: bool = False):
        self.ref_task_dir = ref_task_dir
        self.ref_bounty_number = ref_bounty_number

        super().__init__(
            task_dir=task_dir,
            bounty_number=bounty_number,
            model=model,
            phase_iterations=phase_iterations,
            interactive=interactive
        )
    
    def _create_phases(self):
        """Define and create phases specific to DetectWorkflow."""
        init_prompt = self._get_initial_prompt()
        print("====================")
        print(init_prompt)
        print("====================")

        phase_kwargs = {
            'model': self.params.get('model'),
            'bounty_number': self.bounty_number,
            'initial_prompt': init_prompt,
        }
        if hasattr(self, "phase_iterations"):
            phase_kwargs["max_iterations"] = self.phase_iterations

        exploit_phase = ExploitPhase(workflow=self, **phase_kwargs)
        
        self._register_root_phase(exploit_phase)


    def _get_initial_prompt(self):
        """
        Provide the initial prompt for the workflow by reading the exploit report.

        Returns:
            str: The formatted initial prompt.
        """
        exploit_report = read_exploit_report(self.ref_task_dir, self.ref_bounty_number)
        prompt = DETECT_PROMPT.format(
            similar_bounty_report=exploit_report,
            stop_token=STOP_TOKEN,
            target_host=self.repo_metadata["target_host"],
        )
        return prompt

def main() -> None:
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the exploit and patch workflow")
    parser.add_argument("--task_dir", type=str, help="The directory of the task repo")
    parser.add_argument("--bounty_number", type=str, help="The bounty number")
    parser.add_argument("--ref_task_dir", type=str, help="The directory of the reference task repo")
    parser.add_argument("--ref_bounty_number", type=str, help="The reference task bounty number")

    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    
    parser.add_argument("--model", type=str, help="The LM model to query")
    
    parser.add_argument("--phase_iterations", type=int, help="max iteractions to run of ExploitPhase and PatchPhase each")
    args = parser.parse_args()
    logger.info("Parsed command line args")
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    logger.info(f"Created logs directory at: {logs_dir}")
    
    # Run workflow
    
    workflow = DetectWorkflow(task_dir=Path(args.task_dir), bounty_number=args.bounty_number, interactive=args.interactive, model=args.model, phase_iterations=args.phase_iterations, 
                              ref_task_dir=args.ref_task_dir, ref_bounty_number=args.ref_bounty_number)
    workflow.run()

if __name__ == "__main__":
    main()
