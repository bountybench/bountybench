import asyncio
from pathlib import Path
from utils.logger import get_main_logger
from workflows.base_workflow import BaseWorkflow
from phases.scraper_phase import ScraperPhase
from prompts.prompts import BASE_RESPONSE_FORMAT

logger = get_main_logger(__name__)

class ScraperWorkflow(BaseWorkflow):
    """Workflow for finding and importing bounties"""
    
    def _create_phases(self):
        """Define and create phases specific to ScraperWorkflow."""
        phase_kwargs = {
            "model": self.params.get("model"),
            "helm": self.params.get("helm"),
        }
        if hasattr(self, "phase_iterations"):
            phase_kwargs["max_iterations"] = self.phase_iterations
        scraper_phase = ScraperPhase(workflow=self, **phase_kwargs)
        self._register_root_phase(scraper_phase)

    def _get_initial_prompt(self):
        """
        Provide the initial prompt for the workflow.

        Returns:
            str: The formatted initial prompt.
        """
        return BASE_RESPONSE_FORMAT

async def main() -> None:
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Run the webscraper import bounty workflow")
    parser.add_argument(
        "--phase_iterations",
        type=int,
        help="max iteractions to run of ScraperPhase",
    )
    args = parser.parse_args()
    logger.info("Parsed command line args")

    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    logger.info(f"Created logs directory at: {logs_dir}")

    # Run workflow
    workflow = ScraperWorkflow(
        phase_iterations=args.phase_iterations,
    )
    await workflow.run()

if __name__ == "__main__":
    asyncio.run(main())