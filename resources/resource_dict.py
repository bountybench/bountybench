from collections import defaultdict
from resources.resource import BaseResource

#does it inherit from dict?
# given this is a singleton, make it do little work besides 
# in future rather than __get_tiem,mabye separate and just a single instruction because of multithreading
class ResourceDict(dict):
    def __init__(self):
        self.id_to_resource = dict()
        self.resource_type_to_resources = defaultdict(list)

    def get_item_of_resource_type(self, resource_type):
        items = self.get_items_of_resource_type(resource_type)
        if items:
            return items[0]
        return None

    def get_items_of_resource_type(self, resource_type):
        resource_name = resource_type.__name__
        if resource_name in self.resource_type_to_resources:
            return self.resource_type_to_resources[resource_name]
        return []
    
    def delete_items_of_resource_type(self, resource_type):
        if resource_type in self.resource_type_to_resources:
            # Remove the resources from id_to_resource
            for resource in self.resource_type_to_resources[resource_type]:
                resource_id = resource.resource_id
                if resource_id in self.id_to_resource:
                    del self.id_to_resource[resource_id]
                    
            del self.resource_type_to_resources[resource_type]

    def delete_items(self, id):
        if id in self.id_to_resource:
            resource = self.id_to_resource[id]
            resource_type = type(resource).__name__ 
            del self.id_to_resource[id]
            if resource_type in self.resource_type_to_resources:
                self.resource_type_to_resources[resource_type].remove(resource)
                # If no more resources of this type, remove the key
                if not self.resource_type_to_resources[resource_type]:
                    del self.resource_type_to_resources[resource_type]

    def __getitem__(self, id):
        return self.id_to_resource[id]

    def __setitem__(self, id, value):
        # key must be an id, not a resource class
        # make sure to update both dicts each time
        self.id_to_resource[id] = value
        self.resource_type_to_resources[type(value).__name__].append(value)


resource_dict = ResourceDict()