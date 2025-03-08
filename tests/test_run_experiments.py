import os

import pytest

from run_experiments import ExperimentRunner


@pytest.fixture
def runner():
    class MockExperimentRunner(ExperimentRunner):
        def _load_config(self, path):
            return {"workflow_type": "dummy"}

    return MockExperimentRunner("dummy_config.yaml", hold_terminals=False)


def print_groups(groups):
    print("\nGrouped tasks:")
    for group, tasks in groups.items():
        print(f"{group}: {tasks}")


def test_real_directories(runner):
    # Get the directory of the test file
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Move up one directory to reach the parent of 'tests'
    parent_dir = os.path.dirname(base_dir)

    dirs = ["bountybench/astropy", "bountybench/lunary", "bountybench/open-webui"]

    for dir in dirs:
        full_path = os.path.join(parent_dir, dir)
        ports = runner._get_ports(full_path)
        print(f"\nPorts for {dir}: {ports}")

    # Now test the ExperimentRunner's get_port method
    task_groups = {
        os.path.join(parent_dir, dir): [("cmd", [f"command for {dir}"])] for dir in dirs
    }

    result = runner.task_groups_port_constraints(task_groups)

    print("\nGrouped tasks:")
    for group, tasks in result.items():
        print(f"{group}: {tasks}")

    # Assertions
    assert len(result) == 2, "Expected 2 groups due to conflict between lunary and "

    # Check if lunary and open-webui are in the same group (they should be due to conflict)
    lunary_group = None
    open_webui_group = None
    for group, tasks in result.items():
        for task in tasks:
            if "lunary" in task[1][0]:
                lunary_group = group
            if "open-webui" in task[1][0]:
                open_webui_group = group

    assert (
        lunary_group == open_webui_group
    ), "lunary and open-webui should be in the same group due to port conflict"
    print(f"\nlunary and open-webui group: {lunary_group}")
    print("lunary and open-webui are in the same group (conflict detected)")

    # Check that astropy is in a different group
    astropy_group = None
    for group, tasks in result.items():
        for task in tasks:
            if "astropy" in task[1][0]:
                astropy_group = group
                break
        if astropy_group:
            break

    assert (
        astropy_group != lunary_group
    ), "astropy should be in a different group from lunary and open-webui"
    print(f"astropy group: {astropy_group}")
    print("astropy is in a different group (no conflict with lunary/open-webui)")


class MockExperimentRunner(ExperimentRunner):
    def __init__(self):
        self.port_map = {}

    def _get_ports(self, task_dir):
        return self.port_map.get(task_dir, [])


@pytest.fixture
def mock_runner():
    return MockExperimentRunner()


def print_groups(groups):
    print("\nGrouped tasks:")
    for group, tasks in groups.items():
        print(f"{group}: {tasks}")


def test_no_conflicts(mock_runner):
    mock_runner.port_map = {
        "task1": ["8000"],
        "task2": ["9000"],
        "task3": ["7000"],
    }
    task_groups = {
        "task1": [("cmd1", ["command1"])],
        "task2": [("cmd2", ["command2"])],
        "task3": [("cmd3", ["command3"])],
    }

    result = mock_runner.task_groups_port_constraints(task_groups)
    print_groups(result)

    assert len(result) == 3
    assert all(len(group) == 1 for group in result.values())


def test_single_conflict(mock_runner):
    mock_runner.port_map = {
        "task1": ["8000"],
        "task2": ["8000"],
        "task3": ["7000"],
    }
    task_groups = {
        "task1": [("cmd1", ["command1"])],
        "task2": [("cmd2", ["command2"])],
        "task3": [("cmd3", ["command3"])],
    }

    result = mock_runner.task_groups_port_constraints(task_groups)
    print_groups(result)

    assert len(result) == 2
    assert any(len(group) == 2 for group in result.values())


def test_multiple_conflicts(mock_runner):
    mock_runner.port_map = {
        "task1": ["8000"],
        "task2": ["8000", "9000"],
        "task3": ["9000"],
        "task4": ["7000"],
    }
    task_groups = {
        "task1": [("cmd1", ["command1"])],
        "task2": [("cmd2", ["command2"])],
        "task3": [("cmd3", ["command3"])],
        "task4": [("cmd4", ["command4"])],
    }

    result = mock_runner.task_groups_port_constraints(task_groups)
    print_groups(result)

    assert len(result) == 2
    assert any(len(group) == 3 for group in result.values())


def test_no_ports(mock_runner):
    mock_runner.port_map = {
        "task1": [],
        "task2": [],
        "task3": [],
    }
    task_groups = {
        "task1": [("cmd1", ["command1"])],
        "task2": [("cmd2", ["command2"])],
        "task3": [("cmd3", ["command3"])],
    }

    result = mock_runner.task_groups_port_constraints(task_groups)
    print_groups(result)

    assert len(result) == 3
    assert all(len(group) == 1 for group in result.values())
