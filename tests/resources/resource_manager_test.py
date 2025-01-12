import unittest
from unittest.mock import MagicMock, patch
from typing import Dict, Any, List, Union, Tuple

from agents.base_agent import BaseAgent
from phases.base_phase import BasePhase, PhaseConfig
from resources.base_resource import BaseResource, BaseResourceConfig
from resources.resource_manager import ResourceManager

class MockResourceConfig(BaseResourceConfig):
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

class MockResource(BaseResource):
    def __init__(self, resource_id, resource_config):
        super().__init__(resource_id, resource_config)
        self.initialized = True

    def stop(self):
        self.initialized = False

class MockAgent1(BaseAgent):
    REQUIRED_RESOURCES: List[Union[type, Tuple[type, str]]] = [
        (MockResource, "resource1"),
        (MockResource, "resource2")
    ]

class MockAgent2(BaseAgent):
    REQUIRED_RESOURCES: List[Union[type, Tuple[type, str]]] = [
        (MockResource, "resource2"),
        (MockResource, "resource3")
    ]

class MockPhase1(BasePhase):
    REQUIRED_AGENTS = [MockAgent1]

    @classmethod
    def get_required_resources(cls):
        return {"resource1", "resource2"}

class MockPhase2(BasePhase):
    REQUIRED_AGENTS = [MockAgent1, MockAgent2]

    @classmethod
    def get_required_resources(cls):
        return {"resource1", "resource2", "resource3"}

REQUIRED_PHASES = [MockPhase1, MockPhase2]

@patch("utils.logger.get_main_logger")
class TestResourceManager(unittest.TestCase):
    def setUp(self):
        self.resource_manager = ResourceManager()

    def test_resource_lifecycle(self, mock_logger):
        # Register resources
        for i in range(1, 4):
            self.resource_manager.register_resource(f"resource{i}", MockResource, MockResourceConfig())

        # Compute schedule
        self.resource_manager.compute_schedule(REQUIRED_PHASES)

        # Check resource lifecycle
        self.assertEqual(self.resource_manager._resource_lifecycle["resource1"], (0, 1))
        self.assertEqual(self.resource_manager._resource_lifecycle["resource2"], (0, 1))
        self.assertEqual(self.resource_manager._resource_lifecycle["resource3"], (1, 1))

        # Initialize resources for Phase1
        self.resource_manager.initialize_phase_resources(0)
        self.assertIn("resource1", self.resource_manager._resources)
        self.assertIn("resource2", self.resource_manager._resources)
        self.assertNotIn("resource3", self.resource_manager._resources)

        # Deallocate resources after Phase1
        self.resource_manager.deallocate_phase_resources(0)
        self.assertIn("resource1", self.resource_manager._resources)
        self.assertIn("resource2", self.resource_manager._resources)

        # Initialize resources for Phase2
        self.resource_manager.initialize_phase_resources(1)
        self.assertIn("resource1", self.resource_manager._resources)
        self.assertIn("resource2", self.resource_manager._resources)
        self.assertIn("resource3", self.resource_manager._resources)

        # Deallocate resources after Phase2
        self.resource_manager.deallocate_phase_resources(1)
        self.assertNotIn("resource1", self.resource_manager._resources)
        self.assertNotIn("resource2", self.resource_manager._resources)
        self.assertNotIn("resource3", self.resource_manager._resources)

    def test_get_resource(self, mock_logger):
        self.resource_manager.register_resource("resource1", MockResource, MockResourceConfig())
        self.resource_manager.register_resource("resource2", MockResource, MockResourceConfig())
        self.resource_manager.compute_schedule([MockPhase1])
        self.resource_manager.initialize_phase_resources(0)

        resource = self.resource_manager.get_resource("resource1")
        self.assertIsInstance(resource, MockResource)

        resource = self.resource_manager.get_resource("resource2")
        self.assertIsInstance(resource, MockResource)

        with self.assertRaises(KeyError):
            self.resource_manager.get_resource("non_existent_resource")

    def test_error_handling(self, mock_logger):
        # Test initializing resources without computing schedule
        with self.assertRaises(KeyError):
            self.resource_manager.initialize_phase_resources(0)

        # Register resource and compute schedule
        self.resource_manager.register_resource("resource1", MockResource, MockResourceConfig())
        self.resource_manager.register_resource("resource2", MockResource, MockResourceConfig())
        self.resource_manager.compute_schedule([MockPhase1])

        # Test with a mocked resource that raises an exception during initialization
        with patch.object(MockResource, '__init__', side_effect=Exception("Initialization error")):
            with self.assertRaises(Exception):
                self.resource_manager.initialize_phase_resources(0)

if __name__ == "__main__":
    unittest.main()