import os
from typing import Any, List, Tuple

import pytest
from _pytest.config import Config
from _pytest.nodes import Item
from _pytest.terminal import TerminalReporter

# ------------------------------------------------------------------------------
# Setup paths
# ------------------------------------------------------------------------------
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(TESTS_DIR, ".."))


# ------------------------------------------------------------------------------
# Custom Plugin
# ------------------------------------------------------------------------------
class PrettyReporter:
    """Custom reporter for prettier test output"""

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item: Item) -> None:
        """Print banner before and after each test"""
        # Before test
        print(
            "\n============================================================", flush=True
        )
        print(f"🚀 Starting Test: {item.name}", flush=True)
        if item.function.__doc__:
            print(f"ℹ️  {item.function.__doc__.strip()}", flush=True)
        print(
            "============================================================", flush=True
        )

        # Run the test
        yield

        # After test
        print(
            "------------------------------------------------------------", flush=True
        )
        print(f"✅ Finished Test: {item.name}", flush=True)
        print(
            "------------------------------------------------------------\n", flush=True
        )

    @pytest.hookimpl(hookwrapper=True)
    def pytest_terminal_summary(
        self, terminalreporter: TerminalReporter, exitstatus: int
    ) -> None:
        """Print custom summary at the end of test session"""
        yield

        print(
            "\n===================== 📊 TEST RUN SUMMARY =====================",
            flush=True,
        )

        # Print unique test files run
        unique_files = {
            report.location[0] for report in terminalreporter.stats.get("passed", [])
        }
        unique_files.update(
            report.location[0] for report in terminalreporter.stats.get("failed", [])
        )
        unique_files.update(
            report.location[0] for report in terminalreporter.stats.get("skipped", [])
        )
        unique_files.update(
            report.location[0] for report in terminalreporter.stats.get("error", [])
        )

        if unique_files:
            print("\n📂 **Test Files Run:**", flush=True)
            for file in sorted(unique_files):
                print(f"   - 📄 `{file}`", flush=True)

        # Print skipped tests
        if terminalreporter.stats.get("skipped", []):
            print("\n⚠️  **Skipped Tests:**", flush=True)
            for report in terminalreporter.stats["skipped"]:
                print(f"   - ❕ {report.nodeid}: `{report.longrepr[2]}`", flush=True)

        # Print failed tests
        if terminalreporter.stats.get("failed", []):
            print("\n❌ **Failed Tests:**", flush=True)
            for report in terminalreporter.stats["failed"]:
                print(f"   - 🔴 {report.nodeid}", flush=True)

        # Print error tests
        if terminalreporter.stats.get("error", []):
            print("\n🔥 **Tests with Errors:**", flush=True)
            for report in terminalreporter.stats["error"]:
                print(f"   - 🚨 {report.nodeid}", flush=True)

        # Print success message if no failures/errors
        if not (
            terminalreporter.stats.get("failed", [])
            or terminalreporter.stats.get("error", [])
        ):
            print("\n✅ **All tests passed successfully!** 🎉", flush=True)

        print(
            "\n============================================================\n",
            flush=True,
        )


# ------------------------------------------------------------------------------
# Plugin Registration
# ------------------------------------------------------------------------------
def pytest_configure(config: Config) -> None:
    """Register the custom reporter plugin"""
    reporter = PrettyReporter()
    config.pluginmanager.register(reporter, "pretty-reporter")


# ------------------------------------------------------------------------------
# Custom pytest.ini settings
# ------------------------------------------------------------------------------
def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--pretty",
        action="store_true",
        default=True,
        help="Enable pretty test output (default: enabled)",
    )


# ------------------------------------------------------------------------------
# Test Collection Customization
# ------------------------------------------------------------------------------
def pytest_ignore_collect(path, config):
    """Ignore certain directories during test collection"""
    ignored_dirs = {".git", ".github", "wip_tests"}
    return any(ignored in str(path) for ignored in ignored_dirs)


# # ------------------------------------------------------------------------------
# # Logging cleanup
# # ------------------------------------------------------------------------------
# @pytest.fixture(scope="session", autouse=True)
# def cleanup_logging():
#     """Ensure logger queue is properly shutdown after tests complete."""
#     yield
#     # Shutdown the logger queue listener to prevent "I/O operation on closed file" errors
#     from utils.logger import logger_config

#     logger_config.shutdown()
