from utils.logger import get_main_logger

def test_logger():
    logger = get_main_logger(__name__)

    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.status("This is a STATUS message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    logger.critical("This is a CRITICAL message")

if __name__ == "__main__":
    test_logger()