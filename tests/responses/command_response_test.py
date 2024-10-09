import unittest
from responses.command_response_interface import CommandResponseInterface
from responses.command_response import SimpleCommandResponse

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

    def test_command_extracts_correctly(self):
        response = "command: run_this_script"
        instance_response = SimpleCommandResponse(response)
        self.assertEqual(instance_response.command, "run_this_script")

if __name__ == '__main__':
    unittest.main()
