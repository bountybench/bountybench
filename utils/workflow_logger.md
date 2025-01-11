# Workflow Logger Documentation

## Overview
The Workflow Logger is designed to track and record the execution of workflows in the cybountyagent system. It provides detailed logging of workflow iterations, agent interactions, and individual actions, making it easier to debug, analyze, and understand the behavior of different workflows.

## Components and Structure

### Core Components

#### 1. WorkflowLog
The root structure that contains:
- Workflow metadata
- List of iterations
- Resources used
- Final status
- Error logs

#### 2. WorkflowMetadata
Stores high-level workflow information:
- Workflow name
- Start/end times
- Task repository directory
- Bounty number
- Model configuration
- Additional metadata

#### 3. WorkflowIteration
Represents a single iteration of the workflow:
- Iteration number
- List of agent interactions
- Status

#### 4. AgentInteraction
Records interaction between agents:
- Agent name
- Input/output messages
- Start/end times
- List of actions
- Metadata

#### 5. Action
Captures individual actions within an interaction:
- Action type
- Input/output data
- Timestamp
- Metadata

### Integration with Workflows

The workflow logger is integrated at the workflow level through a singleton instance (`workflow_logger`). As demonstrated in the patch workflow:

1. **Initialization**: The logger is initialized at the start of the workflow with configuration details.
2. **Iteration Tracking**: Each workflow iteration is tracked using context managers.
3. **Interaction Logging**: Agent interactions within iterations are recorded using nested context managers.
4. **Action Recording**: Individual actions within interactions are logged.

## Tutorial: Using the Workflow Logger

### 1. Basic Setup

```python
from utils.workflow_logger import workflow_logger

# Initialize the logger at the start of your workflow
workflow_logger.initialize(
    workflow_name="your_workflow_name",
    logs_dir="logs",
    task_repo_dir="/path/to/repo",
    bounty_number="123",
    model_config=your_model_config
)
```

### 2. Using Context Managers for Clean Workflow Logic

The workflow logger provides context managers that automatically handle the start and end of iterations and interactions. This approach keeps your workflow code clean and ensures proper logging even if exceptions occur.

```python
def run_workflow():
    # Initialize logger
    workflow_logger.initialize(workflow_name="example_workflow")
    
    # Each iteration is managed by a context
    with workflow_logger.iteration(iteration_number=1) as iteration:
        # Each agent interaction is also managed by a context
        with iteration.interaction("agent_name", input_message) as interaction:
            # Your workflow logic here
            output_message = agent.run([input_message])
            # Set the output message to end the current interaction
            interaction.set_output(output_message)

        # Multiple interactions can be nested within an iteration
        with iteration.interaction("another_agent", another_input) as interaction:
            # More workflow logic...
            interaction.set_output(another_output)
    if success:
        workflow_logger.finalize("success")
```

### 3. Best Practices

- Initialize the logger at the start of your workflow
- Use context managers (`with` statements) for iterations and interactions
- Let the context managers handle the start/end of iterations and interactions
- Always set the output message in successful interactions

## TLDR

The Workflow Logger is a structured logging system that uses context managers to simplify workflow logging:

```python
with workflow_logger.iteration(iteration_number=1) as iteration:
    with iteration.interaction("agent", input_message) as interaction:
        # Your workflow logic here
        interaction.log_action(...)
        interaction.set_output(output_message)
workflow_logger.finalize(status)
```

The logger automatically saves logs to JSON files in the specified logs directory, making it easy to analyze workflow execution later.
