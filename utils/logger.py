import logging
import os

import colorlog

# Define new log level
STATUS = 25  # between INFO and WARNING
logging.addLevelName(STATUS, "STATUS")

class CustomLogger(logging.Logger):
    def status(self, msg, *args, **kwargs):
        if self.isEnabledFor(STATUS):
            self._log(STATUS, msg, args, **kwargs)

# Set the custom logger class as the default
logging.setLoggerClass(CustomLogger)

class CustomColoredFormatter(colorlog.ColoredFormatter):
    def __init__(self, fmt, datefmt=None, log_colors=None, reset=True, style='%'):
        super().__init__(fmt, datefmt=datefmt, log_colors=log_colors, reset=reset, style=style)
        # Define the base directory relative to which paths will be made relative
        self.base_dir = os.getcwd()  # You can set this to your project's root directory

    def format(self, record):
        # Compute the relative path
        try:
            record.relative_path = os.path.relpath(record.pathname, self.base_dir)
        except ValueError:
            # If relpath fails, fallback to pathname
            record.relative_path = record.pathname
        
        # Add line number to the record
        record.lineno = record.lineno
        return super().format(record)

def get_main_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    # Define color scheme
    log_colors = {
        'DEBUG': 'white',
        'INFO': 'bold_black',
        'STATUS': 'cyan',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }

    # Define the format for colored logs
    formatter = CustomColoredFormatter(
        "%(log_color)s%(asctime)s %(levelname)-8s [%(relative_path)s:%(lineno)d]%(reset)s\n%(message)s",
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors=log_colors,
        reset=True,
        style='%'
    )

    # Create a stream handler and set the formatter
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger.addHandler(handler)
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