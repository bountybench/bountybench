from typing import List
import unittest
from resources.base_resource import BaseResource
from resources.resource_dict import resource_dict
from agents.base_agent import BaseAgent
from responses.response import Response

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
    def test_successful_resource_registration(self):
        """Test that required resources are successfully registered in PatchAgent."""
        init_files = InitFilesResource("init-id")
        task_server = TaskServerResource("task-id")
        docker = DockerResource("docker-id")
        kali = KaliEnvResource("kali-id")

        patch_agent = PatchAgent()
        executor_agent = ExecutorAgent()
        self.assertEqual(patch_agent.init_files, init_files)
        self.assertEqual(patch_agent.task_server, task_server)
        self.assertEqual(patch_agent.docker, docker)
        self.assertEqual(executor_agent.kali_env, kali)
        
        with self.assertRaises(AttributeError) as cm:
            task_server_no_access = executor_agent.task_server
        
        self.assertIn("'ExecutorAgent' object has no attribute 'task_server'", str(cm.exception))

        resource_dict.delete_items("init-id")
        resource_dict.delete_items("task-id")
        resource_dict.delete_items("docker-id")
        resource_dict.delete_items("kali-id")

    def test_unsuccessful_resource_registration(self):
        """Test that required resources are successfully registered in PatchAgent."""
        init_files = InitFilesResource("init-id")
        task_server = TaskServerResource("task-id")

        with self.assertRaises(RuntimeError) as cm:
            agent = PatchAgent()

        self.assertIn("Resource 'DockerResource' not set up", str(cm.exception))
        self.assertIn("PatchAgent cannot start", str(cm.exception))
        resource_dict.delete_items("init-id")
        resource_dict.delete_items("task-id")

class PatchAgent(BaseAgent):
    REQUIRED_RESOURCES = [InitFilesResource, TaskServerResource, DockerResource]
    ACCESSIBLE_RESOURCES = [InitFilesResource, TaskServerResource, DockerResource]
    def __init__(self, *args, **kwargs):
        super().__init__()
        
    def run(self, responses: List[Response]) -> Response:
        pass

class ExecutorAgent(BaseAgent):
    REQUIRED_RESOURCES = [InitFilesResource, TaskServerResource, KaliEnvResource]
    ACCESSIBLE_RESOURCES = [KaliEnvResource]
    def __init__(self, *args, **kwargs):
        super().__init__()
        
    def run(self, responses: List[Response]) -> Response:
        pass

if __name__ == "__main__":
    unittest.main()
