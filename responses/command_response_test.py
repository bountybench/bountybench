import unittest
from command_response import  CommandResponseInterface
from response import parse_field

class SimpleCommandResponse:
    def __init__(self, response: str) -> None:
        self._response = response
 
    @property
    def response(self) -> str:
        return self._response

    @property
    def command(self) -> str:
        """
        Extract the 'command' field using parse_field and raise an exception if missing.
        [alternative was do some metaprogramming i.e. get the name of the function and then pass that in automatically]
        """
        command = parse_field(self._response, "command: ")
        if not command:
            raise Exception("Command is missing from the response.")
        return command

class SimpleReflectResponse:
    def reflect(self) -> str:
        return 'test'

class TestSimpleCommandResponse(unittest.TestCase):
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

    def test_command_raises_exception_when_missing(self):
        response = "observation: success"
        with self.assertRaises(Exception) as context:
            SimpleCommandResponse(response).command

        self.assertEqual(str(context.exception), "Command is missing from the response.")

if __name__ == '__main__':
    unittest.main()
