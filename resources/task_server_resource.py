from resources.resource import BaseResource

class TaskServerResource(BaseResource):
    def __init__(self, task_repo_dir: str):
        self.resource_id = server_address 
        task_repo_dir
        "./start_docker.sh"
        resource_dict[self.resource_id] = self
        # how do we get back the server address?
        # Ans: set up start_docker.sh in a way that outputs the address in the last line, ideally automagically (infrastructurally)
        # how should we send it around (through the resource or through a response)

        # this will update the resource_dict

        # we have to have a taskserverresponse (we don't have to, but likely want to)
        # there may be many task servers, and each has its own id. also id should it be the repo or the server

    @property
    def server_address():
        return elf.resource_id
    @property
    def task_repo_dir():
        return self.task_repo_dir

    def stop():
        "./stop_docker.sh"

# task server response. 2 choices. 1) null. nullresponse 2) taskserverresponse that just contains "here's the task server and its address {addr}"