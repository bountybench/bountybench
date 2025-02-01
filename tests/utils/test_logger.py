from utils.logger import logger

def test_logger():
    logger.info("These are INFO messages")
    logger.info("These are INFO messages")
    logger.status("This is a general STATUS message")
    logger.info("These are INFO messages")
    logger.info("These are INFO messages")
    logger.info("These are INFO messages")
    logger.status("This is a success STATUS message", True)
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    logger.critical("This is a CRITICAL message")

if __name__ == "__main__":
    test_logger()