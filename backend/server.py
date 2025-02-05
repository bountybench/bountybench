import asyncio
import signal
import sys

from starlette.middleware.cors import CORSMiddleware


class Server:
    def __init__(self, app, websocket_manager, workflow_factory: dict):
        self.app = app
        self.workflow_factory = workflow_factory
        self.active_workflows = {}
        self.websocket_manager = websocket_manager
        self.should_exit = False

        # Store shared state in app instance
        self.app.state.active_workflows = self.active_workflows
        self.app.state.workflow_factory = self.workflow_factory
        self.app.state.websocket_manager = self.websocket_manager
        self.app.state.should_exit = self.should_exit

        self.setup_middleware()
        self.setup_routes()

        self.app.add_event_handler("shutdown", self.shutdown)

        #self.setup_signal_handlers()

    def setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_routes(self):
        from backend.routers.api_service import api_service_router
        from backend.routers.workflow_service import workflow_service_router
        from backend.routers.workflows import workflows_router

        self.app.include_router(api_service_router)
        self.app.include_router(workflows_router)
        self.app.include_router(workflow_service_router)

    def setup_signal_handlers(self):
        """
        Use the asyncio event loop’s add_signal_handler so that shutdown is scheduled immediately.
        This avoids potential delays when using the standard signal.signal handler.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # If no running loop is found, get the default event loop.
            loop = asyncio.get_event_loop()

        # When SIGINT or SIGTERM is received, schedule the shutdown coroutine.
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda sig=sig: self._handle_signal(sig))

    def _handle_signal(self, sig):
        print(f"\nReceived signal {sig.name}. Shutting down immediately...")
        self.should_exit = True
        # Schedule the shutdown coroutine immediately
        asyncio.create_task(self.shutdown())

    '''
    async def shutdown(self):
        """Gracefully shutdown the server with proper cleanup"""
        # Gather cleanup tasks
        cleanup_tasks = []

        # Close all active websocket connections
        for workflow_id in list(self.websocket_manager.active_connections.keys()):
            connections = list(self.websocket_manager.active_connections[workflow_id])
            for connection in connections:
                try:
                    cleanup_tasks.append(connection.close())
                except Exception as e:
                    print(f"Error closing connection: {e}")

        # Cancel heartbeat tasks
        for task in self.websocket_manager.heartbeat_tasks:
            task.cancel()
            cleanup_tasks.append(task)

        if cleanup_tasks:
            try:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            except Exception as e:
                print(f"Error during cleanup: {e}")
                raise e
        
        # Stop the event loop safely
        try:
            loop = asyncio.get_running_loop()
            loop.stop()
        except RuntimeError as e:
            print(f"Error stopping event loop: {e}")
            raise
    '''

    async def shutdown(self):
        """Gracefully shutdown the server with proper cleanup"""
        # Close all active websocket connections
        for workflow_id in list(self.websocket_manager.active_connections.keys()):
            connections = list(self.websocket_manager.active_connections[workflow_id])
            for connection in connections:
                try:
                    await connection.close()
                except Exception as e:
                    print(f"Error closing connection: {e}")

        # Cancel heartbeat tasks
        for task in self.websocket_manager.heartbeat_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                print(f"Error: {e}")   
                raise e
            except Exception as e:
                print(f"Error awaiting cancelled task: {e}")   
                raise e 
