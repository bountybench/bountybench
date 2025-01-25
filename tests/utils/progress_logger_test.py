import time

from utils.progress_logger import log_progress, start_progress, stop_progress


def simulate_long_running_task():
    start_progress("Simulating a long-running task")
    try:
        for i in range(5):
            time.sleep(1)  # Simulate some work
            log_progress(f"Completed step {i+1} of 5")
    finally:
        stop_progress()


def simulate_quick_task():
    start_progress("Simulating a quick task")
    time.sleep(0.5)
    stop_progress()


def simulate_error_case():
    start_progress("Simulating an error case")
    try:
        time.sleep(1)
        raise Exception("Simulated error")
    except Exception as e:
        log_progress(f"An error occurred: {str(e)}")
    finally:
        stop_progress()


def test_progress_bar():
    print("Testing progress bar functionality:")

    print("\nTesting long-running task:")
    simulate_long_running_task()

    print("\nTesting quick task:")
    simulate_quick_task()

    print("\nTesting error case:")
    simulate_error_case()

    print("\nAll tests completed.")


if __name__ == "__main__":
    test_progress_bar()
