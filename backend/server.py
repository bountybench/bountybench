import asyncio
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
                pass #intentionally passing when shutting down, you intentionally cancel tasks (task.cancel()). This means asyncio.CancelledError is a natural consequence, not an error that needs escalation.
            except Exception as e:
                print(f"Error awaiting cancelled task: {e}")   
                raise e 
