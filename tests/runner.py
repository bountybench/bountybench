import os
import sys
import unittest

# ------------------------------------------------------------------------------
# Setup paths
# ------------------------------------------------------------------------------
# Determine the absolute path of the "tests" directory
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
# Determine the project root (one level up from "tests")
PROJECT_ROOT = os.path.abspath(os.path.join(TESTS_DIR, ".."))

# Ensure the project root is in sys.path for correct imports
sys.path.insert(0, PROJECT_ROOT)

# ------------------------------------------------------------------------------
# Custom TestResult to print clear banners before/after tests
# ------------------------------------------------------------------------------
class PrintTestResult(unittest.TextTestResult):
    def startTest(self, test):
        """Prints a banner before each test."""
        unittest.TestResult.startTest(self, test)
        test_name = self.getDescription(test)
        print("\n============================================================", flush=True)
        print(f"🚀 Starting Test: {test_name}", flush=True)
        doc = test.shortDescription()
        if doc:
            print(f"ℹ️  {doc}", flush=True)
        print("============================================================", flush=True)

    def addSuccess(self, test):
        super().addSuccess(test)
        self.stream.write("ok\n")
        self.stream.flush()

    def stopTest(self, test):
        """Prints a banner after each test."""
        unittest.TestResult.stopTest(self, test)
        test_name = self.getDescription(test)
        print("------------------------------------------------------------", flush=True)
        print(f"✅ Finished Test: {test_name}", flush=True)
        print("------------------------------------------------------------\n", flush=True)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        print(f"⚠️  [SKIPPED] {self.getDescription(test)}: {reason}", flush=True)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        print(f"❌ [FAILED] {self.getDescription(test)}", flush=True)

    def addError(self, test, err):
        super().addError(test, err)
        print(f"🔥 [ERROR] {self.getDescription(test)}", flush=True)

# ------------------------------------------------------------------------------
# Custom TestRunner using our PrintTestResult
# ------------------------------------------------------------------------------
class PrintTestRunner(unittest.TextTestRunner):
    def _makeResult(self):
        return PrintTestResult(self.stream, self.descriptions, self.verbosity)

    def run(self, test):
        self.descriptions = False
        return super().run(test)

# ------------------------------------------------------------------------------
# Custom TestLoader to filter out `.git`, `.github`, `wip_tests`
# ------------------------------------------------------------------------------
class CustomTestLoader(unittest.TestLoader):
    def _match_path(self, path, full_path, pattern):
        """Exclude unwanted directories during test discovery."""
        path_parts = full_path.split(os.sep)
        if any(part in {".git", ".github", "wip_tests"} for part in path_parts):
            return False
        return super()._match_path(path, full_path, pattern)

# ------------------------------------------------------------------------------
# Discover tests **ONLY** in `tests` directory
# ------------------------------------------------------------------------------
loader = CustomTestLoader()
# IMPORTANT: Set `start_dir=TESTS_DIR` instead of `"."` to limit discovery.
suite = loader.discover(start_dir=TESTS_DIR, pattern="test*.py", top_level_dir=PROJECT_ROOT)

# ------------------------------------------------------------------------------
# Helper: Get the list of test files executed
# ------------------------------------------------------------------------------
def get_executed_test_files(suite):
    test_files = set()
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            test_files.update(get_executed_test_files(test))
        else:
            module_name = test.__class__.__module__
            module = sys.modules.get(module_name)
            if module is not None:
                file = getattr(module, '__file__', None)
                if file and file.startswith(TESTS_DIR):
                    test_files.add(os.path.abspath(file))
    return test_files

executed_test_files = sorted(get_executed_test_files(suite))

# ------------------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    print("\n📌 **Test Execution Started**", flush=True)
    print("🟢 Running **all tests** in the tests directory.\n", flush=True)

    runner = PrintTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.testsRun == 0:
        print("\n===================== 🛑 TEST RUN SUMMARY =====================", flush=True)
        print("⚠️  **No tests were found or executed!**", flush=True)
        sys.exit(0)

    print("\n===================== 📊 TEST RUN SUMMARY =====================", flush=True)
    print("\n📂 **Test Files Run:**", flush=True)
    for file in executed_test_files:
        print(f"   - 📄 `{file}`", flush=True)

    if result.skipped:
        print("\n⚠️  **Skipped Tests:**", flush=True)
        for (test_case, reason) in result.skipped:
            print(f"   - ❕ {test_case}: `{reason}`", flush=True)

    if result.failures:
        print("\n❌ **Failed Tests:**", flush=True)
        for (test_case, _) in result.failures:
            print(f"   - 🔴 {test_case}", flush=True)

    if result.errors:
        print("\n🔥 **Tests with Errors:**", flush=True)
        for (test_case, _) in result.errors:
            print(f"   - 🚨 {test_case}", flush=True)

    if not (result.failures or result.errors):
        print("\n✅ **All tests passed successfully!** 🎉", flush=True)

    print("\n============================================================\n", flush=True)
    sys.exit(not result.wasSuccessful())