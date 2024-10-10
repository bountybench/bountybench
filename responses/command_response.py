from responses.command_response_interface import  CommandResponseInterface

class SimpleCommandResponse:
    def __init__(self, response: str) -> None:
        self._response = response
 
    @property
    def response(self) -> str:
        return self._response

    @property
    def command(self) -> str:
        """
        either call
        parse_field('command')
        or do some metaprogramming i.e. get the name of the function and then pass that in automatically
        """
        return 'test'

class SimpleReflectResponse:
    def reflect(self) -> str:
        return 'test'


def test_simple_command_response_instance_is_subclass_of_CommandResponseInterface():
    instance_response = SimpleCommandResponse('test')
    assert issubclass(instance_response.__class__, CommandResponseInterface) is True

def test_simple_command_response_is_subclass_of_CommandResponseInterface():
    assert issubclass(SimpleCommandResponse, CommandResponseInterface) is True

def test_simple_reflect_response_instance_is_not_subclass_of_CommandResponseInterface():
    instance_response2 = SimpleReflectResponse()
    assert issubclass(instance_response2.__class__, CommandResponseInterface) is False

def test_simple_reflect_response_is_not_subclass_of_CommandResponseInterface():
    assert issubclass(SimpleReflectResponse, CommandResponseInterface) is False