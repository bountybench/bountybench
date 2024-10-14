from responses.task_server_response import TaskServerResponse
from agents.base_agent import BaseAgent
from resources.task_server_resource import TaskServerResource
from typing import List
from responses.response import Response

class TaskServerAgent(BaseAgent):
    task_repo_dir: str
    server_address: str

    def __init__(self, *args, **kwargs):
        super().__init(*args, **kwargs)

        if TaskServerResource in self.resource_dict:
            self.task_resource_env = self.resource_dict.get_items_of_resource_type(TaskServerResource)[0]
        else:
            task_resource = TaskServerResource(self.task_repo_dir, self.server_address)
            
            self.resource_dict[self.server_address] = task_resource 
            


    
    def run(self, responses: List[Response]) -> Response:
        return TaskServerResponse(self.server_address)