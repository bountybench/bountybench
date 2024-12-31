from typing import List, Tuple, Optional, Type, Any

from dataclasses import dataclass

from base_phase import BasePhase, PhaseConfig
from agents.patch_agent import PatchAgent, PatchAgentConfig
from agents.executor_agent import ExecutorAgent, ExecutorAgentConfig
from responses.response import Response
from responses.edit_response import EditResponse

from utils.logger import get_main_logger

logger = get_main_logger(__name__)


class PatchPhase(BasePhase):
    """
    PatchPhase is responsible for applying patches to the target system
    and verifying their successful application.
    """

    # Define the agent classes required for this phase
    AGENT_CLASSES: List[Type[BaseAgent]] = [PatchAgent, ExecutorAgent]

    def get_agent_configs(self) -> List[Tuple[str, 'AgentConfig']]:
        """
        Provide agent configurations for the PatchPhase.

        Returns:
            List[Tuple[str, AgentConfig]]: List of (agent_id, AgentConfig) tuples.
        """
        # Configure PatchAgent
        patch_agent_config = PatchAgentConfig(
            id="patch_agent",
            # Add PatchAgent-specific configuration parameters here
            # Example:
            patch_directory="/path/to/patches",
            # ...
        )

        # Configure ExecutorAgent
        executor_agent_config = ExecutorAgentConfig(
            id="executor_agent",
            model="executor-model",
            max_output_tokens=200,
            max_input_tokens=200,
            max_iterations=5,
            use_helm=False,
            target_host="localhost"
        )

        return [
            ("patch_agent", patch_agent_config),
            ("executor_agent", executor_agent_config)
        ]

    def run_one_iteration(
        self,
        agent_instance: Any,
        previous_output: Optional[Response],
        iteration_num: int
    ) -> Tuple[Response, bool]:
        """
        Execute one iteration of the patching process.

        Args:
            agent_instance (Any): The agent instance to run.
            previous_output (Optional[Response]): The output from the previous iteration.
            iteration_num (int): The current iteration number.

        Returns:
            Tuple[Response, bool]: The response from the agent and a flag indicating if the phase is complete.
        """
        # Run the agent with the previous output as input
        response = agent_instance.run([previous_output] if previous_output else [])
        logger.info(f"Iteration {iteration_num}: Agent '{agent_instance.agent_config.id}' response: {response}")

        # Determine if the phase should be marked as complete based on the agent's response
        if isinstance(agent_instance, ExecutorAgent):
            if "patched" in response.response.lower():
                return response, True  # Phase complete
        elif isinstance(agent_instance, PatchAgent):
            # Example condition: check if patching was successful
            if "patch applied" in response.response.lower():
                return response, False  # Continue to next agent or iteration
        # Add more conditions as necessary for other agents

        return response, False  # Continue running the phase

    def _is_phase_complete(self, response: Response) -> bool:
        """
        Determine if the patch phase is complete based on the agent's response.

        Args:
            response (Response): The response from the agent.

        Returns:
            bool: True if the patch was successfully applied, False otherwise.
        """
        return "patched" in response.response.lower()