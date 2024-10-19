import logging

import colorlog

def get_main_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    # Define color scheme
    log_colors = {
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }

    # Define the format for colored logs
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s %(levelname)-8s [%(module)s]%(reset)s\n%(message)s",
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