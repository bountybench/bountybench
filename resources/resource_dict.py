from collections import defaultdict
from resources.base_resource import BaseResource 

class ResourceDict:
    def __init__(self):
        self.id_to_resource = defaultdict(dict)
        self.resource_type_to_resources = defaultdict(lambda: defaultdict(list))

    def __len__(self):
        return sum(len(res_dict) for res_dict in self.id_to_resource.values())

    def contains(self, workflow_id: str, resource_id: str) -> bool:
        if workflow_id not in self.id_to_resource: 
            raise KeyError(f"Workflow ID '{workflow_id}' does not exist.")
        return resource_id in self.id_to_resource[workflow_id]

    def delete_items(self, workflow_id: str, resource_id: str):
        if workflow_id not in self.id_to_resource:
            raise KeyError(f"Workflow ID '{workflow_id}' does not exist.")
        if resource_id in self.id_to_resource[workflow_id]:
            resource = self.id_to_resource[workflow_id][resource_id]
            resource_type = type(resource).__name__
            del self.id_to_resource[workflow_id][resource_id]
            if resource in self.resource_type_to_resources[workflow_id][resource_type]:
                self.resource_type_to_resources[workflow_id][resource_type].remove(resource)
            if not self.resource_type_to_resources[workflow_id][resource_type]:
                del self.resource_type_to_resources[workflow_id][resource_type]

    def delete_items_of_resource_type(self, workflow_id: str, resource_type: str):
        """
        Delete all resources of a given type from a specific workflow.
        """
        if workflow_id not in self.resource_type_to_resources:
            raise KeyError(f"Workflow ID '{workflow_id}' does not exist.")
        if resource_type in self.resource_type_to_resources[workflow_id]:
            # Get a list copy to avoid modifying while iterating.
            for resource in list(self.resource_type_to_resources[workflow_id][resource_type]):
                resource_id = resource.resource_id
                if resource_id in self.id_to_resource[workflow_id]:
                    del self.id_to_resource[workflow_id][resource_id]
            del self.resource_type_to_resources[workflow_id][resource_type]

    def get(self, workflow_id: str, resource_id: str):
        """Retrieve a resource by workflow id and resource id."""
        if workflow_id not in self.id_to_resource:
            raise KeyError(f"Workflow ID '{workflow_id}' does not exist.")
        return self.id_to_resource[workflow_id].get(resource_id)

    def set(self, workflow_id: str, resource_id: str, resource: BaseResource):
        """
        Set a resource under the given workflow id and resource id.
        Also appends the resource to the list under its type.
        """
        self.id_to_resource[workflow_id][resource_id] = resource
        self.resource_type_to_resources[workflow_id][type(resource).__name__].append(resource)  
        
resource_dict = ResourceDict()
