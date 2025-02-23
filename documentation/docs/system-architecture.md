
## System Architecture

### Workflow System 

#### Overview

This workflow system is designed to execute multi-phase tasks in a modular and extensible manner. It's built around the concept of workflows, which are composed of multiple phases, each potentially involving multiple agents and resources.

#### Core Components

1. **BaseWorkflow**: The abstract base class for all workflows.
2. **BountyWorkflow**: A specialized workflow for bounty-related tasks.
3. **ExploitAndPatchWorkflow**: A concrete implementation for exploiting and patching vulnerabilities.
4. **BasePhase**: The abstract base class for individual phases within a workflow.
5. **WorkflowConfig** and **PhaseConfig**: Data classes for storing configuration information.
6. **WorkflowStatus**: An enumeration of possible workflow statuses.

#### Workflow Execution Flow

1. **Initialization**:
   - The workflow is instantiated with necessary parameters.
   - `_initialize()` method is called to set up task-specific attributes.
   - Logger and agent manager are set up.
   - Phases are created and registered.
   - Resource schedule is computed.

2. **Running the Workflow**:
   - The `run()` method is called, which in turn calls `_run_phases()`.
   - `_run_phases()` iterates through each phase:
     - Sets up the phase.
     - Runs the phase.
     - Processes the phase result.
     - Decides whether to continue or terminate the workflow.

3. **Phase Execution**:
   - Each phase is set up using `_setup_phase()`.
   - The phase's `_run_phase()` method is called, which:
     - Initializes resources.
     - Runs iterations, each potentially involving multiple agents.
     - Deallocates resources upon completion.

4. **Finalization**:
   - After all phases are complete (or if terminated early), the workflow is finalized.
   - Final status is set and logged.

#### Key Features

- **Modularity**: Easy to add new workflows and phases.
- **Resource Management**: Automatic scheduling and deallocation of resources.
- **Agent System**: Flexible agent management across phases.
- **Logging**: Logging at workflow, phase, and iteration levels.

### Phase Architecture

The phase architecture in our workflow system is designed to be **modular, extensible, and easy to customize**. At its core, it revolves around the `BasePhase` class, which defines the structure and execution flow for all phases in the system.

#### **BasePhase Overview**

`BasePhase` serves as an abstract base class that standardizes how phases operate within a workflow. Each phase represents a **logical unit of execution**, where **agents interact, process information, and iterate** toward a goal.

##### **Core Responsibilities:**

1. **Agent Management**  
   - Defines and manages the agents required for the phase.  
   - Initializes agents based on configurations.  
   
2. **Resource Management**  
   - Defines and provisions resources required for execution.  
   - Ensures proper allocation and deallocation of resources.  

3. **Iteration Control**  
   - Manages multiple execution cycles (iterations) within a phase.  
   - Supports interactive and automated execution modes.  

4. **Message Handling**  
   - Manages communication between agents.  
   - Tracks messages across iterations to maintain context.  

##### Key Methods:

- `define_agents()`: Abstract method to define the agents required for the phase.
- `define_resources()`: Abstract method to define the resources needed for the phase.
- `run_one_iteration()`: Abstract method to execute a single iteration of the phase.
- `setup()`: Initializes and registers resources and agents for the phase.
- `run()`: Executes the phase by running its iterations.

#### ExploitPhase

`ExploitPhase` is a concrete implementation of `BasePhase` focused on exploiting vulnerabilities.

##### Key Features:

- Uses `ExecutorAgent` to execute commands in the environment and `ExploitAgent` to validate exploit success and terminate the phase upon conditional completion.
- Defines specific resources like `ModelResource`, `InitFilesResource`, `KaliEnvResource`, etc.
- Implements logic to determine successful exploitation.

#### PatchPhase

`PatchPhase` is another concrete implementation of `BasePhase` designed to patch identified vulnerabilities.

##### Key Features:

- Uses `ExecutorAgent` to execute commands in the environment and `PatchAgent` to validate patch success and terminate the phase upon conditional completion.
- Similar resource setup to `ExploitPhase` but with patch-specific configurations.
- Implements logic to determine successful patching.

#### Phase Execution Flow

1. **Initialization**: The phase is initialized with workflow context and configuration.
2. **Setup**: Resources and agents are set up using `setup()` method.
3. **Iteration**: The `run()` method executes multiple iterations:
   - Each iteration calls `run_one_iteration()` with the current agent.
   - Messages are processed and added to the phase message.
   - Success conditions are checked after each iteration.
4. **Completion**: The phase completes when success conditions are met or max iterations are reached.
5. **Cleanup**: Resources are deallocated using `deallocate_resources()`.

#### Customizing Phases

To create a new phase:

1. Subclass `BasePhase`.
2. Implement `define_agents()`, `define_resources()`, and `run_one_iteration()`.
3. Override other methods as needed for specific functionality.

#### Integration with Workflow

Phases are integrated into the workflow (`self` in example) by first defining the root phase, then using the `>>` operator, which defines the sequence of phases:

```python
exploit_phase = ExploitPhase(workflow=self, **phase_kwargs)
patch_phase = PatchPhase(workflow=self, **phase_kwargs)
self._register_root_phase(exploit_phase)
exploit_phase >> patch_phase
```