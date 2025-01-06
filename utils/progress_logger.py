import threading
import time
import sys
from utils.logger import get_main_logger

BOLD_BLACK = "\033[1;30m"
RESET = "\033[0m"

class ProgressLogger:
    def __init__(self, description, update_interval=0.5):
        self.description = description
        self.update_interval = update_interval
        self.is_running = False
        self.thread = None
        self.logger = get_main_logger(__name__)
        self.lock = threading.Lock()
        self.last_message = None

    def _progress_indicator(self):
        indicators = ['|', '/', '-', '\\']
        i = 0
        while self.is_running:
            with self.lock:
                message = f"\r{BOLD_BLACK}{self.description} {indicators[i]} (in progress){RESET}"
                sys.stdout.write(message)
                sys.stdout.flush()
            time.sleep(self.update_interval)
            i = (i + 1) % len(indicators)

    def start(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._progress_indicator)
        self.thread.start()

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join()
        with self.lock:
            sys.stdout.write(f"\r{BOLD_BLACK}{self.description} (completed){RESET}{'  '*10}\n")
            sys.stdout.flush()

    def log(self, message):
        with self.lock:
            if message != self.last_message:  # Only log if the message is different from the last one
                sys.stdout.write('\r' + ' '*80 + '\r')  # Clear the current line
                sys.stdout.write('\n')  # Move to the next line
                sys.stdout.flush()
                self.logger.info(message)
                sys.stdout.write('\n')  # Add another newline after the log message
                sys.stdout.write(f"\r{BOLD_BLACK}{self.description} (in progress){RESET}")  # Rewrite the progress message
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