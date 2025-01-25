import asyncio
from pathlib import Path
from utils.logger import get_main_logger
from workflows.bounty_workflow import BountyWorkflow
from phases.save_data_phase import SaveDataPhase

logger = get_main_logger(__name__)

class FindBountiesWorkflow(BountyWorkflow):
    """Workflow for finding and importing bounties"""
    
    def _create_phases(self):
        """Define and create phases specific to FindBountiesWorkflow."""
        phase_kwargs = {}
        save_data_phase = SaveDataPhase(workflow=self, **phase_kwargs)
        self._register_root_phase(save_data_phase)

async def main() -> None:
    """Main entry point"""

    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Run workflow
    workflow = FindBountiesWorkflow()
    await workflow.run()

if __name__ == "__main__":
    asyncio.run(main())