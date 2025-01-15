import asyncio
from functools import wraps
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from utils.websocket_manager import websocket_manager
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

from messages.message import Message
from messages.error_message import ErrorMessage

from .workflow_logger_types import (
    Action,
    PhaseIteration,
    WorkflowPhase,
    WorkflowLog,
    WorkflowMetadata,
)

def ensure_event_loop():
    """Ensure there's an event loop available in the current thread"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop

def run_async(func):
    """Decorator to run async functions from sync code"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        loop = ensure_event_loop()
        return loop.run_until_complete(func(*args, **kwargs))
    return wrapper

class WorkflowLogger:
    _initialized = False

    def __init__(self):
        if not WorkflowLogger._initialized:
            self.workflow_log: Optional[WorkflowLog] = None
            self.log_file: Optional[Path] = None
            self.worfklow_id: Optional[str] = None
            WorkflowLogger._initialized = True

        self.current_phase: Optional[WorkflowPhase] = None
        self.current_iteration: Optional[PhaseIteration] = None
    

    def reset_state(self):
        """Reset the workflow logger state when navigating away"""
        if self.current_phase:
            # Update phase status directly without using end_phase
            try:
                self.current_phase.status = "incomplete"
                self.current_phase.end_time = datetime.now().isoformat()
                if self.workflow_log and self.current_phase not in self.workflow_log.phases:
                    self.workflow_log.phases.append(self.current_phase)
                
                # Broadcast phase completion
                self.broadcast_update({
                    "type": "phase_update",
                    "phase": {
                        "phase_idx": self.current_phase.phase_idx,
                        "phase_name": self.current_phase.phase_name,
                        "status": "incomplete"
                    }
                })
            except Exception as e:
                logger.error(f"Error updating phase during reset: {e}")
                
        # Reset all state variables
        self.current_phase = None
        self.current_iteration = None
        WorkflowLogger._initialized = False
        
        # Broadcast reset event
        self.broadcast_update({
            "type": "workflow_reset",
            "message": "Workflow state has been reset"
        })
        
        
        logger.info("WorkflowLogger state has been reset")

    async def _broadcast_update(self, data: dict):
        """Broadcast update to WebSocket clients"""
        if self.workflow_id:
            try:
                print(f"Attempting to broadcast message type: {data.get('type')}")
                print(f"Full message data: {data}")
                await websocket_manager.broadcast(self.workflow_id, data)
                print(f"Successfully broadcasted message type: {data.get('type')}")
            except Exception as e:
                print(f"Error broadcasting update: {e}")
                print(f"Failed message data: {data}")

    def broadcast_update(self, data: dict):
        """Synchronous wrapper for _broadcast_update"""
        try:
            loop = asyncio.get_running_loop()
            if not loop.is_running():
                return asyncio.run(self._broadcast_update(data))
            else:
                # Create and store the task to prevent it from being dropped
                task = asyncio.create_task(self._broadcast_update(data))
                # Add a callback to handle any errors
                task.add_done_callback(lambda t: self._handle_broadcast_error(t))
                return task
        except Exception as e:
            print(f"Error in broadcast_update: {e}")

    def _handle_broadcast_error(self, task):
        """Handle any errors from the broadcast task"""
        try:
            # Get the result to raise any exceptions
            task.result()
        except Exception as e:
            print(f"Error in broadcast task: {e}")
            
    def deallocate(self):
        self.workflow_log: Optional[WorkflowLog] = None
        self.log_file: Optional[Path] = None
        self.worfklow_id: Optional[str] = None
        self.current_phase: Optional[WorkflowPhase] = None
        self.current_iteration: Optional[PhaseIteration] = None

    def initialize(
        self,
        workflow_name: str,
        workflow_id: Optional[str] = None,
        logs_dir: str = "logs",
        task: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.workflow_name = workflow_name
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)

        if self.current_phase is not None:
            self.reset_state()
        
        task = task or {}

        metadata_dict = {
            "workflow_name": workflow_name,
            "start_time": datetime.now().isoformat(),
            "phases_status":{}
        }

        if task:
            metadata_dict["task"] = task

        self.workflow_log = WorkflowLog(
            metadata=WorkflowMetadata(**metadata_dict),
            phases=[],
        )

        # Use provided workflow ID or generate one
        self.workflow_id = workflow_id if workflow_id else f"{workflow_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        

        components = [workflow_name]
        for _, value in task.items():
            if value:
                components.append(str(value.name if isinstance(value, Path) else value))

        self.log_file = self.logs_dir / f"{'_'.join(components)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        
        print(f"Initialized workflow logger with ID: {self.workflow_id}")

    def add_metadata(self, key: str, value: Any) -> None:
        if self.workflow_log is None:
            raise RuntimeError("WorkflowLogger not initialized")
        if not hasattr(self.workflow_log.metadata, "additional_metadata"):
            self.workflow_log.metadata.additional_metadata = {}
        self.workflow_log.metadata.additional_metadata[key] = value
        
    def _ensure_initialized(self):
        """Ensure the logger is initialized before use"""
        if not self.workflow_log:
            raise RuntimeError("WorkflowLogger must be initialized before use. Call initialize() first.")

    ################################################################
    # PHASE MANAGEMENT
    ################################################################

    def start_phase(self, phase_idx: int, phase_name: str) -> None:
        """Create a new workflow phase"""
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
        self.broadcast_update({
            "type": "phase_update",
            "phase": {
                "phase_idx": phase_idx,
                "phase_name": phase_name,
                "status": "in_progress"
            }
        })

    def end_phase(self, status: str, phase_instance) -> None:
        """
        Finalize the current phase, append it to the list of phases, and reset.
        """
        self._ensure_initialized()
        if not self.current_phase:
            raise RuntimeError("No phase in progress to end.")

        self.current_phase.status = status
        self.get_phase_metadata(phase_instance)
        self.current_phase.end_time = datetime.now().isoformat()
        self.workflow_log.phases.append(self.current_phase)
        # Broadcast phase completion
        self.broadcast_update({
            "type": "phase_update",
            "phase": {
                "phase_idx": self.current_phase.phase_idx,
                "phase_name": self.current_phase.phase_name,
                "status": status
            }
        })

        self.current_phase = None

        # For durability, save after each phase
        self.save()

    def get_phase_metadata(self, phase_instance) -> None:
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

        self.current_phase.metadata = metadata
    ################################################################
    # ITERATION MANAGEMENT
    ################################################################

    def start_iteration(self, iteration_number: int, agent_name: str, input_message: Optional[Message]) -> None:
        """
        Start a new iteration within the current phase.
        """
        self._ensure_initialized()
        if not self.current_phase:
            raise RuntimeError("Must start a phase before starting an iteration.")
        if self.current_iteration is not None:
            raise RuntimeError("A previous iteration was not ended properly.")

        self.current_iteration = PhaseIteration(
            iteration_number=iteration_number,
            agent_name=agent_name,
            input_message=input_message,
            output_message=None,
            start_time=datetime.now().isoformat(),
            end_time=None,
            actions=[],
            metadata={},
            status="in_progress",
        )
        
        # Broadcast iteration update
        self.broadcast_update({
            "type": "iteration_update",
            "iteration": {
                "iteration_number": iteration_number,
                "agent_name": agent_name,
                "status": "in_progress",
                "input": input_message.to_dict() if input_message else None
            }
        })

    def end_iteration(self, output_message: Message, status: str = "completed") -> None:
        """
        End the current iteration and add it to the current phase.
        """
        self._ensure_initialized()
        if not self.current_phase:
            raise RuntimeError("No phase in progress.")
        if not self.current_iteration:
            raise RuntimeError("No iteration in progress.")

        self.current_iteration.output_message = output_message
        self.current_iteration.end_time = datetime.now().isoformat()
        self.current_iteration.status = status
        self.get_aggregate_metadata()

        self.current_phase.iterations.append(self.current_iteration)
        # Broadcast iteration completion
        self.broadcast_update({
            "type": "iteration_update",
            "iteration": {
                "iteration_number": self.current_iteration.iteration_number,
                "agent_name": self.current_iteration.agent_name,
                "status": status,
                "output": output_message.to_dict() if output_message else None
            }
        })
        self.current_iteration = None

        # You could save after each iteration, but this might be too frequent:
        # self.save()

    def get_aggregate_metadata(self) -> None:
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
        self.current_iteration.metadata = aggregate_metadata

    ################################################################
    # ACTION LOGGING
    ################################################################

    def log_action(
        self,
        action_name: str,
        input_data: Any,
        output_data: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an action within the current interaction"""
        self._ensure_initialized()
        if not self.current_iteration:
            raise RuntimeError("Must start_iteration before logging actions.")
        
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
        self.broadcast_update(update_data)

    ################################################################
    # ERROR / METADATA / FINALIZE
    ################################################################
    def log_error(self, error_msg: str, error_data: Optional[Dict[str, Any]] = None) -> None:
        """Log an error that occurred during the workflow"""
        self._ensure_initialized()
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": error_msg,
            **(error_data or {})
        }
        self.workflow_log.error_log.append(error_entry)
        self.save()
    
    def add_agent(self, agent_name: str, agent) -> None:
        """
        Log an agent being used in the workflow and save its state.
        
        Args:
            agent_name (str): Name of the agent
            agent: Agent instance that has serialization methods
        """
        self._ensure_initialized()

        if agent_name not in self.workflow_log.agents_used and hasattr(agent, 'to_dict'):
            self.workflow_log.agents_used[agent_name] = agent.to_dict()

    def add_resource(self, resource_name: str, resource) -> None:
        """
        Log a resource being used in the workflow and save its state.
        
        Args:
            resource_name (str): Name of the resource
            resource: Resource instance that has serialization methods
        """
        self._ensure_initialized()

        if resource_name not in self.workflow_log.resources_used and hasattr(resource, 'to_dict'):
            self.workflow_log.resources_used[resource_name] = resource.to_dict()

    
    def add_phase_status(self, phase_name: str, phase_status: str) -> None:
        """
        Log a resource being used in the workflow and save its state.
        
        Args:
            phase_name (str): Name of the phase
            phase_status (str): status of phase
        """
        self._ensure_initialized()
        
        self.workflow_log.metadata.phases_status[phase_name] = phase_status

    def finalize(self, final_status: str) -> None:
        """Finalize the workflow log: mark the end time, record final status, and save."""
        self._ensure_initialized()
        self.workflow_log.metadata.end_time = datetime.now().isoformat()
        self.workflow_log.metadata.final_status = final_status
        self.save()
        return self.log_file
    
    def _json_serializable(self, obj: Any) -> Any:
        if isinstance(obj, Path):
            return str(obj)
        elif hasattr(obj, '__dict__'):
            # For objects with a __dict__ attribute (like Message),
            # we'll convert them to a dictionary
            return {key: self._json_serializable(value) for key, value in obj.__dict__.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._json_serializable(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._json_serializable(value) for key, value in obj.items()}
        elif hasattr(obj, '__str__'):
            # For any other objects, we'll use their string representation
            return str(obj)
        raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')

    def save(self) -> None:
        self._ensure_initialized()
        
        metadata_dict = {
            "workflow_name": self.workflow_log.metadata.workflow_name,
            "final_status": self.workflow_log.metadata.final_status,
            "phases_status": self.workflow_log.metadata.phases_status,
            "start_time": self.workflow_log.metadata.start_time,
            "end_time": self.workflow_log.metadata.end_time,
        }

        if hasattr(self.workflow_log.metadata, 'task'):
            metadata_dict["task"] = self.workflow_log.metadata.task

        log_dict = {
            "metadata": metadata_dict,
            "phases": [
                {
                    "name": phase.phase_name,
                    "start_time": phase.start_time,
                    "end_time": phase.end_time,
                    "status": phase.status,
                    "iterations": [
                        {
                            "iteration_number": iteration.iteration_number,
                            "agent_name": iteration.agent_name,
                            "status": iteration.status,
                            "input_message": self._format_message(iteration.input_message),
                            "actions": iteration.actions,
                            "output_message": self._format_message(iteration.output_message),
                            "start_time": iteration.start_time,
                            "end_time": iteration.end_time,
                            "metadata": iteration.metadata
                        } for iteration in phase.iterations
                    ]
                } for phase in self.workflow_log.phases
            ],
            "agents_used": self.workflow_log.agents_used,
            "resources_used": self.workflow_log.resources_used,
        }

        if hasattr(self.workflow_log.metadata, "additional_metadata"):
            log_dict["additional_metadata"] = self.workflow_log.metadata.additional_metadata
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.log_file, 'w') as f:
            json.dump(log_dict, f, indent=4, default=self._json_serializable)
            logger.status(f"Saved log to: {self.log_file}")

    def _format_message(self, message):
        if isinstance(message, dict) and '_message' in message:
            return {"message": message['_message']}
        elif isinstance(message, Message):
            return {"message": message.message}
        else:
            return message
    ################################################################
    # CONTEXT MANAGERS
    ################################################################

    class PhaseContext:
        """
        Context manager for a single phase. On enter: start_phase(...).
        On exit: end_phase(...).
        """
        def __init__(self, logger: 'WorkflowLogger', phase_instance):
            self.logger = logger
            self.phase_instance = phase_instance
            self.phase_idx = phase_instance.phase_config.phase_idx
            self.phase_name = phase_instance.phase_config.phase_name

        def __enter__(self):
            self.logger.start_phase(self.phase_idx, self.phase_name)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            status = "incomplete" if exc_type else "completed"
            self.logger.end_phase(status, self.phase_instance)
            # If we return False, we do NOT suppress exceptions.
            return False

        def iteration(self, iteration_number: int, agent_name: str, input_message: Optional[Message]):
            """
            Returns an iteration context within this phase.
            """
            return self.logger.IterationContext(
                self.logger,
                iteration_number,
                agent_name,
                input_message
            )

    class IterationContext:
        """
        Context manager for a single iteration within a phase.
        On enter: start_iteration(...).
        On exit: end_iteration(...).
        """
        def __init__(
            self,
            logger: 'WorkflowLogger',
            iteration_number: int,
            agent_name: str,
            input_message: Optional[Message]
        ):
            self.logger = logger
            self.iteration_number = iteration_number
            self.agent_name = agent_name
            self.input_message = input_message
            self.output_message: Optional[Message] = None

        def __enter__(self):
            self.logger.start_iteration(self.iteration_number, self.agent_name, self.input_message)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            # If an exception happens, produce an ErrorMessage:
            if exc_type:
                self.output_message = ErrorMessage(
                    answer=str(exc_val),
                    error=True,
                    metadata={"exception_type": exc_type.__name__}
                )
            # If no output was set, create a default "no message" placeholder:
            elif not self.output_message:
                self.output_message = ErrorMessage(
                    answer="Iteration completed without explicit message",
                    error=False
                )
            self.logger.end_iteration(self.output_message, "incomplete" if exc_type else "completed")
            return False  # Don't suppress exceptions

        def set_output(self, output_message: Message):
            """Set the output message for this iteration"""
            self.output_message = output_message

        def log_action(
            self, 
            action_name: str,
            input_data: Any,
            output_data: Any,
            metadata: Optional[Dict[str, Any]] = None
        ):
            """Convenience helper: log an action to the current iteration"""
            self.logger.log_action(action_name, input_data, output_data, metadata)

    def phase(self, phase_instance) -> PhaseContext:
        """Create a new phase context manager"""
        return self.PhaseContext(self, phase_instance)

workflow_logger = WorkflowLogger()