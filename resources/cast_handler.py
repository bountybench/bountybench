from typing import List, Type
from messages.action_messages.action_message import ActionMessage
from resources.runnable_base_resource import RunnableBaseResource


class CastHandler:
    @staticmethod
    def get_compatible_resources(
        message: ActionMessage,
        available_resources: List[Type[RunnableBaseResource]]
    ) -> List[Type[RunnableBaseResource]]:
        """
        Determines which of the provided runnable resource types can handle the given ActionMessage.
        
        Args:
            message: The ActionMessage to check for compatibility
            available_resources: List of runnable resource types to check against
            
        Returns:
            List of compatible runnable resource types from the provided resources
        """
        return [
            resource_type for resource_type in available_resources
            if resource_type.can_handle_message(message)
        ]