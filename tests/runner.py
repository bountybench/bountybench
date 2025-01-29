import os
import sys
import unittest

# Add the parent directory to the Python path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import test modules
from tests.agents import (
    test_base_agent,  # test_patch_agent_git, test_patch_agent_run_exploit, test_patch_agent_verify, test_executor_agent,
)
from tests.messages import test_message  # test_rerun_manager
from tests.phases import test_base_phase, test_managers
from tests.resources import (
    test_init_files_resource,
    test_kali_env_resource,
    test_kali_env_resource_tty,
    test_resource_config,
    test_resource_manager,
    test_setup_resource,
)
from tests.resources.model_resource import test_config_default
from tests.ui_backend import test_server
from tests.utils import test_logger, test_progress_logger
from tests.workflows import test_base_workflow  # test_exploit_patch_workflow

# Initialize the test suite
loader = unittest.TestLoader()
suite = unittest.TestSuite()

# Add tests to the test suite
test_modules = [
    test_base_agent,  # test_executor_agent,
    # test_patch_agent_git, test_patch_agent_run_exploit, test_patch_agent_verify,
    test_message,  # test_rerun_manager,
    # test_managers, test_base_phase,
    test_init_files_resource,
    test_kali_env_resource,
    test_kali_env_resource_tty,
    test_config_default,
    test_resource_config,
    test_resource_manager,
    test_setup_resource,
    test_logger,
    test_progress_logger,
    # test_base_workflow, test_exploit_patch_workflow,
    test_server,
]

for module in test_modules:
    suite.addTests(loader.loadTestsFromModule(module))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # If files are specified, only run tests for those files
        changed_files = sys.argv[1:]
        relevant_modules = []
        for module in test_modules:
            module_file = module.__file__
            if any(changed_file in module_file for changed_file in changed_files):
                relevant_modules.append(module)

        for module in relevant_modules:
            suite.addTests(loader.loadTestsFromModule(module))
    else:
        # If no files specified, run all tests
        for module in test_modules:
            suite.addTests(loader.loadTestsFromModule(module))

    # Initialize a runner, pass it your suite and run it
    runner = unittest.TextTestRunner(verbosity=3)
    result = runner.run(suite)

    # Exit with non-zero code if there were failures
    sys.exit(not result.wasSuccessful())
