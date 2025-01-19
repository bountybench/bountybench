import asyncio
from pathlib import Path

from phases.chat_phase import ChatPhase
from workflows.base_workflow import BaseWorkflow

from utils.logger import get_main_logger

logger = get_main_logger(__name__)

class ChatWorkflow(BaseWorkflow):
    """Workflow for chating vulnerabilities"""
    
    def _create_phases(self):
        """Define and register phases specific to ChatWorkflow."""

        phase_kwargs = {
            'model': self.params.get('model'),
            'initial_prompt': self.initial_prompt,
            'helm': self.params.get('helm'),
        }
        if hasattr(self, "phase_iterations"):
            phase_kwargs["max_iterations"] = self.phase_iterations
        phase_kwargs["interactive"] = self.interactive

        chat_phase = ChatPhase(workflow=self, **phase_kwargs)

        self._register_root_phase(chat_phase)

    def _get_initial_prompt(self) -> str:
        return "You are a helpful chatbot. Please return all your responses with \"Command: {response}\""

async def main() -> None:
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Run the chat workflow")
    parser.add_argument("--interactive", action="store_true", help="Enable interactive mode")
    parser.add_argument("--model", type=str, help="The LM model to query")
    parser.add_argument("--helm", action="store_true", help="Use HelmModels")
    parser.add_argument("--phase_iterations", type=int, help="max iteractions to run of ChatPhase")
    args = parser.parse_args()

    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Run workflow
    workflow = ChatWorkflow(interactive=args.interactive, model=args.model, phase_iterations=args.phase_iterations)
    await workflow.run()

if __name__ == "__main__":
    asyncio.run(main())
