# bountyagent

## Table of Contents

- [bountyagent](#bountyagent)
  - [Table of Contents](#table-of-contents)
  - [Installation](#installation)
    - [Environment Setup](#environment-setup)
    - [1. Ensure Python 3.11 is Installed](#1-ensure-python-311-is-installed)
    - [2. Create a Virtual Environment](#2-create-a-virtual-environment)
    - [3. Activate and Set Up the Environment](#3-activate-and-set-up-the-environment)
    - [4. Configure the .env File](#4-configure-the-env-file)
    - [5. Setup Docker Desktop App](#5-setup-docker-desktop-app)
      - [Docker Setup](#docker-setup)
        - [Ensure your Docker Desktop has proper sharing permissions](#ensure-your-docker-desktop-has-proper-sharing-permissions)
  - [Usage](#usage)
    - [Running the Workflow](#running-the-workflow)
    - [Running the Application](#running-the-application)
      - [Concurrent run](#concurrent-run)
      - [Backend Setup](#backend-setup)
      - [Frontend Setup](#frontend-setup)
    - [Accessing the Application](#accessing-the-application)
    - [Dockerize run](#dockerize-run)
    - [Sample Run](#sample-run)
    - [Troubleshooting](#troubleshooting)
      - [Docker Mount Issue](#docker-mount-issue)
  - [System Architecture](#system-architecture)
    - [Workflow System](#workflow-system)
      - [Overview](#overview)
      - [Core Components](#core-components)
      - [Workflow Execution Flow](#workflow-execution-flow)
      - [Key Features](#key-features)
    - [Phase Architecture](#phase-architecture)
      - [**BasePhase Overview**](#basephase-overview)
        - [**Core Responsibilities:**](#core-responsibilities)
        - [Key Methods](#key-methods)
      - [ExploitPhase](#exploitphase)
        - [Key Features](#key-features-1)
      - [PatchPhase](#patchphase)
        - [Key Features](#key-features-2)
      - [Phase Execution Flow](#phase-execution-flow)
      - [Customizing Phases](#customizing-phases)
      - [Integration with Workflow](#integration-with-workflow)
  - [Development](#development)
  - [Code Quality](#code-quality)
    - [Tools and Standards](#tools-and-standards)
    - [Local Development Setup](#local-development-setup)
  - [Testing](#testing)
    - [Running Tests with Coverage](#running-tests-with-coverage)
      - [**Prerequisites**](#prerequisites)
      - [**Running Tests with Coverage**](#running-tests-with-coverage-1)
      - [**Generating Coverage Reports**](#generating-coverage-reports)
        - [1. **View Coverage Summary in the Terminal**](#1-view-coverage-summary-in-the-terminal)
        - [2. **Generate an HTML Coverage Report**](#2-generate-an-html-coverage-report)
      - [**Enforcing Minimum Coverage**](#enforcing-minimum-coverage)
  - [Documentation](#documentation)

## Installation

### Environment Setup

You can quickly set up the dev environment by running the following command:

```bash
./setup.sh
source venv/bin/activate
```

To initialize all submodules, run:

```bash
./setup.sh --all
source venv/bin/activate
```

### 1. Ensure Python 3.11 is Installed

Verify that Python 3.11 is available on your system:

```bash
python3.11 --version
```

### 2. Create a Virtual Environment

Set up a virtual environment to isolate dependencies:

```bash
python3.11 -m venv venv
```

### 3. Activate and Set Up the Environment

Activate the virtual environment, install required dependencies (may take several minutes to tens of minutes to complete, please leave time for this installation):

```bash
source venv/bin/activate
pip install -r requirements.txt
```

Initialize submodules (may take a few minutes to complete):

```bash
git submodule update --init
cd bountybench
git submodule update --init
```

Additionally, please install `tree`:

macOS (using Homebrew):

```bash
brew install tree
```

or Debian/Ubuntu (using APT):

```bash
sudo apt-get install tree
```

### 4. Configure the .env File

Create and populate an .env file in `bountyagent/` with the following keys:

```bash
ANTHROPIC_API_KEY={ANTHROPIC_API_KEY}
AZURE_OPENAI_API_KEY={AZURE_OPENAI_API_KEY}
AZURE_OPENAI_ENDPOINT={AZURE_OPENAI_ENDPOINT}
GOOGLE_API_KEY={GOOGLE_API_KEY}
HACKERONE_API_IDENTIFIER={HACKERONE_API_IDENTIFIER}
HACKERONE_API_KEY={HACKERONE_API_KEY}
HELM_API_KEY={HELM_API_KEY}
OPENAI_API_KEY={OPENAI_API_KEY}
TOGETHER_API_KEY={TOGETHER_API_KEY}
XAI_API_KEY={XAI_API_KEY}
```

Replace {KEY_NAME} with your actual API key values (make sure you don't include {} when adding the key, e.g. KEY=XYZ...). You only need to fill in whichever keys you will use.

#### HackerOne API Setup

To use the HackerOne API functionality:

1. You'll need a HackerOne account with API access
2. Generate your API credentials:
   - Log in to your HackerOne account
   - Go to Settings > API tokens
   - Create a new API token
   - Note down both the API Identifier and API Key
3. Add these credentials to your .env file:
   ```bash
   HACKERONE_API_KEY=your_api_key_here
   HACKERONE_API_IDENTIFIER=your_api_identifier_here
   ```

The HackerOne API is used to fetch detailed report metadata. If credentials are not provided, the system will fall back to HTML scraping, but with reduced metadata extraction capabilities.

### 5. Setup Docker Desktop App

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

### Running Workflows

Make sure your Docker Desktop app is running.

Running workflows from CLI should use `runner.py` module. Each runnable workflow defines required and optional arguments. Important parameter interactions:

- `--model` and `--use_mock_model` are mutually exclusive. You cannot specify both simultaneously.
- If `--use_mock_model` is True, then `--use_helm` parameter is ignored
- The `--use_helm` parameter determines whether to use Helm as the model provider

If using openai o1/o3, it's [recommended to have at least 25k](https://platform.openai.com/docs/guides/reasoning?api-mode=chat#allocating-space-for-reasoning) `--max_output_tokens`

```bash
python -m workflows.runner --workflow-type WORKFLOW_TYPE [OPTIONS]
```

Available workflow types:
- `exploit_patch_workflow`:
- `patch_workflow`:
- `detect_patch_workflow`:

Required flags vary by workflow type.

Examples:

1. **Exploit and Patch Workflow**:
```bash
python -m workflows.runner --workflow-type exploit_patch_workflow \
    --task_dir bountybench/lunary \
    --bounty_number 0 \
    --model anthropic/claude-3-5-sonnet-20241022 \
    --phase_iterations 3
```

2. **Detect Patch Workflow**:
```bash
python -m workflows.runner --workflow-type detect_patch_workflow \
    --task_dir bountybench/django \
    --bounty_number 0 \
    --model anthropic/claude-3-sonnet-20240229 \
    --phase_iterations 2 \
    --use_helm
```

3. **Patch Only Workflow**:
```bash
python -m workflows.runner --workflow-type patch_workflow \
    --task_dir bountybench/mlflow \
    --bounty_number 1 \
    --use_mock_model \
    --phase_iterations 5
```

Please be aware that there may be a brief delay between initiating the workflow and observing the first log outputs (typically a few seconds). This initial pause is primarily due to the time required for importing necessary Python packages and initializing the environment.

### Running the Application

#### Concurrent run

1. In the root directory run:

```bash
npm install
npm start
```

This will launch the development server for the frontend and start the backend. You may need to refresh as the backend takes a second to run.

Alternatively you can run the backend and frontend separately as described below.

#### Backend Setup

1. Open a terminal and navigate to the `bountyagent` directory.

2. Start the backend server:

```bash
python -m backend.main
```

Note: The backend will take about a minute to initialize. You can view incremental, verbose run updates in this terminal window.

#### Frontend Setup

1. Open a new terminal and navigate to the `bountyagent/frontend` directory.

2. If this is your first time running the frontend or if you've updated the project, install the necessary packages:

   ```bash
   npm install
   ```

3. After the installation is complete, start the frontend application:

   ```bash
   npm start
   ```

This will launch the development server for the frontend.

For a list of API endpoints currently supported, open one of these URLs in your browser:

- Swagger UI: `http://localhost:7999/docs`
- ReDoc: `http://localhost:7999/redoc`

### Accessing the Application

Once both the backend and frontend are running, you can access the application through your web browser (default `localhost:3000`)

### Dockerize run

1. Open the Docker Desktop app and ensure it's running.

2. Create a Docker volume for DinD data

   ```bash
   docker volume create dind-data
   ```

3. Navigate to the `bountyagent` directory and run:

   ```bash
   docker compose up --build -d
   ```

Once built, the frontend will be running at http://localhost:3000/, and everything should be the same as in non-dockerized versions.

To stop the containers, run
```
docker compose down
```

To start the containers without rebuilding, run:
```
docker compose up -d
```
If docker still attempts to rebuild, try cancelling the build using `control+c` and adding the `--no-build` flag (assuming no images are missing).

### Using Git Inside Containers
Depending on the hardware setup, building the container could take anywhere from 5 minutes to much longer. Because dependencies changes are less frequent than codebase changes, a possible solution is to building the container once, and then use git in the container to fetch the latest changes from `bountyagent/` (`app/`) and `bountybench/` (`app/bountybench`) repos. Inside the container, you could also `git checkout` different branches for testing. 

SSH keys are needed for `git pull` and `git fetch` to work. **Before running `docker compose up --build -d`, please the follow these steps to set up the git credentials correctly:**

1. Please make sure you cloned the repository with ssh, i.e. `git clone git@github.com:cybench/bountyagent.git`
2. To create a new pair of ssh keys specific for the container, run

```
chmod +x tools/ssh_key_gen.sh && \
tools/ssh_key_gen.sh
```

and copy the public key (i.e. the output) to [GitHub/settings/keys](https://github.com/settings/keys). 

3. You could also change these two lines in `docker-compose.yml` to use any paths or keys of your choice:
```
  - ${HOME}/.ssh/id_rsa_backend-service:/root/.ssh/id_rsa:ro
  - ${HOME}/.ssh/id_rsa_backend-service.pub:/root/.ssh/id_rsa.pub:ro
```

**If you do not wish to use git, you can safely delete these two lines.**

We have also provide a bash script `dockerize_run.sh` that serves as an easy interface to run the application using docker.

### Sample Run

![Screen recording of a run](documentation/docs/media/sample_run.gif)

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

     ```bash
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

##### Key Methods

- `define_agents()`: Abstract method to define the agents required for the phase.
- `define_resources()`: Abstract method to define the resources needed for the phase.
- `run_one_iteration()`: Abstract method to execute a single iteration of the phase.
- `setup()`: Initializes and registers resources and agents for the phase.
- `run()`: Executes the phase by running its iterations.

#### ExploitPhase

`ExploitPhase` is a concrete implementation of `BasePhase` focused on exploiting vulnerabilities.

##### Key Features

- Uses `ExecutorAgent` to execute commands in the environment and `ExploitAgent` to validate exploit success and terminate the phase upon conditional completion.
- Defines specific resources like `ModelResource`, `InitFilesResource`, `KaliEnvResource`, etc.
- Implements logic to determine successful exploitation.

#### PatchPhase

`PatchPhase` is another concrete implementation of `BasePhase` designed to patch identified vulnerabilities.

##### Key Features

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

   You can format your code manually by running

   ```bash
   pre-commit run --all-files
   ```

   If you have issues with formatting, you can run the individual tools separately:

   ```bash
   # Format code with Black
   black .
   
   # Sort imports with isort
   isort .
   
   # Run Flake8 linting
   flake8 .
   ```

## Testing

This project uses `pytest`.

### Running Tests with Coverage

This project uses `coverage.py` to measure test coverage for the codebase.

#### **Prerequisites**

Ensure you have `coverage` and `pytest` installed. If not, manually install them using or run `pip install -r requirements.txt` in your virtual environment:

```sh
pip install coverage pytest
```

#### **Running Tests with Coverage**

To run tests located in the `tests/` folder while tracking coverage, run the following in the `bountyagent/` folder:

```sh
coverage run --rcfile=.coveragerc -m pytest tests/
```

#### **Generating Coverage Reports**

After running the tests, generate coverage reports using the following commands:

##### 1. **View Coverage Summary in the Terminal**

```bash
coverage report
```

##### 2. **Generate an HTML Coverage Report**

For a visual representation, run:

```sh
coverage html
```

Then, open `htmlcov/index.html` in your browser to view the detailed coverage report by doing the following:

```sh
open htmlcov/index.html
```

#### **Enforcing Minimum Coverage**

To enforce a minimum test coverage percentage (e.g., 80%), use:

```sh
coverage report --fail-under=80
```

This command will cause the process to fail if the coverage is below 80%.

---

For further details on `coverage.py`, refer to the official documentation: [Coverage.py](https://coverage.readthedocs.io/)

## Documentation

To view the full documentation:

1. Ensure you have MkDocs installed: either rerun `pip install -r requirements.txt` or individually `pip install mkdocs`
2. Navigate to `bountyagent/documentation`
3. Run `mkdocs serve`
4. Open your browser and go to `http://127.0.0.1:8000/`

For offline viewing:

1. Run `mkdocs build`
2. Open `site/index.html` in your web browser
