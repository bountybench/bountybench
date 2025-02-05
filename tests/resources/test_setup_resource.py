import subprocess
from unittest.mock import patch

import pytest

from resources.setup_resource import SetupResource, SetupResourceConfig


@patch("resources.setup_resource.SetupResource.wait_until_all_containers_healthy")
def test_cleanup_on_initialization_failure(mock_wait_until_all_containers_healthy):
    """Test that cleanup happens if a runtime error occurs during initialization."""

    resource_id = "test_resource"

    # We expect RuntimeError to be raised due to container health check failing
    mock_wait_until_all_containers_healthy.return_value = False
    with pytest.raises(RuntimeError) as exc_info:
        SetupResource(
            resource_id,
            SetupResourceConfig(
                bounty_level_setup=False,
                task_dir="bountybench/lunary",
                bounty_number="0",
            ),
        )

    # Check if the error message contains the desired substring
    assert "Failed to wait until all containers healthy" in str(exc_info.value)

    # Verify no containers are left
    result = subprocess.run(
        ["docker", "ps"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    assert (
        "lunary-app" not in result.stdout and "lunary-postgres" not in result.stdout
    ), "Containers were not cleaned up properly."
