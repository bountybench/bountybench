from responses.command_response_interface import  TaskServerResponseInterface

class TaskServerResponse(TaskServerResponseInterface):
    def __init__(self, response: str) -> None:
        self._response = response
        self._server_address = response

    @property
    def response(self) -> str:
        return self._response
 
    @property
    def server_address(self) -> str:
        return self._server_address
 
    @property
    def task_repo_dir(self) -> str:
        return self._server_address

