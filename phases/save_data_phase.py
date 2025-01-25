from agents.base_agent import AgentConfig, BaseAgent
from agents.import_bounty_agent.import_bounty import ImportBountyAgent, ImportBountyAgentConfig
from agents.webscraper_agent.webscraper_agent import WebscraperAgent, WebscraperAgentConfig
from messages.message import Message
from phases.base_phase import BasePhase
from resources.base_resource import BaseResource
from typing import Any, Dict, Optional, Tuple, Type
from utils.logger import get_main_logger
from workflows.base_workflow import BaseWorkflow


logger = get_main_logger(__name__)

class SaveDataPhase(BasePhase):
    AGENT_CLASSES = [WebscraperAgent, ImportBountyAgent]

    def __init__(self, workflow: 'BaseWorkflow', **kwargs):
        self.model = kwargs.get('model')
        self.helm = kwargs.get('helm')
        super().__init__(workflow, **kwargs)

    def define_agents(self) -> Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]:
        webscraper_config = WebscraperAgentConfig()

        import_bounty_config = ImportBountyAgentConfig()

        return {
            "webscraper_agent": (WebscraperAgent, webscraper_config),
            "import_bounty_agent": (ImportBountyAgent, import_bounty_config)
        }
    
    
    def define_resources(self) -> Dict[str, Tuple[Type['BaseResource'], Any]]:
        """
        Define resource classes and their configurations required by the SaveDataPhase.

        Returns:
            Dict[str, Tuple[Type[BaseResource], Any]]: Mapping of resource_id to (ResourceClass, ResourceConfig).
        """
        return {}

    async def run_one_iteration(
        self,
        agent_instance: Any,
        previous_output: Optional[Message]
    ) -> Tuple[Message, bool]:
        """
        1) Call the agent with the previous_message as input (if any).
        2) Search for new bounty report upload (WebscraperAgent).
        3) If a new bounty is found, import bounty (ImportBountyAgent).
        4) Otherwise continue.
        """
        # Prepare input message list for agent
        input_list = []
        if previous_output is not None:
            input_list.append(previous_output)

        message = await agent_instance.run(input_list)
        
        # Determine which agent name was used in this iteration
        _, agent_instance = self._get_current_agent()

        # Check for new bounty discovery (WebscraperAgent)
        if isinstance(agent_instance, WebscraperAgent):
            if message.success:
                logger.status("New bounty found!")
                self._set_phase_summary("new_bounty_found")
                return message

        # Check for import success (ImportBountyAgent)
        if isinstance(agent_instance, ImportBountyAgent):
            if message.success:
                logger.status("Bounty import successful!", True)
                self._set_phase_summary("bounty_import_success")
                return message

        # Otherwise, continue looping
        return message
