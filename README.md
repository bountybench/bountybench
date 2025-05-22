# BountyBench

## Table of Contents

- [bountybench](#bountybench)
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
    - [Running Workflows](#running-workflows)
    - [Running the Application](#running-the-application)
    - [Accessing the Application](#accessing-the-application)
    - [Dockerize run](#dockerize-run)
    - [Sample Run](#sample-run)
    - [Troubleshooting](#troubleshooting)
      - [Docker Mount Issue](#docker-mount-issue)

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

### Alternative Manual Setup

If you prefer to set up the environment manually, follow these steps:

#### 1. Ensure Python 3.11 is Installed

Verify that Python 3.11 is available on your system:

```bash
python3.11 --version
```

#### 2. Create a Virtual Environment

Set up a virtual environment to isolate dependencies:

```bash
python3.11 -m venv venv
```

#### 3. Activate and Set Up the Environment

Activate the virtual environment, install required dependencies (may take several minutes to tens of minutes to complete, please leave time for this installation):

```bash
source venv/bin/activate
pip install -r requirements.txt
```

Initialize submodules (may take a few minutes to complete):

```bash
git submodule update --init
git submodule update --remote
cd bountytasks
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

#### 4. Configure the .env File

Create and populate an .env file in `bountybench/` with the following keys:

```bash
ANTHROPIC_API_KEY={ANTHROPIC_API_KEY}
AZURE_OPENAI_API_KEY={AZURE_OPENAI_API_KEY}
AZURE_OPENAI_ENDPOINT={AZURE_OPENAI_ENDPOINT}
GOOGLE_API_KEY={GOOGLE_API_KEY}
HELM_API_KEY={HELM_API_KEY}
OPENAI_API_KEY={OPENAI_API_KEY}
TOGETHER_API_KEY={TOGETHER_API_KEY}
XAI_API_KEY={XAI_API_KEY}
```

Replace {KEY_NAME} with your actual API key values (make sure you don't include {} when adding the key, e.g. KEY=sk-proj...). You only need to fill in whichever keys you will use.

#### 5. Setup Docker Desktop App

Make sure that you have started up your Docker Desktop App before proceeding with running a workflow.

##### Docker Setup

To get started with Docker, follow these installation instructions based on your operating system:

- **[Docker Desktop Installation for Mac](https://docs.docker.com/desktop/setup/install/mac-install/)**
- **[Docker Desktop Installation for Windows](https://docs.docker.com/desktop/setup/install/windows-install/)**

 **Verify Installation**  

- Open a terminal or command prompt and run the following command:  

     ```bash
     docker --version
     ```  

- Ensure Docker is installed and the version is displayed.

###### Ensure your Docker Desktop has proper sharing permissions

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

```bash
python -m workflows.runner --workflow-type WORKFLOW_TYPE [OPTIONS]
```

Available workflow types:
- `detect_workflow`:
- `exploit_workflow`:
- `patch_workflow`:

Required flags vary by workflow type.

Examples:

1. **Detect Workflow**:
```bash
python -m workflows.runner --workflow-type detect_workflow \
    --task_dir bountytasks/lunary \
    --bounty_number 0 \
    --model anthropic/claude-3-5-sonnet-20241022 \
    --phase_iterations 3
```

2. **Exploit Workflow**:
```bash
python -m workflows.runner --workflow-type exploit_workflow \
    --task_dir bountytasks/django \
    --bounty_number 0 \
    --model anthropic/claude-3-sonnet-20240229 \
    --phase_iterations 2 \
    --use_helm
```

3. **Patch Workflow**:
```bash
python -m workflows.runner --workflow-type patch_workflow \
    --task_dir bountytasks/mlflow \
    --bounty_number 1 \
    --use_mock_model \
    --phase_iterations 5
```

Please be aware that there may be a brief delay between initiating the workflow and observing the first log outputs (typically a few seconds). This initial pause is primarily due to the time required for importing necessary Python packages and initializing the environment.

### Running the Application

1. In the root directory run:

```bash
npm install
npm start
```

This will launch the development server for the frontend and start the backend. You may need to refresh as the backend takes a second to run.

### Accessing the Application

Once both the backend and frontend are running, you can access the application through your web browser (default `localhost:3000`)

### Dockerize run

1. Open the Docker Desktop app and ensure it's running.

2. Create a Docker volume for DinD data

   ```bash
   docker volume create dind-data
   ```

3. Navigate to the `bountybench` directory and run:

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

To exec into the container, run:
```
docker exec -it backend-service bash
```

Then follow [Running Workflows](#running-workflows).


### Troubleshooting

#### Docker Mount Issue

**Error Message:**
Internal Server Error ("Mounts denied: The path *** is not shared from the host and is not known to Docker. You can configure shared paths from Docker -> Preferences... -> Resources -> File Sharing.")

**Solution:**
To resolve this issue, add the absolute path of your `bountybench` directory to Docker's shared paths. Follow these steps:

1. **Determine the Absolute Path:**
   - Open your terminal.
   - Navigate to the root directory of your project.
   - Retrieve the absolute path using the `pwd` command.
   - **Example Output:**

     ```bash
     /Users/yourusername/projects/bountybench
     ```

2. **Add the Path to Docker's Shared Paths:**
   - Open **Docker Desktop** on your machine.
   - Click on the **Settings** (gear) icon.
   - Navigate to **Resources** > **File Sharing**.
   - Paste the absolute path you obtained earlier (e.g., `/Users/yourusername/projects/bountybench`).
   - Click the **`+`** button to add the new shared path.
   - Also add `/tmp` using the **`+`** button.
   - Click **Apply & Restart** to save the changes.

3. **Verify the Configuration:**
   - After Docker restarts, try running your `bountybench` workflow again.
   - The error should be resolved, allowing Docker to access the necessary directories.

