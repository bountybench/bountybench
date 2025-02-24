from abc import ABC, abstractmethod
from typing import Dict, Any
from messages.action_messages.action_message import ActionMessage
from messages.message import Message
from resources.base_resource import BaseResource

class RunnableBaseResource(BaseResource):
    """
    Abstract base class for resources that can run messages and produce ActionMessages.
    Inherits from BaseResource and adds run functionality.
    """
    
    @abstractmethod
    def run(self, message: Message) -> ActionMessage:
        """
        Run the message through the resource and produce an ActionMessage.
        
        Args:
            message: The input message to process
            
        Returns:
            ActionMessage: The result of processing the input
        """
        pass