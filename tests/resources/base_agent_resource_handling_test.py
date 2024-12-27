import unittest
from typing import List, Optional, Tuple, Type

from agents.base_agent import BaseAgent

# ----- Mocks and Place-holder Classes for Demonstration -----

class BaseResource:
    """A placeholder base class for resources."""
    def stop(self):
        """Abstract method to stop the resource."""
        raise NotImplementedError("Must implement stop method.")

class MockResource(BaseResource):
    """A mock resource class for testing."""
    def stop(self):
        """Implement the abstract stop method."""
        pass

class InitFilesResource(MockResource):
    """Mock InitFilesResource."""
    pass

class KaliEnvResource(MockResource):
    """Mock KaliEnvResource."""
    pass

class DockerResource(MockResource):
    """Mock DockerResource."""
    pass

class SetupResource(MockResource):
    """Mock SetupResource."""
    pass

class MockResourceManager:
    """
    A minimal ResourceManager mock that stores resources in a dict.
    If a resource isn't found in the dict, KeyError is raised.
    """
    def __init__(self, resources: dict):
        # resources: dict of resource_id -> resource_object
        self.resources = resources

    def get_resource(self, resource_id: str):
        if resource_id not in self.resources:
            raise KeyError(f"Resource '{resource_id}' not found.")
        return self.resources[resource_id]

class Response:
    """Placeholder for a Response base class."""
    pass

class ResponseHistory:
    """Placeholder for response history logic."""
    def is_repetitive(self, response: Response) -> bool:
        return False
    def log(self, response: Response):
        pass

class FailureResponse(Response):
    """A placeholder indicating a failure response."""
    def __init__(self, reason: str):
        self.reason = reason

# ----- A Concrete Agent for Testing -----

class MyAgent(BaseAgent):
    REQUIRED_RESOURCES = [
        InitFilesResource,      # Automatically creates `self.init_files`
        KaliEnvResource,        # Automatically creates `self.kali_env`
        DockerResource          # Automatically creates `self.docker`
    ]
    OPTIONAL_RESOURCES = [
        SetupResource           # Automatically creates `self.setup`
    ]
    ACCESSIBLE_RESOURCES = [
        SetupResource,          # Should be in REQUIRED or OPTIONAL
        InitFilesResource,
        KaliEnvResource,
        DockerResource
    ]

    def run(self, responses: List[Response]) -> Response:
        # Implementation not important for this test
        return Response()

class MyAgentWithCustomSetup(BaseAgent):
    REQUIRED_RESOURCES = [
        InitFilesResource,
        KaliEnvResource,
        DockerResource
    ]
    OPTIONAL_RESOURCES = [
        (SetupResource, "task_server"),    # Creates `self.task_server`
        (SetupResource, "repo_resource")   # Creates `self.repo_resource`
    ]
    ACCESSIBLE_RESOURCES = [
        (SetupResource, "task_server"),
        (SetupResource, "repo_resource"),
        InitFilesResource,
        KaliEnvResource,
        DockerResource
    ]

    def run(self, responses: List[Response]) -> Response:
        return Response()

# ----- The Unit Tests -----

