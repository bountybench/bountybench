import asyncio
import signal

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from backend.routers import api_service, workflow_service, workflows


class Server:
    def __init__(self, app: FastAPI, websocket_manager, workflow_factory):
        self.app = app
        self.websocket_manager = websocket_manager
        self.workflow_factory = workflow_factory
        self.active_workflows = {}
        self.should_exit = False

        self.setup_middleware()
        self.setup_signal_handlers()

        workflows.setup_routes(
            self.app,
            self.workflow_factory,
            self.active_workflows,
            self.websocket_manager,
        )
        workflow_service.setup_routes(
            self.app, self.active_workflows, self.websocket_manager
        )
        api_service.setup_routes(self.app)

    def setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_signal_handlers(self):
        def handle_signal(signum, frame):
            print("\nShutdown signal received. Cleaning up...")
            self.should_exit = True

            try:
                # Try to get the existing event loop
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # If no loop is running, we don't create a new one
                # This avoids issues with atexit handlers
                return

            # Schedule the shutdown coroutine
            try:
                loop.create_task(self.shutdown())
            except Exception as e:
                print(f"Error scheduling shutdown: {e}")

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

    async def shutdown(self):
        """Gracefully shutdown the server with proper cleanup"""
        # Gather all cleanup tasks
        cleanup_tasks = []

        # Clean up all websocket connections
        for workflow_id in list(self.websocket_manager.active_connections.keys()):
            connections = list(self.websocket_manager.active_connections[workflow_id])
            for connection in connections:
                try:
                    cleanup_tasks.append(connection.close())
                except Exception as e:
                    print(f"Error closing connection: {e}")

        # Clean up heartbeat tasks
        for task in self.websocket_manager.heartbeat_tasks:
            task.cancel()
            cleanup_tasks.append(task)

        # Wait for all cleanup tasks to complete
        if cleanup_tasks:
            try:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            except Exception as e:
                print(f"Error during cleanup: {e}")

        # Let the event loop complete any remaining tasks
        try:
            loop = asyncio.get_running_loop()
            loop.stop()
        except Exception as e:
            print(f"Error stopping event loop: {e}")
