from typing import List, Optional, Union

from agents.base_agent import BaseAgent
from messages.action_messages.action_message import ActionMessage
from messages.action_messages.answer_message import AnswerMessage
from messages.action_messages.command_message import CommandMessage
from messages.agent_messages.agent_message import AgentMessage
from resources.model_resource.model_resource import ModelResource
from messages.message import Message
from utils.progress_logger import start_progress, stop_progress
from utils.logger import logger

MAX_RETRIES = 3
RETRY_DELAY = 30

class ChatAgent(BaseAgent):

    REQUIRED_RESOURCES = [
        (ModelResource, "model")

    ]
    OPTIONAL_RESOURCES = []
    ACCESSIBLE_RESOURCES = [
        (ModelResource, "model")]

    
    async def run(self, messages: List[Message]) -> Message:
        if len(messages) > 1:
            raise Exception(f"Accepts at most a single message, got {len(messages)}.")
        if len(messages) == 0:        
            prev_agent_message = None
        else:
            prev_agent_message = messages[0]

        agent_message = AgentMessage(agent_id=self.agent_id, prev=prev_agent_message)
        action_message = prev_agent_message.action_messages[-1] if prev_agent_message and len(prev_agent_message.action_messages) > 0 else None
        self.execute(agent_message, action_message)
        return agent_message

    def execute(self, agent_message: AgentMessage, action_message: Optional[ActionMessage] = None) -> Message:
        model_action_message = self.call_lm(action_message)
        agent_message.add_action_message(model_action_message)
        logger.info(f"LM Response:\n{model_action_message.message}")

        return model_action_message

    def call_lm(self, lm_input_message: Optional[ActionMessage] = None) -> Union[AnswerMessage, CommandMessage]:
        """
        Calls the language model and ensures the response is in valid format.
        Retries up to MAX_RETRIES if the response is invalid.
        """
        iterations = 0
        
        start_progress(f"Getting response from LM")
        try:
            iterations = 0 
            while iterations < MAX_RETRIES:
                try:
                    model_response = self.model.run(lm_input_message)
                    return model_response
                except Exception as e:
                    logger.warning(f"Retrying {iterations + 1}/{MAX_RETRIES} after parse error: {e}")
                    iterations += 1

            # If we've exhausted all retries
            raise Exception("call_lm error: Max retries reached without valid response.")

        except Exception as e:
            logger.error(f"Error in call_lm: {str(e)}")
            raise  # Re-raise the exception after logging it

        finally:
            stop_progress()