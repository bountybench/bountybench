from agents.base_agent import AgentConfig, BaseAgent
from agents.import_bounty_agent.import_bounty_agent import ImportBountyAgent, ImportBountyAgentConfig
from agents.webscraper_agent.webscraper_agent import WebscraperAgent, WebscraperAgentConfig
from messages.message import Message
from messages.phase_messages.phase_message import PhaseMessage
from phases.base_phase import BasePhase
from resources.base_resource import BaseResource, BaseResourceConfig
from resources.resource_type import ResourceType
from typing import Any, Dict, List, Optional, Tuple, Type
from utils.logger import get_main_logger
from workflows.base_workflow import BaseWorkflow


logger = get_main_logger(__name__)

class ScraperPhase(BasePhase):
    """
    ScraperPhase is responsible for scraping the web for new bounty reports.
    """
    AGENT_CLASSES = [WebscraperAgent, ImportBountyAgent]

    def __init__(self, workflow: 'BaseWorkflow', **kwargs):
        """
        Initialize the ScraperPhase.

        Args:
            workflow (BaseWorkflow): The parent workflow.
            **kwargs: Additional keyword arguments.
        """
        self.model = kwargs.get('model')
        self.helm = kwargs.get('helm')
        self.website = kwargs.get('website', "https://huntr.com/bounties")
        self.bounty_dir = kwargs.get('bounty_dir', "agents/import_bounty_agent/bounties")
        super().__init__(workflow, **kwargs)

    def define_agents(self) -> Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]:
        """
        Define the agents required for the ScraperPhase.

        Returns:
            Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]: A dictionary mapping agent names to their types and configurations.
        """
        # Website will use default value
        webscraper_config = WebscraperAgentConfig(
            website=self.website
        )
        import_bounty_config = ImportBountyAgentConfig(
            bounty_dir=self.bounty_dir
        )

        return {
            "webscraper_agent": (WebscraperAgent, webscraper_config),
            "import_bounty_agent": (ImportBountyAgent, import_bounty_config)
        }
    
    
    def define_resources(self) -> List[Tuple[ResourceType, BaseResourceConfig]]:
        """
        Define resource classes and their configurations required by the ScraperPhase.

        Returns:
            List[Tuple[ResourceType, BaseResourceConfig]]: Mapping of resource_id to (ResourceClass, ResourceConfig).
        """
        return []

    async def run_one_iteration(
        self,
        phase_message: PhaseMessage,
        agent_instance: Any,
        previous_output: Optional[Message]
    ) -> Message:
        """
        Run a single iteration of the ScraperPhase.

        This method performs the following steps:
        1) Call the agent with the previous_message as input (if any).
        2) Search for new bounty report upload (WebscraperAgent).
        3) If a new bounty is found, import bounty (ImportBountyAgent).
        4) Otherwise continue.

        Args:
            agent_instance (Any): The agent instance to run.
        """
        # Prepare input message list for agent
        input_list: List[Message] = []
        if previous_output is not None:
            input_list.append(previous_output)

        message: Message = await agent_instance.run(input_list)
        
        # Determine which agent name was used in this iteration
        _, agent_instance = self._get_current_agent()

        # Check for new bounty discovery (WebscraperAgent)
        if isinstance(agent_instance, WebscraperAgent):
            logger.status("New bounty found!", True)
            phase_message.set_summary("new_bounty_found")

        # Check for import success (ImportBountyAgent)
        elif isinstance(agent_instance, ImportBountyAgent):
            if message.success:
                logger.status("Bounty import successful!", True)
                phase_message.set_summary("bounty_import_success")
        else:
            logger.status("ScraperPhase unsuccessful.", False)
            phase_message.set_complete()
            phase_message.set_failure()

        # Stop if we reach max iterations
        # if self.max_iterations_reached():
        #     phase_message.set_complete()
        #     phase_message.set_success()

        return message
