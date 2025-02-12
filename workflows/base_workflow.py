from abc import ABC, abstractmethod
import asyncio
import atexit
from typing import Any, Dict, Type
from enum import Enum
from messages.message import Message
from messages.message_utils import message_dict
from messages.action_messages.action_message import ActionMessage
from messages.phase_messages.phase_message import PhaseMessage
from messages.rerun_manager import RerunManager
from messages.workflow_message import WorkflowMessage
from phases.base_phase import BasePhase
from resources.resource_manager import ResourceManager
from agents.agent_manager import AgentManager

from utils.logger import get_main_logger

logger = get_main_logger(__name__)

class WorkflowStatus(Enum):
    """Status of workflow execution"""
    INCOMPLETE = "incomplete"
    COMPLETED_SUCCESS = "completed_success"
    COMPLETED_FAILURE = "completed_failure"

class BaseWorkflow(ABC):
    status = WorkflowStatus.INCOMPLETE
    
    def __init__(self, **kwargs):
        logger.info(f"Initializing workflow {self.name}")
        self.params = kwargs
        self.interactive = kwargs.get('interactive', False)
        if kwargs.get("phase_iterations"):
            self.phase_iterations = kwargs.get("phase_iterations")
            
        self.max_iterations = 25
        self._current_phase_idx = 0
        self._workflow_iteration_count = 0
        self._phase_graph = {}  # Stores phase relationships
        self._root_phase = None
        self._current_phase = None

        self._initialize()
        
        self.initial_prompt=self._get_initial_prompt()

        self.workflow_message = WorkflowMessage(
            workflow_name=self.name,
            task=self.task,
            additional_metadata=self._get_metadata()
        )
        

        self._setup_resource_manager()
        self._setup_agent_manager()
        self._setup_rerun_manager()
        self._create_phases()
        self._compute_resource_schedule()
        logger.info(f"Finished initializing workflow {self.name}")
        
        self.next_iteration_event = asyncio.Event()
        
        atexit.register(self._finalize_workflow)
        
    def _finalize_workflow(self):
        self.workflow_message.save()

    def _register_root_phase(self, phase: BasePhase):
        """Register the starting phase of the workflow."""
        self._root_phase = phase
        self.register_phase(phase)
        logger.info(f"Registered root phase {phase.name}")

    def register_phase(self, phase: BasePhase):
        """Register a phase and its dependencies."""
        if phase not in self._phase_graph:
            self._phase_graph[phase] = []
            logger.debug(f"Registered phase: {phase.__class__.__name__}")
        
    @abstractmethod
    def _create_phases(self):
        """Create and register phases. To be implemented by subclasses."""
        pass

    @property
    def task(self):
        return self._get_task()
    
    def _create_phase(self, phase_class: Type[BasePhase], **kwargs: Any) -> None:
        """
        Create a phase instance and register it with the workflow.

        Args:
            phase_class (Type[BasePhase]): The class of the phase to create.
            **kwargs: Additional keyword arguments to pass to the phase constructor.

        Raises:
            TypeError: If the provided class is not a subclass of BasePhase.
        """
        if not issubclass(phase_class, BasePhase):
            raise TypeError(f"{phase_class.__name__} is not a subclass of BasePhase")

        phase_instance = phase_class(workflow=self, interactive=self.interactive, **kwargs)
        self.register_phase(phase_instance)
        logger.info(f"Created and registered phase: {phase_class.__name__}")
        
    @abstractmethod
    def _get_initial_prompt(self) -> str:
        """Provide the initial prompt for the workflow."""
        pass

    def _initialize(self):
        """Handles any task level setup pre-resource/agent/phase creation and sets additional params."""
        pass

    def _setup_agent_manager(self):
        self.agent_manager = AgentManager()
        logger.info("Setup agent manager")

    def _setup_resource_manager(self):
        self.resource_manager = ResourceManager()
        logger.info("Setup resource manager")

    def _setup_rerun_manager(self):
        self.rerun_manager = RerunManager(self.agent_manager, self.resource_manager)
        logger.info("Setup rerun manager")
        
    def _get_task(self) -> Dict[str, Any]:
        return {}
    
    def _get_metadata(self) -> Dict[str, Any]:
        return {}
    
    async def run(self) -> None:
        """Execute the entire workflow by running all phases in sequence."""
        logger.info(f"Running workflow {self.name}")
        async for _ in self._run_phases():
            continue

    async def _run_phases(self):
        prev_phase_message = None
        try:
            if not self._root_phase:
                raise ValueError("No root phase registered")

            self._current_phase = self._root_phase

            while self._current_phase:
                logger.info(f"Running {self._current_phase.name}")
                phase_message = await self._run_single_phase(self._current_phase, prev_phase_message)
                yield phase_message
                
                prev_phase_message = phase_message
                if not phase_message.success or self._max_iterations_reached():
                    break
                    
                next_phases = self._phase_graph.get(self._current_phase, [])
                self._current_phase = next_phases[0] if next_phases else None

            if prev_phase_message.success:
                self.workflow_message.set_summary(WorkflowStatus.COMPLETED_SUCCESS.value)
            else:
                self.workflow_message.set_summary(WorkflowStatus.COMPLETED_FAILURE.value)

        except Exception as e:
            self._handle_workflow_exception(e)

    async def _run_single_phase(self, phase: BasePhase, prev_phase_message: PhaseMessage) -> PhaseMessage:
        phase_instance = self._setup_phase(phase)
        for agent_name, agent in phase_instance.agents:
            self.workflow_message.add_agent(agent_name, agent)

        for resource_id, resource in phase_instance.resource_manager._resources.id_to_resource.items():
            self.workflow_message.add_resource(resource_id, resource)

        phase_message = await phase_instance.run(self.workflow_message, prev_phase_message)

        logger.status(f"Phase {phase.phase_config.phase_idx} completed: {phase.__class__.__name__} with success={phase_message.success}", phase_message.success)

        self._workflow_iteration_count += 1

        return phase_message

    async def add_user_message(self, user_input: str) -> str:
        result = await self._current_phase.add_user_message(user_input)
        
        # Trigger the next iteration
        self.next_iteration_event.set()
        
        return result
    
    async def get_last_message(self) -> str:
        result = self._current_phase.last_agent_message  
        return result.message if result else ""
    
    def _max_iterations_reached(self) -> bool:
        return self._workflow_iteration_count >= self.max_iterations

    def _handle_workflow_exception(self, exception: Exception):
        raise exception

    def _setup_phase(self, phase: BasePhase) -> BasePhase:
        try:
            logger.info(f"Setting up phase {phase.__class__.__name__}")
            phase.setup()
            return phase
        except Exception as e:
            logger.error(f"Failed to set up phase: {e}")
            raise

    def _compute_resource_schedule(self):
        """
        Compute the agent (which will compute resource) schedule across all phases.
        """
        phases = self._phase_graph.keys()
        self.resource_manager.compute_schedule(phases)
        logger.debug("Computed resource schedule for all phases based on agents.")

    def register_phase(self, phase: BasePhase):
        if phase not in self._phase_graph:
            self._phase_graph[phase] = []
            phase.phase_config.phase_idx = len(self._phase_graph) - 1
            logger.debug(f"Registered phase { phase.phase_config.phase_idx}: {phase.__class__.__name__}")
            logger.info(f"{phase.phase_config.phase_name} registered")

    async def get_last_message(self) -> str:
        result = self._current_phase.last_agent_message  
        return result.message if result else ""
      
    async def rerun_message(self, message_id: str):
        workflow_messages = message_dict.get(self.workflow_message.workflow_id, {})
        message = workflow_messages.get(message_id)
        message = await self.rerun_manager.rerun(message)        
        if message.next:
            message = await self.rerun_manager.run_edited(message)
            message = message.next
        if isinstance(message, ActionMessage):
            while message.next:
                message = await self.rerun_manager.run_edited(message)
                message = message.next
        return message
    
    async def run_next_message(self):
        workflow_messages = message_dict.get(self.workflow_message.workflow_id, {})
        if len(workflow_messages) > 0:
            _, last_message = list(workflow_messages.items())[-1]
            if last_message.next:
                last_message = await self.rerun_manager.rerun(last_message)
                return last_message
            if last_message.parent and last_message.parent.next:
                last_message = await self.rerun_manager.rerun(last_message.parent)
                return last_message
        return None
    
    
    async def edit_and_rerun_message(self, message_id: str, new_message_data: str) -> Message:
        workflow_messages = message_dict.get(self.workflow_message.workflow_id, {})
        message = workflow_messages.get(message_id)
        message = await self.rerun_manager.edit_message(message, new_message_data)
        if message.next:
            message = await self.rerun_manager.rerun(message)
            if isinstance(message, ActionMessage):
                while message.next:
                    message = await self.rerun_manager.rerun(message)
            return message
        return None
    
    
    async def change_current_model(self, new_model_name: str):
        self.params['model'] = new_model_name
        self.resource_manager.update_model(new_model_name)
        self.agent_manager.update_phase_agents_models(new_model_name)
        
    async def set_interactive_mode(self, interactive: bool):
        if self.interactive != interactive:
            self.interactive = interactive
            logger.info(f"Workflow interactive mode set to {interactive}")
            
            # Update the interactive mode for the current phase
            if self._current_phase:
                await self._current_phase.set_interactive_mode(interactive)
            
            # Update the interactive mode for all remaining phases
            for phase in self._phase_graph:
                if phase != self._current_phase:
                    phase.phase_config.interactive = interactive
            
            if not interactive:
                # If switching to non-interactive, trigger next iteration
                self.next_iteration_event.set()
    
    async def stop(self): 
        # Set the status to stopped
        self.status = WorkflowStatus.INCOMPLETE

        # Deallocate agents and resources
        self.agent_manager.deallocate_all_agents()
        self.resource_manager.deallocate_all_resources()

        if hasattr(self, "next_iteration_event"):
            self.next_iteration_event.clear()
        

        self._finalize_workflow()

        

    @property
    def name(self):
        return self.__class__.__name__