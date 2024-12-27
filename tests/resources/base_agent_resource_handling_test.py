import unittest
from typing import List

from agents.base_agent import BaseAgent

# ----- Mocks and place-holder classes for demonstration -----

class BaseResource:
    """A placeholder base class for resources."""
    pass

class MockResource(BaseResource):
    """A mock resource class for testing."""

class MockResourceManager:
    """
    A minimal ResourceManager mock that stores resources in a dict.
    If a resource isn't found in the dict, KeyError is raised.
    """
    def __init__(self, resources):
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
    REQUIRED_RESOURCES = ["required_res"]
    OPTIONAL_RESOURCES = ["optional_res"]
    ACCESSIBLE_RESOURCES = ["required_res", "optional_res"]

    def run(self, responses: List[Response]) -> Response:
        # Implementation not important for this test
        return Response()


# ----- The Unit Tests -----

class TestBaseAgent(unittest.TestCase):

    def test_required_resource_present(self):
        """
        If the required resource is present, it should be bound to the agent.
        The optional resource is missing, so it should not be an attribute at all.
        """
        rm = MockResourceManager({
            "required_res": MockResource(),
            # "optional_res" is missing
        })
        agent = MyAgent(resource_manager=rm)
        agent.register_resources()

        # The required resource should exist
        self.assertTrue(hasattr(agent, "required_res"))
        self.assertIsInstance(agent.required_res, MockResource)

        # The optional resource is missing in rm => not set
        self.assertFalse(hasattr(agent, "optional_res"))

    def test_required_resource_missing_raises_keyerror(self):
        """
        If a required resource is missing, KeyError should be raised.
        """
        rm = MockResourceManager({})
        agent = MyAgent(resource_manager=rm)
        with self.assertRaises(KeyError):
            agent.register_resources()

    def test_optional_resource_present(self):
        """
        If the optional resource is also present, it should be bound.
        """
        rm = MockResourceManager({
            "required_res": MockResource(),
            "optional_res": MockResource()
        })
        agent = MyAgent(resource_manager=rm)
        agent.register_resources()

        self.assertTrue(hasattr(agent, "required_res"))
        self.assertTrue(hasattr(agent, "optional_res"))

    def test_accessible_not_subset_raises_valueerror(self):
        """
        If ACCESSIBLE_RESOURCES contains something that is not in
        REQUIRED_RESOURCES or OPTIONAL_RESOURCES, raise ValueError.
        """
        class BadAgent(BaseAgent):
            REQUIRED_RESOURCES = ["foo"]
            OPTIONAL_RESOURCES = []
            # 'bar' is not in required or optional
            ACCESSIBLE_RESOURCES = ["bar"]

            def run(self, responses: List[Response]) -> Response:
                return Response()

        rm = MockResourceManager({"foo": MockResource()})
        agent = BadAgent(resource_manager=rm)
        with self.assertRaises(ValueError) as ctx:
            agent.register_resources()
        self.assertIn("ACCESSIBLE_RESOURCES must be a subset", str(ctx.exception))

    def test_optional_resource_missing_no_error(self):
        """
        Missing optional resource should not raise KeyError, but the attribute
        also should not exist on the agent.
        """
        rm = MockResourceManager({
            "required_res": MockResource(),
            # 'optional_res' missing
        })
        agent = MyAgent(resource_manager=rm)
        # Should not raise
        agent.register_resources()

        self.assertTrue(hasattr(agent, "required_res"))
        self.assertFalse(hasattr(agent, "optional_res"))


if __name__ == "__main__":
    unittest.main()
