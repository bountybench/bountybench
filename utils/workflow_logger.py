import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from models.model_response import ModelResponse
from responses.response import Response
from responses.error_response import ErrorResponse

from .workflow_logger_types import (
    Action,
    AgentInteraction,
    WorkflowIteration,
    WorkflowLog,
    WorkflowMetadata,
)

class WorkflowLogger:
    _initialized = False

    def __init__(self):
        # Only initialize once
        if not WorkflowLogger._initialized:
            self.workflow_log = None
            self.log_file = None
            WorkflowLogger._initialized = True

    def initialize(
        self,
        workflow_name: str,
        logs_dir: str = "logs",
        task_repo_dir: Optional[str] = None,
        bounty_number: Optional[str] = None,
        model_config: Optional[Dict[str, Any]] = None,
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
                bounty_number=bounty_number,
                model_config=model_config
            ),
            iterations=[],
        )
        
        # Generate log filename
        components = [workflow_name]
        if task_repo_dir:
            components.append(Path(task_repo_dir).name)
        if bounty_number:
            components.append(str(bounty_number))
        if model_config and "model" in model_config:
            components.append(model_config["model"].replace("/", "_"))
            
        self.log_file = self.logs_dir / f"{'_'.join(components)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    def _ensure_initialized(self):
        """Ensure the logger is initialized before use"""
        if not self.workflow_log:
            raise RuntimeError("WorkflowLogger must be initialized before use. Call initialize() first.")

    def start_iteration(self, iteration_number: int) -> None:
        """Start a new workflow iteration"""
        self._ensure_initialized()
        if hasattr(self, 'current_iteration'):
            raise RuntimeError("Previous iteration not ended")
        
        self.current_iteration = WorkflowIteration(
            iteration_number=iteration_number,
            interactions=[],
            status="in_progress"
        )
    
    def start_interaction(self, agent_name: str, input_response: Response) -> None:
        """Start a new interaction within the current iteration"""
        self._ensure_initialized()
        if not hasattr(self, 'current_iteration'):
            raise RuntimeError("Must call start_iteration before logging interactions")
            
        self.current_interaction = AgentInteraction(
            agent_name=agent_name,
            input_response=input_response,
            output_response=None,
            start_time=datetime.now().isoformat(),
            end_time=None,
            actions=[],
            metadata={}
        )
    
    def log_action(
        self,
        action_name: str,
        input_data: Any,
        output_data: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an action within the current interaction"""
        self._ensure_initialized()
        if not hasattr(self, 'current_interaction'):
            raise RuntimeError("Must call start_interaction before logging actions")
            
        self.current_interaction.actions.append(
            Action(
                action_type=action_name,
                input_data=input_data,
                output_data=output_data,
                metadata=metadata
            )
        )
    
    def end_iteration(self, status: str) -> None:
        """End the current iteration and add it to the workflow log"""
        self._ensure_initialized()
        if not hasattr(self, 'current_iteration'):
            raise RuntimeError("No iteration in progress")
            
        self.current_iteration.status = status
            
        self.workflow_log.iterations.append(self.current_iteration)
        delattr(self, 'current_iteration')
        
        # Save after each iteration for durability
        self.save()
    
    def end_interaction(self, output_response: Response) -> None:
        """End the current interaction and add it to the current iteration"""
        self._ensure_initialized()
        if not hasattr(self, 'current_interaction'):
            raise RuntimeError("No interaction in progress")
            
        self.current_interaction.output_response = output_response
        self.current_interaction.end_time = datetime.now().isoformat()
        self.get_aggregate_metadata()

        self.current_iteration.interactions.append(self.current_interaction)
        delattr(self, 'current_interaction')
    
    def get_aggregate_metadata(self) -> None:
        """Get the aggregate metadata for the workflow"""
        if not hasattr(self, 'current_interaction'):
            raise RuntimeError("No interaction in progress")

        aggregate_metadata = {
            'input_tokens': 0,
            'output_tokens': 0,
            'time_taken_in_ms': 0
        }
        for action in self.current_interaction.actions:
            for key, value in action.metadata.items():
                if key in ['input_tokens', 'output_tokens', 'time_taken_in_ms']:
                    aggregate_metadata[key] += value
        self.current_interaction.metadata = aggregate_metadata

    def add_resource(self, resource_name: str) -> None:
        """Log a resource being used in the workflow"""
        self._ensure_initialized()
        if resource_name not in self.workflow_log.resources_used:
            self.workflow_log.resources_used.append(resource_name)
    
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
    
    def finalize(self, final_status: str = "completed") -> None:
        """Finalize the workflow log"""
        self._ensure_initialized()
        self.workflow_log.metadata.end_time = datetime.now().isoformat()
        self.workflow_log.final_status.append(final_status)
        self.save()
    
    def save(self) -> None:
        """Save the workflow log to a JSON file"""
        self._ensure_initialized()
        # Convert the workflow log to a dictionary
        log_dict = {
            "metadata": {
                "workflow_name": self.workflow_log.metadata.workflow_name,
                "start_time": self.workflow_log.metadata.start_time,
                "end_time": self.workflow_log.metadata.end_time,
                "task_repo_dir": self.workflow_log.metadata.task_repo_dir,
                "bounty_number": self.workflow_log.metadata.bounty_number,
                "model_config": self.workflow_log.metadata.model_config,
                "additional_metadata": self.workflow_log.metadata.additional_metadata
            },
            "resources_used": self.workflow_log.resources_used,
            "final_status": self.workflow_log.final_status,
            "iterations": [
                {
                    "iteration_number": it.iteration_number,
                    "status": it.status,
                    "interactions": [
                        {
                            "agent_name": inter.agent_name,
                            "input_response": inter.input_response.to_dict() if inter.input_response else None,
                            "output_response": inter.output_response.to_dict() if inter.output_response else None,
                            "start_time": inter.start_time,
                            "end_time": inter.end_time,
                            "actions": [
                                {
                                    "action_type": action.action_type,
                                    "input_data": action.input_data,
                                    "output_data": action.output_data,
                                    "timestamp": action.timestamp,
                                    "metadata": action.metadata
                                }
                                for action in inter.actions
                            ],
                            "metadata": inter.metadata
                        }
                        for inter in it.interactions
                    ]
                }
                for it in self.workflow_log.iterations
            ],
            "error_log": self.workflow_log.error_log
        }
        
        with open(self.log_file, 'w') as f:
            json.dump(log_dict, f, indent=4)

    class IterationContext:
        def __init__(self, logger: 'WorkflowLogger', iteration_number: int):
            self.logger = logger
            self.iteration_number = iteration_number

        def __enter__(self):
            self.logger.start_iteration(self.iteration_number)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            status = "failed" if exc_type else "completed"
            self.logger.end_iteration(status)
            return False  # Don't suppress exceptions

        def interaction(self, agent_name: str, input_response: Response):
            """Create a new interaction context within this iteration"""
            return self.logger.InteractionContext(self.logger, agent_name, input_response)

    class InteractionContext:
        def __init__(self, logger: 'WorkflowLogger', agent_name: str, input_response: Response):
            self.logger = logger
            self.agent_name = agent_name
            self.input_response = input_response
            self.output_response = None

        def __enter__(self):
            self.logger.start_interaction(self.agent_name, self.input_response)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type:
                # In case of exception, create an error response
                self.output_response = ErrorResponse(
                    answer=str(exc_val),
                    error=True,
                    metadata={"exception_type": exc_type.__name__}
                )
            elif not self.output_response:
                # If no output response was set, create a default one
                self.output_response = ErrorResponse(
                    answer="Interaction completed without explicit response",
                    error=False
                )
            self.logger.end_interaction(self.output_response)
            return False  # Don't suppress exceptions

        def set_output(self, output_response: Response):
            """Set the output response for this interaction"""
            self.output_response = output_response

        def log_action(self, action_name: str, input_data: Any, output_data: Any, metadata: Optional[Dict[str, Any]] = None):
            """Log an action within this interaction"""
            self.logger.log_action(action_name, input_data, output_data, metadata)

    def iteration(self, iteration_number: int) -> IterationContext:
        """Create a new iteration context"""
        return self.IterationContext(self, iteration_number)

workflow_logger = WorkflowLogger()