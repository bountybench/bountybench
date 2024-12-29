# cybountyagent

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [System Architecture](#system-architecture)
  - [Workflow and Resource Manager](#workflow-and-resource-manager)
  - [Phases](#phases)
  - [Agents](#agents)
  - [Resources](#resources)
  - [Validation Process](#validation-process)
- [Development](#development)
  - [Agent Development](#agent-development)
  - [Phase Development](#phase-development)
  - [Workflow Development](#workflow-development)
- [Contributing](#contributing)
- [License](#license)

## Installation
## Environment Setup

### 1. Ensure Python 3.11 is Installed
Verify that Python 3.11 is available on your system:
```
python3.11 --version
```
### 2. Create a Virtual Environment
Set up a virtual environment to isolate dependencies:
```
python3.11 -m venv venv
```

### 3. Activate and Set Up the Environment
Activate the virtual environment, install required dependencies, and initialize submodules:
```
source venv/bin/activate
pip install -r requirements.txt
git submodule update --init
```

### 4. Configure the .env File
Create and populate a .env file with the following keys:
```
HELM_API_KEY={HELM_API_KEY}
OPENAI_API_KEY={OPENAI_API_KEY}
AZURE_OPENAI_API_KEY={AZURE_OPENAI_API_KEY}
AZURE_OPENAI_ENDPOINT={AZURE_OPENAI_ENDPOINT}
ANTHROPIC_API_KEY={ANTHROPIC_API_KEY}
GOOGLE_API_KEY={GOOGLE_API_KEY}
TOGETHER_API_KEY={TOGETHER_API_KEY}
```
Replace {KEY_NAME} with your actual API key values.

## Usage

### Running the Workflow
To run the exploit-and-patch workflow interactively, use the following command:
```
python3 -m workflows.exploit_and_patch_workflow_v2 \
    --task_repo_dir bountybench/astropy \
    --bounty_number 0 \
    --interactive
```

## System Architecture

### Workflow and Resource Manager

The `BaseWorkflow` class serves as the core orchestrator of the system. It manages the execution of phases, coordinates resource allocation, and handles the overall flow of the workflow.

Key features:
- Automatic resource initialization and allocation
- Phase sequencing and execution
- Agent registration and configuration
- Logging and metadata management

The `ResourceManager` works in tandem with the workflow to handle resource lifecycle:
- Resource registration and initialization
- Allocation of resources to phases and agents
- Automatic cleanup and deallocation of resources

Automatic processes:
- Resource scheduling across phases
- Initialization of resources before phase execution
- Deallocation of resources after phase completion

### Phases

Phases represent distinct stages in a workflow. The `BasePhase` class provides a foundation for creating custom phases.

Key features:
- Automatic agent rotation within a phase
- Resource allocation for the phase duration
- Iteration management and completion criteria

Automatic processes:
- Agent selection for each iteration
- Resource binding for agents within the phase
- Execution of iterations until completion criteria are met

### Agents

Agents are the workhorses of the system, performing specific tasks within phases. The `BaseAgent` class offers a flexible framework for agent development.

Key features:
- Declarative resource requirements
- Automatic resource binding
- Standardized execution interface

Automatic processes:
- Resource validation and binding before execution
- Error handling for missing required resources
- Attribute-based access to bound resources

### Resources

Resources represent reusable components or services that agents can utilize. The `BaseResource` class provides a template for creating custom resources.

Key features:
- Lifecycle management (initialization, allocation, deallocation)
- Configuration via `BaseResourceConfig`
- Integration with the ResourceManager for centralized control

Automatic processes:
- Resource initialization based on configuration
- Allocation to agents when required
- Cleanup and deallocation when no longer needed

### Validation Process
The `BaseWorkflow` class includes a built-in validation process to ensure that all required components are properly registered and configured. This validation occurs automatically during workflow initialization and includes the following checks:

#### Required Phases Validation:

Ensures that all phases specified in the `REQUIRED_PHASES` class attribute are properly registered.
Raises a `ValueError` if any required phase is missing.
#### Required Agents Validation:
Checks that all agents specified in each phase's `REQUIRED_AGENTS` attribute are registered.
Raises a `ValueError` if any required agent is missing for a particular phase.
#### Required Resources Validation:
Verifies that all resources specified in each agent's `REQUIRED_RESOURCES` attribute are registered with the ResourceManager.
Raises a `ValueError` if any required resource is missing.

To leverage this validation process:
Ensure that your workflow subclass correctly defines the `REQUIRED_PHASES` attribute, each phase class properly defines`REQUIRED_AGENTS`, each agent class properly defines `REQUIRED_RESOURCES`.
Use the `register_resource`, `register_agent`, and `register_phase` methods in your workflow's configuration methods to register all necessary components.
The validation process will automatically run during workflow initialization, helping to catch configuration errors early in the development process.

## Development

This section provides guidelines for developing new components within the project.

### Agent Development

When developing a new agent, subclass `BaseAgent` and implement the following:

1. Define `REQUIRED_RESOURCES`, `OPTIONAL_RESOURCES`, and `ACCESSIBLE_RESOURCES` class attributes:
   ```python
   REQUIRED_RESOURCES = [ResourceClass1, (ResourceClass2, "custom_name")]
   OPTIONAL_RESOURCES = [(ResourceClass3, "optional_resource")]
   ACCESSIBLE_RESOURCES = [ResourceClass1, (ResourceClass2, "custom_name"), (ResourceClass3, "optional_resource")]
   ```
2. Implement the run method:
    ```python
    def run(self, responses: List[Response]) -> Response:
        # Agent logic here
        pass
    ```
3. Optionally, implement additional helper methods as needed.

4. Ensure proper resource handling:
    - Required resources will automatically raise a KeyError if missing.
    - Optional resources will be None if not available.
    - Only resources listed in ACCESSIBLE_RESOURCES will be bound as attributes.

### Phase Development
When creating a new phase, subclass `BasePhase` and implement the following:

1. Define the REQUIRED_AGENTS class attribute:
    ```python
    REQUIRED_AGENTS = [AgentClass1, AgentClass2]
    ```

2. Implement the run_one_iteration method:
    ```python
    def run_one_iteration(
        self,
        agent_instance: Any,
        previous_output: Optional[Response],
        iteration_num: int
    ) -> Tuple[Response, bool]:
        # Phase logic here
        pass
    ```

### Workflow Development
To create a new workflow, subclass `BaseWorkflow` and implement the following:

1. Define the REQUIRED_PHASES class attribute:
    ```python
    REQUIRED_PHASES = [PhaseClass1, PhaseClass2]
    ```
2. Implement the `get_initial_prompt` method to define workflow task, e.g..
    ```python
    def get_initial_prompt(self) -> str:
        exploit_report = read_exploit_report(self.task_repo_dir, self.bounty_number)
        prompt = PATCH_PROMPT.format(
            task_description=exploit_report,
            stop_token=STOP_TOKEN,
            target_host=self.repo_metadata["target_host"],
        )
        return prompt
    ```
3. Implement the `define_phase_configs` method to define workflow task, e.g..
    ```python
    def define_phase_configs(self) -> None:
        """Define and register all phases required for the workflow."""
        pass
    ```

4. Implement the `define_agent_configs` method to define workflow task, e.g..
    ```python
    def define_agent_configs(self) -> None:
        """Define and register all agents required for the workflow."""
        pass
    ```
4. Implement the `define_resource_configs` method to register necessary resources - `BaseWorkflow` automatically registers `InitFilesResource` and `SetupResource`(s) (the basic resources for a bounty task) as necessary:
    ```python
    def define_resource_configs(self) -> None:
        super().define_resource_configs()
        # Register additional resources here
    ```
5. Use the `register_resource`, `register_agent`, and `register_phase` methods to add resources, agents, and phases to the workflow.

6. Implement the `setup_directories` methods if there is any additional file setup needed.
    ```python
    def setup_directories(self) -> None:
        """Setup necessary directories for the workflow."""
        pass
    ```
