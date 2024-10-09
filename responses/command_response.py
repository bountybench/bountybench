from responses.command_response_interface import  CommandResponseInterface
from responses.response import parse_field

class SimpleCommandResponse:
    def __init__(self, response: str) -> None:
        self._response = response
 
    @property
    def response(self) -> str:
        return self._response

    @property
    def command(self) -> str:
        """
        Extract the 'command' field using parse_field or None if missing.
        [alternative was do some metaprogramming i.e. get the name of the function and then pass that in automatically]
        """
        command = parse_field(self._response, "command: ")
        if not command:
            return None
        return command

class SimpleReflectResponse:
    def reflect(self) -> str:
        return 'test'

def test_simple_command_response_instance_is_subclass_of_CommandResponseInterface(self):
    instance_response = SimpleCommandResponse('test')
    self.assertTrue(issubclass(instance_response.__class__, CommandResponseInterface))

def test_simple_command_response_is_subclass_of_CommandResponseInterface(self):
    self.assertTrue(issubclass(SimpleCommandResponse, CommandResponseInterface))

def test_simple_reflect_response_instance_is_not_subclass_of_CommandResponseInterface(self):
    class SimpleReflectResponse:
        def reflect(self) -> str:
            return 'test'
    instance_response2 = SimpleReflectResponse()
    self.assertFalse(issubclass(instance_response2.__class__, CommandResponseInterface))

def test_simple_reflect_response_is_not_subclass_of_CommandResponseInterface(self):
    class SimpleReflectResponse:
        def reflect(self) -> str:
            return 'test'
    self.assertFalse(issubclass(SimpleReflectResponse, CommandResponseInterface))

