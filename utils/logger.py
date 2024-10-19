import logging

def get_main_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    main_formatter = logging.Formatter(
        '%(asctime)s %(levelname)-5s [%(module)s] \n%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    main_handler = logging.StreamHandler()
    main_handler.setFormatter(main_formatter)
    logger.addHandler(main_handler)
    return logger

def get_separator_logger(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger('separator')
    logger.setLevel(level)
    separator_formatter = logging.Formatter('%(message)s')

    separator_handler = logging.StreamHandler()
    separator_handler.setFormatter(separator_formatter)
    logger.addHandler(separator_handler)
    return logger