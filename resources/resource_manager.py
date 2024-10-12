from typing import Optional
from collections import defaultdict

#does it inherit from dict?
class ResourceDict():
    def __init__():
        self.id_to_resource = dict()
        self.resource_type_to_resources = defaultdict(list)

    def __get_item__(key):
        if key is a resource class:
            if self_resource_type_to_resources[key]:
                return self_resource_type_to_resources[key]
            return None
        # maybe check type of key, I think it a hashable
        elif if hashable:
            if key in id_to_resource:
                return.id_to_resource[key]
            else:
                return None
        else:
            raise Exception('unsupported type')

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
