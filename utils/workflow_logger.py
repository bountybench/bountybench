import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from utils.logger import get_main_logger

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
            WorkflowLogger._initialized = True

        # Keep track of the current phase and iteration
        self.current_phase: Optional[WorkflowPhase] = None
        self.current_iteration: Optional[PhaseIteration] = None

    def initialize(
        self,
        workflow_name: str,
        logs_dir: str = "logs",
        task_repo_dir: Optional[str] = None,
        bounty_number: Optional[str] = None,
    ) -> None:
        """Initialize the workflow logger with the given parameters"""
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
        
        # Generate log filename
        components = [workflow_name]
        if task_repo_dir:
            components.append(Path(task_repo_dir).name)
        if bounty_number:
            components.append(str(bounty_number))
            
        self.log_file = self.logs_dir / f"{'_'.join(components)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

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

    def start_iteration(self, iteration_number: int, agent_name: str, input_response: Optional[Response]) -> None:
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
            input_response=input_response,
            output_response=None,
            start_time=datetime.now().isoformat(),
            end_time=None,
            actions=[],
            metadata={},
            status="in_progress",
        )

    def end_iteration(self, output_response: Response, status: str = "completed") -> None:
        """
        End the current iteration and add it to the current phase.
        """
        self._ensure_initialized()
        if not self.current_phase:
            raise RuntimeError("No phase in progress.")
        if not self.current_iteration:
            raise RuntimeError("No iteration in progress.")

        self.current_iteration.output_response = output_response
        self.current_iteration.end_time = datetime.now().isoformat()
        self.current_iteration.status = status
        self.get_aggregate_metadata()

        self.current_phase.iterations.append(self.current_iteration)
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
        
        self.current_iteration.actions.append(
            Action(
                action_type=action_name,
                input_data=input_data,
                output_data=output_data,
                metadata=metadata
            )
        )

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
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add additional metadata to the workflow"""
        self._ensure_initialized()
        self.workflow_log.metadata.additional_metadata[key] = value
    
    def add_agent(self, agent_name: str, agent) -> None:
        """
        Log an agent being used in the workflow and save its state.
        
        Args:
            agent_name (str): Name of the agent
            agent: Agent instance that has serialization methods
        """
        self._ensure_initialized()

        if agent_name not in self.workflow_log.agent_used and hasattr(agent, 'to_dict'):
            self.workflow_log.agent_used[agent_name] = agent.to_dict()

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

    
    def finalize(self, final_status: str = "completed") -> None:
        """Finalize the workflow log: mark the end time, record final status, and save."""
        self._ensure_initialized()
        self.workflow_log.metadata.end_time = datetime.now().isoformat()
        self.workflow_log.final_status.append(final_status)
        self.save()
    
    def save(self) -> None:
        """Save the workflow log to a JSON file"""
        self._ensure_initialized()
        # Convert the workflow log to a dictionary for JSON serialization
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
        
        with open(self.log_file, 'w') as f:
            json.dump(log_dict, f, indent=4)

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
            status = "failed" if exc_type else "completed"
            self.logger.end_phase(status, self.phase_instance)
            # If we return False, we do NOT suppress exceptions.
            return False

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
        Context manager for a single iteration within a phase.
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

        def __enter__(self):
            self.logger.start_iteration(self.iteration_number, self.agent_name, self.input_response)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            # If an exception happens, produce an ErrorResponse:
            if exc_type:
                self.output_response = ErrorResponse(
                    answer=str(exc_val),
                    error=True,
                    metadata={"exception_type": exc_type.__name__}
                )
            # If no output was set, create a default "no response" placeholder:
            elif not self.output_response:
                self.output_response = ErrorResponse(
                    answer="Iteration completed without explicit response",
                    error=False
                )
            self.logger.end_iteration(self.output_response, "failed" if exc_type else "completed")
            return False  # Don't suppress exceptions

        def set_output(self, output_response: Response):
            """Set the output response for this iteration"""
            self.output_response = output_response

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