from typing import List, Type
from messages.action_messages.action_message import ActionMessage
from resources.runnable_base_resource import RunnableBaseResource
from resources.resource_manager import ResourceManager


class CastHandler:
    @staticmethod
    def get_compatible_resources_from_resource_manager(
        message: ActionMessage,
        resource_manager: ResourceManager
    ) -> List[Type[RunnableBaseResource]]:
        """
        Determines which of the provided runnable resource types can handle the given ActionMessage.
        
        Args:
            message: The ActionMessage to check for compatibility
            resource_manager: The ResourceManager to iterate through the existing resources and get the compatible ones fro a given message. 
            
        Returns:
            List of compatible runnable resource types from the provided resources
        """

        resources = resource_manager.get_resources()
        for resource_id, resource in resources.items():
            if type(resource) in 



        return [
            resource_type for resource_type in available_resources
            if resource_type.can_cast_message(message)
        ]
    


    
