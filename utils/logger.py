import logging
import os
import queue
import sys
from logging.handlers import QueueHandler, QueueListener

import colorlog

# Custom logging levels
STATUS = 25  # between INFO and WARNING
SUCCESS_STATUS = 26  # just above STATUS
logging.addLevelName(STATUS, "STATUS")
logging.addLevelName(SUCCESS_STATUS, "SUCCESS_STATUS")


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
        self.base_dir = os.getcwd()  # Define the base directory for relative paths

    def format(self, record):
        """Compute the relative path of the log source."""
        try:
            record.relative_path = os.path.relpath(record.pathname, self.base_dir)
        except ValueError:
            # If relpath fails, fallback to pathname
            logging.warning(f"Failed to compute relative path for: {record.pathname}")
            record.relative_path = record.pathname

        # Ensure lineno is set
        record.lineno = record.lineno if hasattr(record, "lineno") else 0
        return super().format(record)


# Logging setup encapsulated in a class
class LoggerConfig:
    def __init__(self):
        self.log_queue = queue.Queue()
        self.queue_listener = self.configure_logging_thread()

    def configure_logging_thread(self):
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

        formatter = CustomColoredFormatter(
            "\r%(log_color)s%(asctime)s %(levelname)-8s [%(relative_path)s:%(lineno)d]%(reset)s\n%(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors=log_colors,
            reset=True,
            style="%",
        )

        handler = logging.StreamHandler()
        handler.setFormatter(formatter)

        queue_listener = QueueListener(
            self.log_queue, handler, respect_handler_level=True
        )
        queue_listener.start()
        return queue_listener

    def shutdown(self):
        """Shutdown the queue listener."""
        self.queue_listener.stop()

    def get_main_logger(self, name: str, level: int = logging.INFO) -> logging.Logger:
        """Get a logger instance with a QueueHandler."""
        logger = logging.getLogger(name)
        logger.setLevel(level)

        if not any(isinstance(h, QueueHandler) for h in logger.handlers):
            queue_handler = QueueHandler(self.log_queue)
            logger.addHandler(queue_handler)

        logger.propagate = False
        return logger


# Initialize the LoggerConfig to set up logging
logger_config = LoggerConfig()
get_main_logger = logger_config.get_main_logger
