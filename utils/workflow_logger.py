import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import asyncio
from functools import wraps

from utils.logger import get_main_logger
from .websocket_manager import websocket_manager

logger = get_main_logger(__name__)

from models.model_response import ModelResponse
from responses.response import Response
from responses.error_response import ErrorResponse

from .workflow_logger_types import (
    Action,
    PhaseIteration,
    WorkflowPhase,
    WorkflowLog,
    WorkflowMetadata,
)

class WorkflowLogger:
    _initialized = False

    def __init__(self):
        if not WorkflowLogger._initialized:
            self.workflow_log: Optional[WorkflowLog] = None
            self.log_file: Optional[Path] = None
            self.workflow_id: Optional[str] = None
            WorkflowLogger._initialized = True

        # Keep track of the current phase and iteration
        self.current_phase: Optional[WorkflowPhase] = None
        self.current_iteration: Optional[PhaseIteration] = None

    async def _broadcast_update(self, data: dict):
        """Broadcast update to WebSocket clients (internal)."""
        if self.workflow_id:
            try:
                print(f"Attempting to broadcast message type: {data.get('type')}")
                print(f"Full message data: {data}")
                await websocket_manager.broadcast(self.workflow_id, data)
                print(f"Successfully broadcasted message type: {data.get('type')}")
            except Exception as e:
                print(f"Error broadcasting update: {e}")
                print(f"Failed message data: {data}")

    async def broadcast_update(self, data: dict):
        """Async wrapper for broadcasting an update."""
        try:
            await self._broadcast_update(data)
        except Exception as e:
            print(f"Error in broadcast_update: {e}")

    def _handle_broadcast_error(self, task):
        """Handle any errors from the broadcast task."""
        try:
            task.result()
        except Exception as e:
            print(f"Error in broadcast task: {e}")

    async def initialize(
        self,
        workflow_name: str,
        workflow_id: Optional[str] = None,
        logs_dir: str = "logs",
        task_repo_dir: Optional[str] = None,
        bounty_number: Optional[str] = None,
    ) -> None:
        """Initialize the workflow logger with the given parameters."""
        self.workflow_name = workflow_name
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)
        
        # Initialize workflow log
        self.workflow_log = WorkflowLog(
            metadata=WorkflowMetadata(
                workflow_name=workflow_name,
                start_time=datetime.now().isoformat(),
                task_repo_dir=task_repo_dir,
                bounty_number=bounty_number
            ),
            phases=[],
        )
        
        # Use provided workflow ID or generate one
        self.workflow_id = workflow_id if workflow_id else f"{workflow_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Generate log filename
        components = [workflow_name]
        if task_repo_dir:
            components.append(Path(task_repo_dir).name)
        if bounty_number:
            components.append(str(bounty_number))
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = self.logs_dir / f"{'_'.join(components)}_{timestamp}.json"
        
        print(f"Initialized workflow logger with ID: {self.workflow_id}")

    async def start_phase(self, phase_idx: int, phase_name: str) -> None:
        """Create a new workflow phase."""
        self._ensure_initialized()
        if self.current_phase is not None:
            raise RuntimeError("A phase is already in progress. End it before starting a new one.")

        self.current_phase = WorkflowPhase(
            phase_idx=phase_idx,
            phase_name=phase_name,
            start_time=datetime.now().isoformat(),
            end_time=None,
            status="in_progress",
            iterations=[],
        )
        
        # Broadcast phase update
        await self.broadcast_update({
            "type": "phase_update",
            "phase": {
                "phase_idx": phase_idx,
                "phase_name": phase_name,
                "status": "in_progress"
            }
        })

    async def start_iteration(self, iteration_number: int, agent_name: str, input_response: Optional[Response]) -> None:
        """Start a new iteration within the current phase."""
        self._ensure_initialized()
        if not self.current_phase:
            raise RuntimeError("Must start_phase before starting iterations.")
        if self.current_iteration:
            raise RuntimeError("An iteration is already in progress. End it before starting a new one.")
            
        self.current_iteration = PhaseIteration(
            iteration_number=iteration_number,
            agent_name=agent_name,
            input_response=input_response,
            output_response=None,
            start_time=datetime.now().isoformat(),
            end_time=None,
            status="in_progress",
            actions=[],
            metadata={}
        )
        
        # Broadcast iteration update
        await self.broadcast_update({
            "type": "iteration_update",
            "iteration": {
                "iteration_number": iteration_number,
                "agent_name": agent_name,
                "status": "in_progress",
                "input": input_response.to_dict() if input_response else None
            }
        })

    async def log_action(
        self,
        action_name: str,
        input_data: Any,
        output_data: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an action within the current iteration."""
        self._ensure_initialized()
        if not self.current_iteration:
            print("Warning: Attempting to log action without active iteration")
            return

        print(f'Logging action: {action_name}')
        action = Action(
            action_type=action_name,
            input_data=input_data,
            output_data=output_data,
            metadata=metadata
        )
        
        self.current_iteration.actions.append(action)
        
        # Broadcast action update
        update_data = {
            "type": "action_update",
            "action": {
                "action_type": action_name,
                "input_data": input_data,
                "output_data": output_data,
                "metadata": metadata,
                "timestamp": action.timestamp
            }
        }
        print(f"Preparing to broadcast action update: {update_data}")
        await self.broadcast_update(update_data)

    async def end_iteration(self, output_response: Response, status: str = "completed") -> None:
        """End the current iteration and add it to the current phase."""
        self._ensure_initialized()
        if not self.current_phase:
            raise RuntimeError("No phase in progress.")
        if not self.current_iteration:
            raise RuntimeError("No iteration in progress to end.")
            
        self.current_iteration.end_time = datetime.now().isoformat()
        self.current_iteration.status = status
        self.current_iteration.output_response = output_response
        self.current_iteration.metadata = self.get_aggregate_metadata()
        
        self.current_phase.iterations.append(self.current_iteration)
        
        # Broadcast iteration completion
        await self.broadcast_update({
            "type": "iteration_update",
            "iteration": {
                "iteration_number": self.current_iteration.iteration_number,
                "agent_name": self.current_iteration.agent_name,
                "status": status,
                "output": output_response.to_dict() if output_response else None
            }
        })
        
        self.current_iteration = None
        await self.save()

    async def end_phase(self, status: str, phase_instance) -> None:
        """Finalize the current phase, append it to the list of phases, and reset."""
        self._ensure_initialized()
        if not self.current_phase:
            raise RuntimeError("No phase in progress to end.")
            
        self.current_phase.end_time = datetime.now().isoformat()
        self.current_phase.status = status
        self.current_phase.metadata = self.get_phase_metadata(phase_instance)
        
        self.workflow_log.phases.append(self.current_phase)
        
        # Broadcast phase completion
        await self.broadcast_update({
            "type": "phase_update",
            "phase": {
                "phase_idx": self.current_phase.phase_idx,
                "phase_name": self.current_phase.phase_name,
                "status": status
            }
        })
        
        self.current_phase = None
        await self.save()

    def _ensure_initialized(self):
        """Ensure the logger is initialized before use."""
        if not self.workflow_log:
            raise RuntimeError("WorkflowLogger must be initialized before use. Call initialize() first.")

    ################################################################
    # PHASE MANAGEMENT
    ################################################################

    def get_phase_metadata(self, phase_instance) -> Dict[str, Any]:
        """
        Aggregate certain metadata from the current phase
        into the phase's metadata field (e.g., phase_summary).
        """
        if not self.current_phase:
            raise RuntimeError("No phase in progress to gather metadata for.")

        metadata = {
            'phase_summary': phase_instance.phase_summary if phase_instance.phase_summary else "not_set",
            'iterations_used': phase_instance.iteration_count
        }

        return metadata

    ################################################################
    # ITERATION MANAGEMENT
    ################################################################

    def get_aggregate_metadata(self) -> Dict[str, int]:
        """
        Aggregate certain metadata from the current iteration's actions
        into the iteration's metadata field (e.g., token usage, time).
        """
        if not self.current_iteration:
            raise RuntimeError("No iteration in progress to gather metadata for.")

        aggregate_metadata = {
            'input_tokens': 0,
            'output_tokens': 0,
            'time_taken_in_ms': 0
        }
        for action in self.current_iteration.actions:
            if action.metadata:
                for key in ['input_tokens', 'output_tokens', 'time_taken_in_ms']:
                    if key in action.metadata:
                        aggregate_metadata[key] += action.metadata[key]
        return aggregate_metadata

    ################################################################
    # ERROR / METADATA / FINALIZE
    ################################################################
    async def log_error(self, error_msg: str, error_data: Optional[Dict[str, Any]] = None) -> None:
        """Log an error that occurred during the workflow."""
        self._ensure_initialized()
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": error_msg,
            **(error_data or {})
        }
        self.workflow_log.error_log.append(error_entry)
        await self.save()
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add additional metadata to the workflow (non-async)."""
        self._ensure_initialized()
        self.workflow_log.metadata.additional_metadata[key] = value
    
    def add_agent(self, agent_name: str, agent) -> None:
        """
        Log an agent being used in the workflow and save its state.
        """
        self._ensure_initialized()

        if agent_name not in self.workflow_log.agent_used and hasattr(agent, 'to_dict'):
            self.workflow_log.agent_used[agent_name] = agent.to_dict()

    def add_resource(self, resource_name: str, resource) -> None:
        """
        Log a resource being used in the workflow and save its state.
        """
        self._ensure_initialized()

        if resource_name not in self.workflow_log.resources_used and hasattr(resource, 'to_dict'):
            self.workflow_log.resources_used[resource_name] = resource.to_dict()

    async def finalize(self, final_status: str = "completed") -> None:
        """Finalize the workflow log: mark the end time, record final status, and save."""
        self._ensure_initialized()
        self.workflow_log.metadata.end_time = datetime.now().isoformat()
        self.workflow_log.final_status.append(final_status)
        await self.save()
    
    async def save(self) -> None:
        """Save the workflow log to a JSON file (async)."""
        self._ensure_initialized()
        log_dict = {
            "metadata": {
                "workflow_name": self.workflow_log.metadata.workflow_name,
                "start_time": self.workflow_log.metadata.start_time,
                "end_time": self.workflow_log.metadata.end_time,
                "task_repo_dir": self.workflow_log.metadata.task_repo_dir,
                "bounty_number": self.workflow_log.metadata.bounty_number,
                "additional_metadata": self.workflow_log.metadata.additional_metadata
            },
            "agent_used": self.workflow_log.agent_used,
            "resources_used": self.workflow_log.resources_used,
            "final_status": self.workflow_log.final_status,
            "phases": [
                {
                    "phase_idx": ph.phase_idx,
                    "phase_name": ph.phase_name,
                    "start_time": ph.start_time,
                    "end_time": ph.end_time,
                    "status": ph.status,
                    "metadata": ph.metadata,
                    "iterations": [
                        {
                            "iteration_number": it.iteration_number,
                            "agent_name": it.agent_name,
                            "status": it.status,
                            "input_response": it.input_response.to_dict() if it.input_response else None,
                            "output_response": it.output_response.to_dict() if it.output_response else None,
                            "start_time": it.start_time,
                            "end_time": it.end_time,
                            "actions": [
                                {
                                    "action_type": action.action_type,
                                    "input_data": action.input_data,
                                    "output_data": action.output_data,
                                    "timestamp": action.timestamp,
                                    "metadata": action.metadata
                                }
                                for action in it.actions
                            ],
                            "metadata": it.metadata
                        }
                        for it in ph.iterations
                    ]
                }
                for ph in self.workflow_log.phases
            ],
            "error_log": self.workflow_log.error_log
        }

        # Perform file I/O in a thread to avoid blocking the event loop
        def write_log():
            with open(self.log_file, 'w') as f:
                json.dump(log_dict, f, indent=4)

        await asyncio.to_thread(write_log)

    ################################################################
    # ASYNC CONTEXT MANAGERS
    ################################################################

    class PhaseContext:
        """
        Async context manager for a single phase. On enter: start_phase(...).
        On exit: end_phase(...).
        """
        def __init__(self, logger: 'WorkflowLogger', phase_instance):
            self.logger = logger
            self.phase_instance = phase_instance
            self.phase_idx = phase_instance.phase_config.phase_idx
            self.phase_name = phase_instance.phase_config.phase_name

        async def __aenter__(self):
            await self.logger.start_phase(self.phase_idx, self.phase_name)
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            status = "failed" if exc_type else "completed"
            await self.logger.end_phase(status, self.phase_instance)
            return False  # Do not suppress exceptions

        def iteration(self, iteration_number: int, agent_name: str, input_response: Optional[Response]):
            """
            Returns an iteration context within this phase.
            """
            return self.logger.IterationContext(
                self.logger,
                iteration_number,
                agent_name,
                input_response
            )

    class IterationContext:
        """
        Async context manager for a single iteration within a phase.
        On enter: start_iteration(...).
        On exit: end_iteration(...).
        """
        def __init__(
            self,
            logger: 'WorkflowLogger',
            iteration_number: int,
            agent_name: str,
            input_response: Optional[Response]
        ):
            self.logger = logger
            self.iteration_number = iteration_number
            self.agent_name = agent_name
            self.input_response = input_response
            self.output_response: Optional[Response] = None

        async def __aenter__(self):
            await self.logger.start_iteration(self.iteration_number, self.agent_name, self.input_response)
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if exc_type:
                self.output_response = ErrorResponse(
                    answer=str(exc_val),
                    error=True,
                    metadata={"exception_type": exc_type.__name__}
                )
            elif not self.output_response:
                self.output_response = ErrorResponse(
                    answer="Iteration completed without explicit response",
                    error=False
                )
            await self.logger.end_iteration(
                self.output_response,
                "failed" if exc_type else "completed"
            )
            return False

        def set_output(self, output_response: Response):
            """Set the output response for this iteration (synchronous setter)."""
            self.output_response = output_response

        async def log_action(
            self, 
            action_name: str,
            input_data: Any,
            output_data: Any,
            metadata: Optional[Dict[str, Any]] = None
        ):
            """Convenience helper: log an action to the current iteration."""
            await self.logger.log_action(action_name, input_data, output_data, metadata)

    def phase(self, phase_instance) -> PhaseContext:
        """Create a new phase context manager (async)."""
        return self.PhaseContext(self, phase_instance)


# Create a single global instance as before
workflow_logger = WorkflowLogger()
