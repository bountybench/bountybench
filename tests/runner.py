import os
import sys
import pytest

# Add the parent directory to the Python path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# List of test files (relative paths)
test_files = ["test_calculator.py"
    #"tests/agents/test_base_agent.py",  # "tests/agents/test_executor_agent.py",
    # "tests/agents/test_patch_agent_git.py", "tests/agents/test_patch_agent_run_exploit.py", "tests/agents/test_patch_agent_verify.py",
    # "tests/messages/test_message.py", "tests/messages/test_rerun_manager.py",
    # "tests/phases/test_base_phase.py", "tests/phases/test_managers.py",
    #"tests/resources/test_init_files_resource.py",
    #"tests/resources/test_kali_env_resource.py",  # "tests/resources/test_kali_env_resource_tty.py",
    #"tests/resources/model_resource/test_config_default.py",  # "tests/resources/test_resource_manager.py", "tests/resources/test_setup_resource.py",
    #"tests/utils/test_logger.py",
    #"tests/utils/test_progress_logger.py",
    # "tests/workflows/test_base_workflow.py", "tests/workflows/test_exploit_patch_workflow.py",
    #"tests/ui_backend/test_server.py",
]

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # If specific files are passed, filter the test files
        changed_files = sys.argv[1:]
        relevant_tests = [
            test_file for test_file in test_files if any(changed_file in test_file for changed_file in changed_files)
        ]
    else:
        # Run all tests if no specific files are provided
        relevant_tests = test_files

    # Run pytest with the selected test files
    exit_code = pytest.main(relevant_tests)

    # Exit with the appropriate status code
    sys.exit(exit_code)