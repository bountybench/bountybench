# Workflow Logger Documentation

## TLDR
The Workflow Logger is a logging system designed to track and record the execution of workflows in the bountyagent system that can be generalized to any workflow. It captures detailed information about workflow iterations, agent interactions, actions, and metadata. The logger creates structured JSON logs that can be used for debugging, analysis, and monitoring of workflow execution.

## Detailed Description

### Components

#### 1. Data Types (`workflow_logger_types.py`)
- **Action**: Records individual actions performed by a specific agent within an iteration with:
  - Action type
  - Input/output data
  - Timestamp
  - Metadata

- **AgentInteraction**: Captures individual agent interaction within an iteration including:
  - Agent name
  - Input/output responses
  - Start/end times
  - List of Actions
  - Metadata

- **WorkflowIteration**: Represents a single iteration within a **workflow** with:
  - Iteration number
  - List of AgentInteractions
  - Status

- **WorkflowMetadata**: Stores workflow-level information:
  - Workflow name
  - Start/end times
  - Task repository directory
  - Bounty number
  - Model configuration
  - Additional metadata

- **WorkflowLog**: The main log structure containing:
  - Workflow metadata
  - List of WorkflowIterations
  - Resources used
  - Final status
  - Error logs

#### 2. Logger Implementation (`workflow_logger.py`)
The `WorkflowLogger` class provides the following key functionalities:

**Initialization**:
```python
def __init__(self, workflow_name: str, logs_dir: str = "logs", 
             task_repo_dir: Optional[str] = None, 
             bounty_number: Optional[str] = None,
             model_config: Optional[Dict[str, Any]] = None)
```
- Creates a new workflow log with metadata
- Generates a unique log filename based on workflow parameters
- Creates the logs directory if it doesn't exist

**Core Logging Methods**:
```python
def start_iteration(self, iteration_number: int) -> None:
    """Start a new workflow iteration"""

def start_interaction(self, agent_name: str, input_response: Response) -> None:
    """Start a new interaction within the current iteration"""

def log_action(self, action_name: str, input_data: Any, 
               output_data: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Log an action within the current interaction"""

def end_iteration(self, status: str) -> None:
    """End the current iteration and add it to the workflow log"""

def end_interaction(self, output_response: Response) -> None:
    """End the current interaction and add it to the current iteration"""
```

**Resource and Error Tracking**:
```python
def add_resource(self, resource_name: str) -> None:
    """Log a resource being used in the workflow"""

def log_error(self, error_msg: str, error_data: Optional[Dict[str, Any]] = None) -> None:
    """Log an error that occurred during the workflow"""

def add_metadata(self, key: str, value: Any) -> None:
    """Add additional metadata to the workflow"""
```

**Finalization and Saving**:
```python
def finalize(self, final_status: str = "completed") -> None:
    """Finalize the workflow log"""

def save(self) -> None:
    """Save the workflow log to a JSON file"""
```

## Tutorial: Using the Workflow Logger

### 1. Creating a New Workflow with Logging

```python
from utils.workflow_logger import WorkflowLogger

def my_workflow():
    # Initialize the logger
    logger = WorkflowLogger(
        workflow_name="my_workflow",
        logs_dir="logs",
        task_repo_dir="/path/to/repo",
        bounty_number="123"
    )

    # Start an iteration
    logger.start_iteration(iteration_number=1)

    try:
        # Log agent interaction
        logger.start_interaction("my_agent", input_response)
        
        # Log specific actions
        logger.log_action(
            action_name="process_data",
            input_data={"data": "input"},
            output_data={"result": "output"},
            metadata={"duration": "1s"}
        )

        # End interaction
        logger.end_interaction(output_response)

        # End iteration successfully
        logger.end_iteration("completed")

    except Exception as e:
        # Log any errors
        logger.log_error(str(e))
        logger.end_iteration("failed")

    # Finalize the workflow
    logger.finalize()
```

### 2. Adding Logging to an Existing Agent

```python
class MyAgent:
    def __init__(self, workflow_logger: WorkflowLogger):
        self.logger = workflow_logger

    def process(self, input_data):
        """ start and end interaction in the workflow-level """
        output_data = llm(input_data)
        # Log specific actions
        self.logger.log_action(
            "llm",
            input_data=input_data,
            output_data=output_data
        )
```

### Example: Patch Workflow Implementation

The patch workflow demonstrates how to use the workflow logger in a complex scenario involving multiple agents and resources. Here's a detailed breakdown:

1. **Initialize the Logger**:
```python
workflow_logger = WorkflowLogger(
    workflow_name="patch",
    logs_dir=str(logs_dir),
    task_repo_dir=str(args.task_repo_dir),
    bounty_number=bounty_number,
    model_config=executor_agent_config.__dict__
)
```

2. **Track Resources**:
```python
# Log initialization of resources
workflow_logger.add_resource("InitFilesResource")
InitFilesResource(task_repo_dir=task_repo_dir, files_dir_name=files_dir)

workflow_logger.add_resource("KaliEnv")
KaliEnvResource("KaliEnv", task_repo_dir=task_repo_dir, bounty_number=bounty_number)
```

3. **Add Workflow Context**:
```python
# Add important workflow metadata
workflow_logger.add_metadata("vulnerable_files", vulnerable_files)
workflow_logger.add_metadata("exploit_description", exploit_description)
workflow_logger.add_metadata("repo_metadata", repo_metadata)
```

4. **Log Iterations and Agent Interactions**:
```python
for iteration in range(max_iterations):
    # Start a new iteration
    workflow_logger.start_iteration(iteration + 1)

    # Log executor agent interaction
    workflow_logger.start_interaction(
        agent_name="executor_agent",
        input_response=prev_response
    )
    response = executor_agent.run(inputs)
    workflow_logger.end_interaction(output_response=response)

    # Log patch agent interaction
    workflow_logger.start_interaction(
        agent_name="patch_agent",
        input_response=response
    )
    patch_response = patch_agent.run([response])
    workflow_logger.end_interaction(output_response=patch_response)

    # Handle iteration status
    if issubclass(patch_response.__class__, AnswerResponseInterface):
        workflow_logger.end_iteration("success")
        workflow_logger.finalize("completed_success")
        break
    
    workflow_logger.end_iteration("in_progress")
```

5. **Handle Completion and Errors**:
```python
# Handle successful completion
if success:
    workflow_logger.finalize("completed_success")
else:
    # Log error if max iterations reached
    workflow_logger.finalize("completed_max_iterations")
```

The resulting log file will contain:
- Complete workflow metadata
- Detailed record of each iteration
- All agent interactions and their responses
- Resources used throughout the workflow
- Final workflow status and any errors

## Best Practices

1. **Always finalize workflows**: Call `finalize()` at the end of your workflow to ensure proper completion.
2. **Error handling**: Use `log_error()` to track exceptions and issues.
3. **Metadata**: Use `add_metadata()` to include additional context when needed.
4. **Resource tracking**: Use `add_resource()` to track external resources being used.
5. **Proper nesting**: Always maintain the proper nesting of iterations and interactions:
   - Workflow → Iteration → Interaction → Action
