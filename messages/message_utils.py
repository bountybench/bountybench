import asyncio

from utils.websocket_manager import websocket_manager
from utils.logger import get_main_logger



logger = get_main_logger(__name__)


def broadcast_update(self, data: dict):
    """Send an update over WebSocket. This can be disabled or customized as desired."""
    try:
        loop = asyncio.get_running_loop()
        if not loop.is_running():
            return asyncio.run(_broadcast_update_async(data))
        else:
            task = asyncio.create_task(_broadcast_update_async(data))
            task.add_done_callback(lambda t: _handle_broadcast_error(t))
            return task
    except Exception as e:
        logger.error(f"Error in broadcast_update: {e}")

async def _broadcast_update_async(self, workflow_id, data: dict):
    if workflow_id:
        try:
            await websocket_manager.broadcast(workflow_id, data)
        except Exception as e:
            logger.error(f"[WorkflowLogger] Error broadcasting update: {e}")

def _handle_broadcast_error(task):
    try:
        task.result()
    except Exception as e:
        logger.error(f"[WorkflowLogger] Error in broadcast task: {e}")
