# bountyagent

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
   - [Running the Workflow](#running-the-workflow)
   - [Running the Application](#running-the-application)
- [System Architecture](#system-architecture)
  - [Workflow System](#workflow-system)
- [Development](#development)

## Installation
## Environment Setup

You can quickly set up the environment by running the following command:
```
./setup.sh
source venv/bin/activate
```

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
Activate the virtual environment, install required dependencies (may take several minutes to tens of minutes to complete, please leave time for this installation):
```
source venv/bin/activate
pip install -r requirements.txt
```
Initialize submodules (may take a few minutes to complete):
```
git submodule update --init
cd bountybench
git submodule update --init
```

### 4. Configure the .env File
Create and populate an .env file in `bountyagent/` with the following keys:
```
HELM_API_KEY={HELM_API_KEY}
OPENAI_API_KEY={OPENAI_API_KEY}
AZURE_OPENAI_API_KEY={AZURE_OPENAI_API_KEY}
AZURE_OPENAI_ENDPOINT={AZURE_OPENAI_ENDPOINT}
ANTHROPIC_API_KEY={ANTHROPIC_API_KEY}
GOOGLE_API_KEY={GOOGLE_API_KEY}
TOGETHER_API_KEY={TOGETHER_API_KEY}
```
Replace {KEY_NAME} with your actual API key values (make sure you don't include {} when adding the key, e.g. KEY=XYZ...). You only need to fill in whichever keys you will use. 

### 5. Setup Docker Desktop App. 
Make sure that you have started up your Docker Desktop App before proceeding with running a workflow. 

#### Docker Setup
To get started with Docker, follow these installation instructions based on your operating system:

- **[Docker Desktop Installation for Mac](https://docs.docker.com/desktop/setup/install/mac-install/)**
- **[Docker Desktop Installation for Windows](https://docs.docker.com/desktop/setup/install/windows-install/)**

 **Verify Installation**  
   - Open a terminal or command prompt and run the following command:  
     ```bash
     docker --version
     ```  
   - Ensure Docker is installed and the version is displayed.

##### Ensure your Docker Desktop has proper sharing permissions
You want to ensure that Docker Desktop has mounting permissions for your current working directory. Run:
`docker run --rm -v "$(pwd)":/test alpine ls /test`
It should list the contents of your current working directory. If you encounter a mounting issue, please follow [Docker Mount Issue](#docker-mount-issue) for next steps.

## Usage

### Running the Workflow
Make sure your Docker Desktop app is running.

To run the exploit-and-patch workflow from the command line, navigate to the ``` bountyagent ``` directory and use the following command:
```
python -m workflows.exploit_and_patch_workflow \
    --task_dir bountybench/setuptools \
    --bounty_number 0 \
    --model anthropic/claude-3-5-sonnet-20240620 \
    --phase_iterations 14
```
Please be aware that there may be a brief delay between initiating the workflow and observing the first log outputs (typically a few seconds). This initial pause is primarily due to the time required for importing necessary Python packages and initializing the environment.

### Running the Application

## Concurrent run
1. In the root directory run:

```
npm install
npm start
```

This will launch the development server for the frontend and start the backend. You may need to refresh as the backend takes a second to run.

Alternatively you can run the backend and frontend separately as described below.


## Backend Setup

1. Open a terminal and navigate to the `bountyagent` directory.

2. Start the backend server:
```
python server.py
```
Note: The backend will take about a minute to initialize. You can view incremental, verbose run updates in this terminal window.

## Frontend Setup

1. Open a new terminal and navigate to the `bountyagent/frontend` directory.

2. If this is your first time running the frontend or if you've updated the project, install the necessary packages:
```
npm install
```
3. After the installation is complete, start the frontend application:
```
npm start
```

This will launch the development server for the frontend.

## Accessing the Application

Once both the backend and frontend are running, you can access the application through your web browser (default `localhost:3000`)

### Sample Run
![Screen recording of a run](media/sample_run.gif)

### Troubleshooting

#### Docker Mount Issue

**Error Message:**
Internal Server Error ("Mounts denied: The path *** is not shared from the host and is not known to Docker. You can configure shared paths from Docker -> Preferences... -> Resources -> File Sharing.")

**Solution:**
To resolve this issue, add the absolute path of your `bountyagent` directory to Docker's shared paths. Follow these steps:

1. **Determine the Absolute Path:**
   - Open your terminal.
   - Navigate to the root directory of your project.
   - Retrieve the absolute path using the `pwd` command.
   - **Example Output:**
     ```
     /Users/yourusername/projects/bountyagent
     ```

2. **Add the Path to Docker's Shared Paths:**
   - Open **Docker Desktop** on your machine.
   - Click on the **Settings** (gear) icon.
   - Navigate to **Resources** > **File Sharing**.
   - Paste the absolute path you obtained earlier (e.g., `/Users/yourusername/projects/bountyagent`).
   - Click the **`+`** button to add the new shared path.
   - Also add `/tmp` using the **`+`** button.
   - Click **Apply & Restart** to save the changes.

3. **Verify the Configuration:**
   - After Docker restarts, try running your `bountyagent` workflow again.
   - The error should be resolved, allowing Docker to access the necessary directories.

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

## Development

1. To create a new workflow:
   - Subclass `BaseWorkflow` or `BountyWorkflow`.
   - Implement `_create_phases()`, `_get_initial_prompt()`, and any optional methods.

2. To create a new phase:
   - Subclass `BasePhase`.
   - Implement `define_agents()`, `define_resources()`, and `run_one_iteration()`.

## Code Quality

### Tools and Standards

- **Black**: Code formatter that ensures consistent Python code style
- **Flake8**: Linter that checks for Python code style and errors
- **isort**: Sorts and organizes Python imports

### Local Development Setup

1. **Pre-commit Hooks**

   ```bash
   # Install pre-commit hooks (automatically runs on every commit)
   pre-commit install
   ```

2. **Manual Code Formatting**

   ```bash
   # Format code with Black
   black .
   
   # Sort imports with isort
   isort .
   
   # Run Flake8 linting
   flake8 .
   ```
