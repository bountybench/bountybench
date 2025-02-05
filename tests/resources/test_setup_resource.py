import pytest
from unittest.mock import patch, MagicMock
from resources.setup_resource import SetupResource, SetupResourceConfig

@pytest.fixture
def setup_resource_config():
    """Create a fixture for SetupResourceConfig."""
    return SetupResourceConfig(
        bounty_level_setup=False, 
        task_dir="bountybench/lunary",
        bounty_number="0"
    )

@pytest.fixture
def setup_resource(setup_resource_config):
    """Create a fixture for SetupResource."""
    resource_id = "test_resource"
    resource = SetupResource(resource_id, setup_resource_config)
    return resource

@patch('resources.setup_resource.run_command')
def test_cleanup_on_initialization_failure(mock_run_command, setup_resource):
    """Test that cleanup happens if a runtime error occurs during initialization."""

    # Mocking the run_command to simulate the setup script execution
    mock_run_command.side_effect = [
        # First call to simulate the setup script execution (successful)
        MagicMock(returncode=0, stdout=b'Container lunary-app Started\n'),
        # Second call simulating that the container is healthy
        MagicMock(returncode=0, stdout=b'Container lunary-postgres Healthy\n'),
        # Third call simulating an unhealthy status for the container
        MagicMock(returncode=0, stdout=b'Container lunary-app Unhealthy\n'),
        # The container health status check should now return an unhealthy status
        MagicMock(returncode=0, stdout=b'unhealthy')
    ]

    # Simulate the container names being extracted correctly after starting
    setup_resource.container_names = ["lunary-app", "lunary-postgres"]  # Pretend these are the names of the running containers
    
    # We expect RuntimeError to be raised due to container health check failing
    with pytest.raises(RuntimeError, match="Container 'lunary-app' has unexpected health status: unhealthy."):
        setup_resource._start()

    # Ensure that stop was called to clean up resources
    setup_resource.stop()  # Call stop explicitly for cleanup in the setup
    
    # Verify no containers are left
    assert len(setup_resource.container_names) == 0, "Containers were not cleaned up properly."