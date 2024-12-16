from collections import defaultdict
from resources.resource import BaseResource

#does it inherit from dict?
# given this is a singleton, make it do little work besides 
# in future rather than __get_tiem,mabye separate and just a single instruction because of multithreading

class ResourceDict(dict):
    def __init__(self):
        self.id_to_resource = dict()
        self.resource_type_to_resources = defaultdict(list)

    def get_items_of_resource_type(self, key):
        # if issubclass(key, BaseResource):
        if key in self.resource_type_to_resources:
            return self.resource_type_to_resources[key]
        return None
        # raise Exception("key is not a resource class")
 
    def delete_items_of_resource_type(self, key):
        if key in self.resource_type_to_resources:
            # Remove the resources from id_to_resource
            for resource in self.resource_type_to_resources[key]:
                resource_id = resource.resource_id
                if resource_id in self.id_to_resource:
                    del self.id_to_resource[resource_id]
                    
            del self.resource_type_to_resources[key]

    def delete_items(self, key):
        if key in self.id_to_resource:
            resource = self.id_to_resource[key]
            resource_type = type(resource) 
            del self.id_to_resource[key]
            if resource_type in self.resource_type_to_resources:
                self.resource_type_to_resources[resource_type].remove(resource)
                # If no more resources of this type, remove the key
                if not self.resource_type_to_resources[resource_type]:
                    del self.resource_type_to_resources[resource_type]

    def __getitem__(self, key):
        return self.id_to_resource[key]

    def __setitem__(self, key, value):
        # key must be an id, not a resource class
        # make sure to update both dicts each time
        self.id_to_resource[key] = value
        self.resource_type_to_resources[type(value)].append(value)

resource_dict = ResourceDict()