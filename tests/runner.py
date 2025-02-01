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
        """Prints a clear starting banner without duplication."""
        unittest.TestResult.startTest(self, test)
        test_name = self.getDescription(test)

        print("\n============================================================", flush=True)
        print(f"🚀 Starting Test: {test_name}", flush=True)

        doc = test.shortDescription()
        if doc:
            print(f"ℹ️  {doc}", flush=True)  # Print test description if provided
        
        print("============================================================", flush=True)

    def stopTest(self, test):
        """Prints a clean finish banner."""
        unittest.TestResult.stopTest(self, test)
        test_name = self.getDescription(test)

        print("------------------------------------------------------------", flush=True)
        print(f"✅ Finished Test: {test_name}", flush=True)
        print("------------------------------------------------------------\n", flush=True)

    def addSkip(self, test, reason):
        """Logs skipped tests clearly."""
        super().addSkip(test, reason)
        print(f"⚠️  [SKIPPED] {self.getDescription(test)}: {reason}", flush=True)

    def addFailure(self, test, err):
        """Logs failed tests."""
        super().addFailure(test, err)
        print(f"❌ [FAILED] {self.getDescription(test)}", flush=True)

    def addError(self, test, err):
        """Logs errors in tests."""
        super().addError(test, err)
        print(f"🔥 [ERROR] {self.getDescription(test)}", flush=True)

# ------------------------------------------------------------------------------
# Custom TestRunner using our PrintTestResult
# ------------------------------------------------------------------------------
class PrintTestRunner(unittest.TextTestRunner):
    """
    A TextTestRunner that uses our PrintTestResult to fully suppress the
    default 'test_name ...' output.
    """
    def _makeResult(self):
        return PrintTestResult(self.stream, self.descriptions, self.verbosity)

    def run(self, test):
        # If descriptions is True, unittest prints test names, so let's disable it
        self.descriptions = False
        return super().run(test)



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
    
    print("\n📌 **Test Execution Started**", flush=True)
    if changed_files:
        print(f"🔍 Detected changed files: {', '.join(changed_files)}\n", flush=True)
    else:
        print("🟢 No specific changed files. Running **all tests**.\n", flush=True)

    suite = build_test_suite(changed_files if changed_files else None)
    runner = PrintTestRunner(verbosity=3)
    result = runner.run(suite)

    # ----- Check if zero tests were actually run -----
    if result.testsRun == 0:
        print("\n===================== 🛑 TEST RUN SUMMARY =====================", flush=True)
        print("⚠️  **No tests were found or executed!**", flush=True)
        print("Make sure the changed files contain valid test cases.\n", flush=True)
        sys.exit(0)

    # ----- Otherwise, print the structured summary -----
    print("\n===================== 📊 TEST RUN SUMMARY =====================", flush=True)

    # Print test files that were actually executed
    print("\n📂 **Test Files Run:**", flush=True)
    for file in executed_test_files:
        print(f"   - 📄 `{file}`", flush=True)

    # Print skipped tests
    if result.skipped:
        print("\n⚠️  **Skipped Tests:**", flush=True)
        for (test_case, reason) in result.skipped:
            print(f"   - ❕ {test_case}: `{reason}`", flush=True)

    # Print failed tests
    if result.failures:
        print("\n❌ **Failed Tests:**", flush=True)
        for (test_case, _) in result.failures:
            print(f"   - 🔴 {test_case}", flush=True)

    # Print errored tests
    if result.errors:
        print("\n🔥 **Tests with Errors:**", flush=True)
        for (test_case, _) in result.errors:
            print(f"   - 🚨 {test_case}", flush=True)

    # If no failures or errors, show success message
    if not (result.failures or result.errors):
        print("\n✅ **All tests passed successfully!** 🎉", flush=True)

    print("\n============================================================\n", flush=True)

    # Exit with non-zero code if there were failures or errors
    sys.exit(not result.wasSuccessful())