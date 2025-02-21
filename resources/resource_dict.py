from collections import defaultdict

from resources.base_resource import BaseResource


class ResourceDict:
    def __init__(self):
        self.id_to_resource = defaultdict(dict)
        self.resource_type_to_resources = defaultdict(lambda: defaultdict(list))

    def count_total_resources_across_workflows(self):
        return sum(len(res_dict) for res_dict in self.id_to_resource.values())

    def count_resources_in_workflow(self, workflow_id: str) -> int:
        """Return the number of resources for a given workflow."""
        if workflow_id not in self.id_to_resource:
            raise KeyError(f"Workflow ID '{workflow_id}' does not exist.")
        return len(self.id_to_resource[workflow_id])

    def count_workflows(self) -> int:
        """Return the total number of workflows."""
        return len(self.id_to_resource)

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
                self.resource_type_to_resources[workflow_id][resource_type].remove(
                    resource
                )
            if not self.resource_type_to_resources[workflow_id][resource_type]:
                del self.resource_type_to_resources[workflow_id][resource_type]

    def resources_by_type(self, workflow_id: str, resource_type):
        if workflow_id not in self.id_to_resource:
            raise KeyError(f"Workflow ID '{workflow_id}' does not exist.")
        resource_name = resource_type.__name__
        if resource_name in self.resource_type_to_resources[workflow_id]:
            return self.resource_type_to_resources[workflow_id][resource_name]
        return []

    def delete_items_of_resource_type(self, workflow_id: str, resource_type):
        if workflow_id not in self.id_to_resource:
            raise KeyError(f"Workflow ID '{workflow_id}' does not exist.")
        resource_name = resource_type.__name__
        if resource_name in self.resource_type_to_resources[workflow_id]:
            for resource in self.resource_type_to_resources[workflow_id][resource_name]:
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
        if workflow_id not in self.id_to_resource:
            raise KeyError(f"Workflow ID '{workflow_id}' does not exist.")
        self.id_to_resource[workflow_id][resource_id] = resource
        self.resource_type_to_resources[workflow_id][type(resource).__name__].append(
            resource
        )


resource_dict = ResourceDict()
