import logging
import queue
import sys
from collections import deque
from logging.handlers import QueueHandler, QueueListener
from pathlib import Path

import colorlog

# Custom logging levels
STATUS = 25  # between INFO and WARNING
SUCCESS_STATUS = 26  # just above STATUS
logging.addLevelName(STATUS, "STATUS")
logging.addLevelName(SUCCESS_STATUS, "SUCCESS_STATUS")

# Directory for full log files
FULL_LOG_DIR = Path.cwd() / "full_logs"
FULL_LOG_DIR.mkdir(parents=True, exist_ok=True)

FULL_LOG_FILE_PATH = FULL_LOG_DIR / "app.log"
if FULL_LOG_FILE_PATH.exists():
    FULL_LOG_FILE_PATH.unlink()  # Remove the existing log file if it exists


# Define LogBufferHandler
class LogBufferHandler(logging.Handler):
    """Custom logging handler that stores logs in a buffer."""

    def __init__(self, capacity=1000):
        super().__init__()
        self.log_buffer = deque(maxlen=capacity)

    def emit(self, record):
        log_entry = self.format(record)
        self.log_buffer.append(log_entry)

    def get_logs(self):
        return list(self.log_buffer)


class CustomLogger(logging.Logger):
    def status(self, msg, success=False, *args, **kwargs):
        """Log a message with a STATUS level."""
        level = SUCCESS_STATUS if success else STATUS
        if self.isEnabledFor(level):
            # Get the caller's stack frame
            frame = sys._getframe(1)
            # Create a LogRecord with the correct stack info
            record = self.makeRecord(
                self.name,
                level,
                frame.f_code.co_filename,
                frame.f_lineno,
                msg,
                args,
                None,
                frame.f_code.co_name,
                kwargs,
            )
            self.handle(record)


# Set the custom logger class as the default
logging.setLoggerClass(CustomLogger)


class CustomColoredFormatter(colorlog.ColoredFormatter):
    def __init__(self, fmt, datefmt=None, log_colors=None, reset=True, style="%"):
        super().__init__(
            fmt, datefmt=datefmt, log_colors=log_colors, reset=reset, style=style
        )
        self.base_dir = Path.cwd()  # Define the base directory for relative paths

    def format(self, record):
        """Compute the relative path of the log source."""
        try:
            record.relative_path = Path(record.pathname).relative_to(self.base_dir)
        except ValueError:
            # If relative_to fails, fallback to pathname
            logging.warning(f"Failed to compute relative path for: {record.pathname}")
            record.relative_path = record.pathname

        # Ensure lineno is set
        record.lineno = record.lineno if hasattr(record, "lineno") else 0
        return super().format(record)


# Logging setup encapsulated in a class
class LoggerConfig:
    def __init__(self):
        self.log_queue = queue.Queue()
        self.queue_listener = self._configure_logging_thread()
        self.log_buffer_handler = LogBufferHandler()

    def _configure_logging_thread(self):
        """Configure the logging thread with colored output."""
        log_colors = {
            "DEBUG": "white",
            "INFO": "cyan",
            "STATUS": "bold_yellow",
            "SUCCESS_STATUS": "bold_green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        }

        console_formatter = CustomColoredFormatter(
            "\r%(log_color)s%(asctime)s %(levelname)-8s [%(relative_path)s:%(lineno)d]%(reset)s\n%(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors=log_colors,
            reset=True,
            style="%",
        )

        file_formatter = logging.Formatter(
            "%(asctime)s %(levelname)-8s [%(relative_path)s:%(lineno)d] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)

        file_handler = logging.FileHandler(FULL_LOG_FILE_PATH, mode="a")
        file_handler.setFormatter(file_formatter)

        queue_listener = QueueListener(
            self.log_queue, console_handler, file_handler, respect_handler_level=True
        )
        queue_listener.start()
        return queue_listener

    def shutdown(self):
        """Shutdown the queue listener safely."""
        try:
            if self.queue_listener:
                self.queue_listener.stop()
        except Exception as e:
            logging.info(f"Logger shutdown: {e}")
        finally:
            self.queue_listener = None

    def restart(self):
        """Recreate a QueueListener with the FileHandlers defined in the helper."""
        try:
            if self.queue_listener:
                self.queue_listener.stop()
        except Exception as e:
            # Swallow shutdown errors (can happen at exit)
            logging.info(f"Logger restart: failed to stop old listener: {e}")
        self.queue_listener = self._configure_logging_thread()

    def get_main_logger(self, name: str, level: int = logging.DEBUG) -> logging.Logger:
        """Get a logger instance with a QueueHandler."""
        logger = logging.getLogger(name)
        logger.setLevel(level)

        if not any(isinstance(h, QueueHandler) for h in logger.handlers):
            queue_handler = QueueHandler(self.log_queue)
            logger.addHandler(queue_handler)
        if not any(isinstance(h, LogBufferHandler) for h in logger.handlers):
            logger.addHandler(self.log_buffer_handler)

        logger.propagate = False
        return logger


# Initialize the LoggerConfig to set up logging
logger_config = LoggerConfig()
get_main_logger = logger_config.get_main_logger