class TestBaseAgent(unittest.TestCase):

    def test_required_resource_present(self):
        """
        If the required resources are present, they should be bound to the agent.
        The optional resource is missing, so it should not be an attribute at all.
        """
        rm = MockResourceManager({
            "init_files": InitFilesResource(),
            "kali_env": KaliEnvResource(),
            "docker": DockerResource(),
            # "setup" is missing
        })
        agent = MyAgent(resource_manager=rm)
        agent.register_resources()

        # The required resources should exist
        self.assertTrue(hasattr(agent, "init_files"))
        self.assertIsInstance(agent.init_files, InitFilesResource)

        self.assertTrue(hasattr(agent, "kali_env"))
        self.assertIsInstance(agent.kali_env, KaliEnvResource)

        self.assertTrue(hasattr(agent, "docker"))
        self.assertIsInstance(agent.docker, DockerResource)

        # The optional resource is missing in rm => not set
        self.assertFalse(hasattr(agent, "setup"))

    def test_required_resource_missing_raises_keyerror(self):
        """
        If a required resource is missing, KeyError should be raised.
        """
        rm = MockResourceManager({
            # "init_files" is missing
            "kali_env": KaliEnvResource(),
            "docker": DockerResource(),
        })
        agent = MyAgent(resource_manager=rm)
        with self.assertRaises(KeyError):
            agent.register_resources()

    def test_optional_resource_present(self):
        """
        If the optional resource is also present, it should be bound.
        """
        rm = MockResourceManager({
            "init_files": InitFilesResource(),
            "kali_env": KaliEnvResource(),
            "docker": DockerResource(),
            "setup": SetupResource()
        })
        agent = MyAgent(resource_manager=rm)
        agent.register_resources()

        self.assertTrue(hasattr(agent, "init_files"))
        self.assertTrue(hasattr(agent, "kali_env"))
        self.assertTrue(hasattr(agent, "docker"))
        self.assertTrue(hasattr(agent, "setup"))

    def test_accessible_not_subset_raises_valueerror(self):
        """
        If ACCESSIBLE_RESOURCES contains something that is not in
        REQUIRED_RESOURCES or OPTIONAL_RESOURCES, raise ValueError.
        """
        class BadAgent(BaseAgent):
            REQUIRED_RESOURCES = [
                InitFilesResource,
                KaliEnvResource,
                DockerResource
            ]
            OPTIONAL_RESOURCES = []
            # 'SetupResource' is accessible but not required or optional
            ACCESSIBLE_RESOURCES = [
                SetupResource,
                InitFilesResource,
                KaliEnvResource,
                DockerResource
            ]

            def run(self, responses: List[Response]) -> Response:
                return Response()

        rm = MockResourceManager({
            "init_files": InitFilesResource(),
            "kali_env": KaliEnvResource(),
            "docker": DockerResource(),
            "setup": SetupResource()
        })
        agent = BadAgent(resource_manager=rm)
        with self.assertRaises(ValueError) as ctx:
            agent.register_resources()
        self.assertIn("ACCESSIBLE_RESOURCES must be a subset", str(ctx.exception))

    def test_optional_resource_missing_no_error(self):
        """
        Missing optional resource should not raise KeyError, and the attribute
        should not exist on the agent.
        """
        rm = MockResourceManager({
            "init_files": InitFilesResource(),
            "kali_env": KaliEnvResource(),
            "docker": DockerResource(),
            # "task_server" and "repo_resource" are missing
        })
        agent = MyAgentWithCustomSetup(resource_manager=rm)
        # Should not raise
        agent.register_resources()

        self.assertTrue(hasattr(agent, "init_files"))
        self.assertTrue(hasattr(agent, "kali_env"))
        self.assertTrue(hasattr(agent, "docker"))

        # Optional resources with custom attribute names
        self.assertFalse(hasattr(agent, "task_server"))
        self.assertFalse(hasattr(agent, "repo_resource"))

    def test_optional_resource_present_with_custom_attr(self):
        """
        If the optional resource with custom attribute name is present, it should be bound.
        """
        rm = MockResourceManager({
            "init_files": InitFilesResource(),
            "kali_env": KaliEnvResource(),
            "docker": DockerResource(),
            "task_server": SetupResource(),
            "repo_resource": SetupResource()
        })
        agent = MyAgentWithCustomSetup(resource_manager=rm)
        agent.register_resources()

        self.assertTrue(hasattr(agent, "init_files"))
        self.assertTrue(hasattr(agent, "kali_env"))
        self.assertTrue(hasattr(agent, "docker"))
        self.assertTrue(hasattr(agent, "task_server"))
        self.assertTrue(hasattr(agent, "repo_resource"))

if __name__ == "__main__":
    unittest.main()