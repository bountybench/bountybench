import os
import sys
import colorlog
import queue
import threading
import logging
from logging.handlers import QueueHandler, QueueListener

STATUS = 25  # between INFO and WARNING
SUCCESS_STATUS = 26  # just above STATUS
logging.addLevelName(STATUS, "STATUS")
logging.addLevelName(SUCCESS_STATUS, "SUCCESS_STATUS")

class CustomLogger(logging.Logger):
    def status(self, msg, success=False, *args, **kwargs):
        level = SUCCESS_STATUS if success else STATUS
        if self.isEnabledFor(level):
            # Get the caller's stack frame
            frame = sys._getframe(1)
            # Create a LogRecord with the correct stack info
            record = self.makeRecord(
                self.name, level, frame.f_code.co_filename, frame.f_lineno,
                msg, args, None, frame.f_code.co_name, kwargs
            )
            self.handle(record)

# Set the custom logger class as the default
logging.setLoggerClass(CustomLogger)

class CustomColoredFormatter(colorlog.ColoredFormatter):
    def __init__(self, fmt, datefmt=None, log_colors=None, reset=True, style='%'):
        super().__init__(fmt, datefmt=datefmt, log_colors=log_colors, reset=reset, style=style)
        # Define the base directory relative to which paths will be made relative
        self.base_dir = os.getcwd() 

    def format(self, record):
        # Compute the relative path
        try:
            record.relative_path = os.path.relpath(record.pathname, self.base_dir)
        except ValueError:
            # If relpath fails, fallback to pathname            
            logging.warning(f"Failed to compute relative path for: {record.pathname}")
            record.relative_path = record.pathname
        
        # Add line number to the record
        # Ensure lineno is set
        if not hasattr(record, 'lineno'):
            record.lineno = 0  
            
        return super().format(record)

# Create a shared logging queue
log_queue = queue.Queue()

# Function to configure the logging thread
def configure_logging_thread():
    log_colors = {
        'DEBUG': 'white',
        'INFO': 'cyan',
        'STATUS': 'bold_yellow',
        'SUCCESS_STATUS': 'bold_green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }

    # Define the format for colored logs
    formatter = CustomColoredFormatter(
        "\r%(log_color)s%(asctime)s %(levelname)-8s [%(relative_path)s:%(lineno)d]%(reset)s\n%(message)s",
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors=log_colors,
        reset=True,
        style='%'
    )

    # Create a stream handler and set the formatter
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    queue_listener = QueueListener(log_queue, handler, respect_handler_level=True)
    queue_listener.start()
    return queue_listener

queue_listener = configure_logging_thread()

def get_main_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not any(isinstance(h, QueueHandler) for h in logger.handlers):
        queue_handler = QueueHandler(log_queue)
        logger.addHandler(queue_handler)

    logger.propagate = False
    return logger

def get_separator_logger(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger('separator')
    logger.setLevel(level)
    separator_formatter = logging.Formatter('%(message)s')

    separator_handler = logging.StreamHandler()
    separator_handler.setFormatter(separator_formatter)
    logger.addHandler(separator_handler)
    logger.propagate = False
    return logger