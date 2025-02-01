import asyncio
import logging

from utils.logger import logger


class SSELoggingHandler(logging.Handler):
    def __init__(self, log_queue: asyncio.Queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        log_entry = self.format(record)
        if record.levelname == "ERROR":
            log_entry = f"error: {log_entry}"
        asyncio.create_task(self.log_queue.put(log_entry))


log_queue = asyncio.Queue()
log_handler = SSELoggingHandler(log_queue)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
log_handler.setFormatter(formatter)

logger.addHandler(log_handler)
logger.setLevel(logging.INFO)
