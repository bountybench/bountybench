from typing import Any, Dict, Optional, Callable, Awaitable
from pathlib import Path
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from .base_workflow import BaseWorkflow, WorkflowStatus, PhaseStatus
from messages.message import Message
from phase_messages.phase_message import PhaseMessage

class AsyncWorkflow(BaseWorkflow):
    """Async version of BaseWorkflow that supports interactive mode and websocket communication"""
    
    def __init__(self, **kwargs):
        logger.info("Initializing AsyncWorkflow")
        # Initialize broadcast_message and request_user_input as None
        # These will be set by the backend server
        self.broadcast_message: Optional[Callable[[str, Dict], Awaitable[None]]] = None
        self.request_user_input: Optional[Callable[[str, Dict], Awaitable[Dict]]] = None
        super().__init__(**kwargs)

    async def run_async(self) -> None:
        """Async version of run() that supports interactive mode"""
        logger.info("Starting run_async")
        if not self.broadcast_message:
            raise RuntimeError("broadcast_message not set. This should be set by the backend server.")
            
        await self.broadcast_message("workflow_start", {
            "workflow_name": self.name,
            "start_time": datetime.now().isoformat()
        })
        
        try:
            logger.info("Starting to run phases")
            async for phase_message in self._run_phases_async():
                logger.info(f"Phase completed: {self._current_phase.name if hasattr(self, '_current_phase') else None}")
                await self.broadcast_message("phase_complete", {
                    "phase_name": self._current_phase.name if hasattr(self, "_current_phase") else None,
                    "success": phase_message.success,
                    "messages": [msg.to_dict() for msg in phase_message.agent_messages] if phase_message else []
                })
                
            final_status = "success" if self.status == WorkflowStatus.COMPLETED_SUCCESS else "failure"
            logger.info(f"Workflow completed with status: {final_status}")
            await self.broadcast_message("workflow_complete", {
                "status": final_status,
                "end_time": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in run_async: {str(e)}", exc_info=True)
            await self.broadcast_message("error", {
                "error": str(e),
                "phase": self._current_phase.name if hasattr(self, "_current_phase") else None
            })
            raise

    async def _run_phases_async(self):
        """Async version of _run_phases()"""
        logger.info("Starting _run_phases_async")
        if not self._root_phase:
            raise ValueError("No root phase registered")

        self._set_workflow_status(WorkflowStatus.INCOMPLETE)
        current_phase = self._root_phase
        prev_phase_message = self._get_initial_phase_message()

        while current_phase:
            logger.info(f"Running phase: {current_phase.name}")
            self._current_phase = current_phase  # Store current phase for error handling
            await self.broadcast_message("phase_start", {
                "phase_name": current_phase.name,
                "start_time": datetime.now().isoformat()
            })
            
            self._set_phase_status(current_phase.name, PhaseStatus.INCOMPLETE)
            phase_message = await self._run_single_phase_async(current_phase, prev_phase_message)
            yield phase_message
            
            if phase_message.success:
                logger.info(f"Phase {current_phase.name} completed successfully")
                self._set_phase_status(current_phase.name, PhaseStatus.COMPLETED_SUCCESS)
            else:
                logger.warning(f"Phase {current_phase.name} failed")
                self._set_phase_status(current_phase.name, PhaseStatus.COMPLETED_FAILURE)

            if not phase_message.success or self._max_iterations_reached():
                break
                
            next_phases = self._phase_graph.get(current_phase, [])
            current_phase = next_phases[0] if next_phases else None
            prev_phase_message = phase_message

        if prev_phase_message.success:
            logger.info("Workflow completed successfully")
            self._set_workflow_status(WorkflowStatus.COMPLETED_SUCCESS)
        else:
            logger.warning("Workflow failed")
            self._set_workflow_status(WorkflowStatus.COMPLETED_FAILURE)

    async def _run_single_phase_async(self, phase, prev_phase_message: PhaseMessage) -> PhaseMessage:
        """Async version of _run_single_phase()"""
        logger.info(f"Running single phase async: {phase.name}")
        phase_instance = self._setup_phase(phase)
        
        try:
            if self.interactive:
                logger.info(f"Running phase {phase_instance.name} in interactive mode")
                return await phase_instance.run_interactive(
                    prev_phase_message,
                    request_user_input=self.request_user_input
                )
            else:
                logger.info(f"Running phase {phase_instance.name} in non-interactive mode")
                phase_message = await phase_instance.run_phase_async(prev_phase_message)
                self._workflow_iteration_count += 1
                return phase_message
                
        except Exception as e:
            logger.error(f"Error running phase {phase_instance.name}: {str(e)}", exc_info=True)
            raise