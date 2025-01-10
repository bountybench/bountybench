from pathlib import Path
from agents.executor_agent.prompt import DETECT_PROMPT, STOP_TOKEN
from phases.exploit_phase import ExploitPhase
from phases.patch_phase import PatchPhase
from resources.utils import read_writeup
from utils.logger import get_main_logger
from workflows.bounty_workflow import BountyWorkflow

logger = get_main_logger(__name__)

class DetectWorkflow(BountyWorkflow):
    """Workflow for detecting vulnerabilities"""

    def __init__(self, task_dir: Path, bounty_number: str, model: str, phase_iterations: int, interactive: bool = False, ref_task_dir: Path = None, ref_bounty_number: str = None, 
                 ref_exploit_report_path: Path = None):

        if ref_exploit_report_path is None and (ref_task_dir is None or ref_bounty_number is None):
            raise ValueError("Must provide either exploit_report_path or both ref_task_dir and ref_bounty_number")

        self.ref_task_dir = ref_task_dir
        self.ref_bounty_number = ref_bounty_number
        self.ref_exploit_report_path = ref_exploit_report_path



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
        if self.ref_exploit_report_path is not None:
            with open(self.ref_exploit_report_path, 'r') as f:
                exploit_report = f.read()
        else:
            exploit_report = read_writeup(self.ref_task_dir, self.ref_bounty_number)

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
    parser.add_argument("--task_dir", type=str, required=True, help="The directory of the task repo")
    parser.add_argument("--bounty_number", type=str, required=True, help="The bounty number")
    
    # Create a mutually exclusive group for exploit report input
    report_group = parser.add_mutually_exclusive_group()
    report_group.add_argument("--ref_exploit_report_path", type=str, help="Path to exploit report file")
    report_group.add_argument("--ref_task_dir", type=str, help="The directory of the reference task repo")
    
    # Only required if ref_task_dir is provided
    parser.add_argument("--ref_bounty_number", type=str, help="The reference task bounty number")
    
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    parser.add_argument("--model", type=str, help="The LM model to query")
    parser.add_argument("--phase_iterations", type=int, help="max iteractions to run of ExploitPhase and PatchPhase each")
    
    args = parser.parse_args()
    
    # Validate that ref_bounty_number is provided if ref_task_dir is used
    if args.ref_task_dir and not args.ref_bounty_number:
        parser.error("--ref_bounty_number is required when using --ref_task_dir")
    
    logger.info("Parsed command line args")
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    logger.info(f"Created logs directory at: {logs_dir}")
    
    # Run workflow
    workflow = DetectWorkflow(
        task_dir=Path(args.task_dir),
        bounty_number=args.bounty_number,
        interactive=args.interactive,
        model=args.model,
        phase_iterations=args.phase_iterations,
        ref_task_dir=Path(args.ref_task_dir) if args.ref_task_dir else None,
        ref_bounty_number=args.ref_bounty_number,
        ref_exploit_report_path=Path(args.ref_exploit_report_path) if args.ref_exploit_report_path else None
    )
    workflow.run()

if __name__ == "__main__":
    main()