import os
import sys
import unittest

# Ensure the parent directory is on the path (so we can import "tests.*")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, PARENT_DIR)

# ------------------------------------------------------------------------------
# Import test modules
# ------------------------------------------------------------------------------
# Agents
from tests.agents import (
    test_base_agent,
    # test_patch_agent_git,
    # test_patch_agent_run_exploit,
    # test_patch_agent_verify,
    # test_executor_agent,
)

# Messages
from tests.messages import test_message  
# from tests.messages import test_rerun_manager

# Phases
from tests.phases import test_base_phase, test_managers  # if you want to add them

# Resources
from tests.resources import (
    test_init_files_resource,
    test_kali_env_resource,
    test_kali_env_resource_tty,
    test_resource_config,
    test_resource_manager,
    test_setup_resource
)
from tests.resources.model_resource import test_config_default

# UI/Backend
from tests.ui_backend import test_server

# Utils
from tests.utils import test_logger, test_progress_logger

# Workflows
from tests.workflows import test_base_workflow  
# from tests.workflows import test_exploit_patch_workflow

# ------------------------------------------------------------------------------
# List of test modules you want to run. Comment out anything you don't want.
# ------------------------------------------------------------------------------
test_modules = [
    test_base_agent,
    test_message,
    test_init_files_resource,
    test_kali_env_resource,
    test_kali_env_resource_tty,
    test_resource_config,
    test_resource_manager,
    test_logger,
    test_progress_logger,
    test_server
]

# Store test modules actually run for summary
executed_test_files = []

# ------------------------------------------------------------------------------
# Custom TestResult to print clear messages before/after each test
# ------------------------------------------------------------------------------
class PrintTestResult(unittest.TextTestResult):
    def startTest(self, test):
        super().startTest(test)
        test_name = self.getDescription(test)
        print("\n============================================================")
        print(f"Starting Test: {test_name}")
        print("============================================================")

    def stopTest(self, test):
        test_name = self.getDescription(test)
        print("------------------------------------------------------------")
        print(f"Finished Test: {test_name}")
        print("------------------------------------------------------------\n")
        super().stopTest(test)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        print(f"[SKIPPED] {self.getDescription(test)}: {reason}")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        print(f"[FAILED] {self.getDescription(test)}")

    def addError(self, test, err):
        super().addError(test, err)
        print(f"[ERROR] {self.getDescription(test)}")

# ------------------------------------------------------------------------------
# Custom TestRunner using our PrintTestResult
# ------------------------------------------------------------------------------
class PrintTestRunner(unittest.TextTestRunner):
    resultclass = PrintTestResult

# ------------------------------------------------------------------------------
# Function to create a suite of tests based on optionally changed files
# ------------------------------------------------------------------------------
def build_test_suite(changed_files=None):
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    global executed_test_files  # Track which test files were run

    if changed_files:
        relevant_modules = []
        for module in test_modules:
            module_file = getattr(module, '__file__', None)
            if module_file and any(changed_file in module_file for changed_file in changed_files):
                relevant_modules.append(module)

        for module in relevant_modules:
            executed_test_files.append(module.__file__)
            suite.addTests(loader.loadTestsFromModule(module))
    else:
        for module in test_modules:
            executed_test_files.append(module.__file__)
            suite.addTests(loader.loadTestsFromModule(module))

    return suite

# ------------------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    changed_files = sys.argv[1:]
    if changed_files:
        print(f"Detected changed files: {changed_files}", flush=True)
    else:
        print("No changed files specified. Running *all* tests.", flush=True)

    suite = build_test_suite(changed_files if changed_files else None)
    runner = PrintTestRunner(verbosity=3)
    result = runner.run(suite)

    # ----- Check if zero tests were actually run -----
    if result.testsRun == 0:
        print("\n==================== TEST RUN SUMMARY ====================")
        print("No tests were found or run!")
        sys.exit(0)

    # ----- Otherwise, proceed with the standard summary -----
    print("\n==================== TEST RUN SUMMARY ====================")

    # Print test files that were actually executed
    print("Test Files Run:")
    for file in executed_test_files:
        print(f"  - {file}")

    if result.skipped:
        print("\nSKIPPED TESTS:")
        for (test_case, reason) in result.skipped:
            print(f"  - {test_case}: {reason}")

    if result.failures:
        print("\nFAILED TESTS:")
        for (test_case, _) in result.failures:
            print(f"  - {test_case}")

    if result.errors:
        print("\nERRORS:")
        for (test_case, _) in result.errors:
            print(f"  - {test_case}")

    # If we have no failures or errors, we can say all tests passed:
    if not (result.failures or result.errors):
        print("\nAll tests passed successfully!")

    # Exit with non-zero code if there were failures or errors
    sys.exit(not result.wasSuccessful())