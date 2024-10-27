from typing import List
import unittest
from resources.base_resource import BaseResource
from resources.resource_dict import resource_dict
from agents.base_agent import BaseAgent
from responses.response import Response

class ResourceInitializationError(RuntimeError):
    def __init__(self, resource_name, agent_name):
        super().__init__(f"{resource_name} not set up. {agent_name} cannot start.")

class InitFilesResource(BaseResource):
    def __init__(self, resource_id: str) -> None:
        resource_dict[resource_id] = self
    def stop(args, kwargs):
        pass
class DockerResource(BaseResource):
    def __init__(self, resource_id: str):
        resource_dict[resource_id] = self

    def stop(args, kwargs):
        pass
class KaliEnvResource(BaseResource):
    def __init__(self, resource_id: str) -> None:
        resource_dict[resource_id] = self
    def stop(args, kwargs):
        pass
class TaskServerResource(BaseResource):
    def __init__(self, resource_id: str) -> None:
        resource_dict[resource_id] = self
    def stop(args, kwargs):
        pass       
class TestResourceRegistration(unittest.TestCase):

    def setUp(self):
        # Clear resource_dict before each test
        resource_dict.clear()

    def tearDown(self):
        # Clear resource_dict after each test
        resource_dict.clear()

    def test_successful_resource_registration(self):
        """Test that required resources are successfully registered in PatchAgent."""
        # Instantiate resources; start is mocked so no actual initialization occurs
        init_files = InitFilesResource("init-id")
        task_server = TaskServerResource("task-id")
        docker = DockerResource("docker-id")

        # Initialize PatchAgent and verify resources are correctly registered
        agent = PatchAgent()
        self.assertEqual(agent.init_files, init_files)
        self.assertEqual(agent.task_server, task_server)
        self.assertEqual(agent.docker, docker)
        resource_dict.delete_items("init-id")
        resource_dict.delete_items("task-id")
        resource_dict.delete_items("docker-id")

    def test_unsuccessful_resource_registration(self):
        """Test that required resources are successfully registered in PatchAgent."""
        init_files = InitFilesResource("init-id")
        task_server = TaskServerResource("task-id")

        with self.assertRaises(RuntimeError) as cm:
            agent = PatchAgent()

        # Assert that the exception message contains the expected text
        self.assertIn("Resource 'DockerResource' not set up", str(cm.exception))
        self.assertIn("PatchAgent cannot start", str(cm.exception))

class PatchAgent(BaseAgent):
    REQUIRED_RESOURCES = [InitFilesResource, TaskServerResource, DockerResource]
    def __init__(self, *args, **kwargs):
        super().__init__()
        
    def run(self, responses: List[Response]) -> Response:
        pass

# Run the tests
if __name__ == "__main__":
    unittest.main()
