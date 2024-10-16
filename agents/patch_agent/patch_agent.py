import atexit
import logging
from typing import List, Tuple
from agents.base_agent import BaseAgent
from resources.init_files_resource import InitFilesResource
from resources.task_server_resource import TaskServerResource
from responses.command_response_interface import CommandResponseInterface
from responses.response import Response


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PatchAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__()
        # Check if there are TaskServerResource and InitFilesResource
        if InitFilesResource in self.resource_dict.resource_type_to_resources:
            self.init_files: InitFilesResource = self.resource_dict.get_items_of_resource_type(InitFilesResource)[0]
        else:
            logger.error("InitFilesResource not found in resource_dict. Terminating Patch Agent.")
            raise RuntimeError("InitFilesResource not set up. Patch agent cannot start.")
        
        if TaskServerResource in self.resource_dict.resource_type_to_resources:
            self.task_server: TaskServerResource = self.resource_dict.get_items_of_resource_type(TaskServerResource)[0]
        else:
            logger.error("TaskServerResource not found in resource_dict. Terminating Patch Agent.")
            raise RuntimeError("TaskServerResource not set up. Patch agent cannot start.")

        #TODO: Create a temporary branch for the original_files_dir on local machine
        self.create_git_branch()
        atexit.register(self.cleanup)

    def run(self, responses: List[Response]) -> Response:        
        if len(responses) != 1:
            return Exception(f'Accepts only a single response, you passed in {len(responses)} responses')
        response = responses[0]
        if issubclass(response.__class__, CommandResponseInterface):
            if self.get_git_diff() != "":
                return self.execute()
            else:
                return response
        else:
            raise Exception('Response not of an interpretable type. The response type is {response.__class__} but we expect a class of CommandResponseInterface')

    def execute(self) -> Response:
        """
        This function executes the patching command
        """
        diff = self.get_git_diff()
        self.create_git_patch(diff)
        self.create_git_commit() # This will commit the changes to the tmp directory

        res, msg = self.apply_git_patch(p2) # Apply the agent patch file (p2) to the tmp branch
        res, msg = self.apply_git_patch(p1) # Apply the flag patch file (p1) to the tmp branch
        if res:
            res = self.restart_task_server_resource()
            if res:
                flag = self.run_exploit()
                if flag:
                    # Patch succeed?
                    # Maybe just send back an AnswerResponse object?
                else:
                    # Patch failed
                    #TODO: what should we return in this case?

            else:
                #TODO: Handle the case where the task server resource is not restarted successfully; git reset

        else:
            #TODO: Handle the case where the patch is not applied successfully i.e. merge conflicts; I think it will make sense to just set the observation field.; git reset



        raise NotImplementedError

    def get_git_diff(self) -> str:
        """
        This function returns the git diff of the changes in the task repository
        """
        raise NotImplementedError
    
    def create_git_patch(self, diff: str) -> None:
        """
        This function creates a patch file from the diff
        """
        raise NotImplementedError

    def create_git_commit(self) -> None:
        """
        This function creates a git commit
        """
        raise NotImplementedError

    def create_git_branch(self) -> None:
        """
        This function creates a temporary branch on the local machine
        """
        raise NotImplementedError
    
    def apply_git_patch(self) -> Tuple[bool, str]:
        """
        This function applies the patch file to the target directory
        """
        # TODO: Remember to handle the case where the patch is not applied successfully
        raise NotImplementedError

    def cleanup(self) -> None:
        """
        This function cleans up the temporary branch etc.
        """
        raise NotImplementedError
