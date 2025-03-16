import sys
import threading
import time
from datetime import datetime, timedelta

from utils.logger import get_main_logger

CYAN = "\033[36m"
RESET = "\033[0m"


class ProgressLogger:
    def __init__(self, description, update_interval=0.2):
        self.description = description
        self.update_interval = update_interval
        self.is_running = False
        self.thread = None
        self.logger = get_main_logger(__name__)
        self.lock = threading.Lock()
        self.last_message = None
        self.start_time = None

    def _format_elapsed_time(self, elapsed):
        hours, remainder = divmod(elapsed.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02d}:{int(minutes):02d}:{seconds:05.2f}"

    def _progress_indicator(self):
        while self.is_running:
            with self.lock:
                elapsed_time = datetime.now() - self.start_time
                elapsed_str = self._format_elapsed_time(elapsed_time)
                message = f"\r{CYAN}{self.description} (elapsed: {elapsed_str}){RESET}"
                sys.stdout.write(message)
                sys.stdout.flush()
            time.sleep(self.update_interval)

    def start(self):
        self.is_running = True
        self.start_time = datetime.now()
        self.thread = threading.Thread(target=self._progress_indicator)
        self.thread.start()

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join()
        with self.lock:
            elapsed_time = datetime.now() - self.start_time
            elapsed_str = self._format_elapsed_time(elapsed_time)
            sys.stdout.write(
                f"\r{CYAN}{self.description} (completed in {elapsed_str}){RESET}{'  '*10}\n"
            )
            sys.stdout.flush()

    def log(self, message):
        with self.lock:
            if (
                message != self.last_message
            ):  # Only log if the message is different from the last one
                sys.stdout.write("\r" + " " * 80 + "\r")  # Clear the current line
                sys.stdout.write("\n")  # Move to the next line
                sys.stdout.flush()
                self.logger.info(message)
                sys.stdout.write("\n")  # Add another newline after the log message
                elapsed_time = datetime.now() - self.start_time
                elapsed_str = self._format_elapsed_time(elapsed_time)
                sys.stdout.write(
                    f"{CYAN}{self.description} (elapsed: {elapsed_str}){RESET}"
                )  # Rewrite the progress message
                sys.stdout.flush()
                self.last_message = message


# Global progress logger instance
current_progress = None


def start_progress(description):
    global current_progress
    if current_progress:
        current_progress.stop()
    current_progress = ProgressLogger(description)
    current_progress.start()


def stop_progress():
    global current_progress
    if current_progress:
        current_progress.stop()
        current_progress = None


def log_progress(message):
    global current_progress
    if current_progress:
        current_progress.log(message)
    else:
        logger = get_main_logger(__name__)
        logger.info(message)
