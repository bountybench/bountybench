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
        if resource_type in self.resource_type_to_resources:
            return self.resource_type_to_resources[resource_type]
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
            resource_type = type(resource) 
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
        self.resource_type_to_resources[type(value)].append(value)


    """
    What exactly are we accomplishing here over just a dictionary.
    Maybe there's value in a dictionary that we call resourcemanager

    https://realpython.com/inherit-python-dict/#:~:text=In%20Python%2C%20you%20can%20do,the%20built%2Din%20dict%20class

    How to think about the task server vs agent env

    'name' of the resource?

    is a resource of type Browser there? how to do with dictionary

    access patterns:
        by name/id
            - this is necessary for cases of multiple task servers where you want to reach a specific server
        OR
        by resource type
            - this is useful for those when you jsut want any of this resource type (e.g. any kali linux work env or browser)

    in future:
        resources may have constaints, e.g. kali linux work env can only support x parallelism n cpu etc.
        say if resources are being used

        or even task server maybe can only support x api calls
    """
# Export globally / or maybe everyone can just import resource_dict. also mabye should make capital? 
resource_dict = ResourceDict()