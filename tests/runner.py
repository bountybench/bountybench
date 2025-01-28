import os
import sys
import unittest

# Add the parent directory to the Python path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# from tests import test_workflow

# Import test modules
from tests.agents import (
    base_agent_test,
    config_default_test,
    executor_agent_test,
    patch_agent_git_test,
)
from tests.messages import message_test, rerun_manager_test
from tests.phases import base_phase_test, managers_test
from tests.resources import (  # resource_config_test,
    init_files_resource_test,
    kali_env_resource_test,
    kali_env_resource_tty_test,
    resource_manager_test,
    setup_resource_test,
)
from tests.resources.model_resource.service import test_api_key_service
from tests.utils import logger_test, progress_logger_test
from tests.workflows import base_workflow_test  # exploit_patch_workflow_test,

# Initialize the test suite
loader = unittest.TestLoader()
suite = unittest.TestSuite()

# Add tests to the test suite
test_modules = [
    base_agent_test,
    config_default_test,
    executor_agent_test,
    patch_agent_git_test,
    message_test,
    rerun_manager_test,
    base_phase_test,
    managers_test,
    init_files_resource_test,
    kali_env_resource_test,
    kali_env_resource_tty_test,
    # resource_config_test,
    resource_manager_test,
    setup_resource_test,
    test_api_key_service,
    logger_test,
    progress_logger_test,
    base_workflow_test,
    # exploit_patch_workflow_test,
    # test_workflow,
]

for module in test_modules:
    suite.addTests(loader.loadTestsFromModule(module))

if __name__ == "__main__":
    # Initialize a runner, pass it your suite and run it
    runner = unittest.TextTestRunner(verbosity=3)
    result = runner.run(suite)

    # Exit with non-zero code if there were failures
    sys.exit(not result.wasSuccessful())
