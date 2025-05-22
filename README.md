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
    - [Running the Workflow](#running-workflows)
    - [Running the Application](#running-the-application)
      - [Concurrent run](#concurrent-run)
      - [Backend Setup](#backend-setup)
      - [Frontend Setup](#frontend-setup)
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

Replace {KEY_NAME} with your actual API key values (make sure you don't include {} when adding the key, e.g. KEY=XYZ...). You only need to fill in whichever keys you will use.

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
- `exploit_patch_workflow`:
- `patch_workflow`:
- `detect_patch_workflow`:

Required flags vary by workflow type.

Examples:

1. **Exploit and Patch Workflow**:
```bash
python -m workflows.runner --workflow-type exploit_patch_workflow \
    --task_dir bountytasks/lunary \
    --bounty_number 0 \
    --model anthropic/claude-3-5-sonnet-20241022 \
    --phase_iterations 3
```

2. **Detect Patch Workflow**:
```bash
python -m workflows.runner --workflow-type detect_patch_workflow \
    --task_dir bountytasks/django \
    --bounty_number 0 \
    --model anthropic/claude-3-sonnet-20240229 \
    --phase_iterations 2 \
    --use_helm
```

3. **Patch Only Workflow**:
```bash
python -m workflows.runner --workflow-type patch_workflow \
    --task_dir bountytasks/mlflow \
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

1. Open a terminal and navigate to the `bountybench` directory.

2. Start the backend server:

```bash
python -m backend.main
```

Note: The backend will take about a minute to initialize. You can view incremental, verbose run updates in this terminal window.

#### Frontend Setup

1. Open a new terminal and navigate to the `bountybench/frontend` directory.

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

### Using Git Inside Containers
Depending on the hardware setup, building the container could take anywhere from 5 minutes to much longer. Because dependencies changes are less frequent than codebase changes, a possible solution is to building the container once, and then use git in the container to fetch the latest changes from `bountybench/` (`app/`) and `bountytasks/` (`app/bountytasks`) repos. Inside the container, you could also `git checkout` different branches for testing. 

SSH keys are needed for `git pull` and `git fetch` to work. **Before running `docker compose up --build -d`, please the follow these steps to set up the git credentials correctly.** 

**If you do not wish to use git, please skip to step 3, and you can safely delete these two lines from your `docker-compose.yml`.**

1. Please make sure you cloned the repository with ssh:
```
git clone git@github.com:cybench/bountyagent.git
```
2. To create a new pair of ssh keys specific for the container, run:

```
chmod +x tools/ssh_key_gen.sh && \
tools/ssh_key_gen.sh
```

and copy the public key (i.e. the output) to [GitHub/settings/keys](https://github.com/settings/keys). 

3. Please uncomment these two lines in `docker-compose.yml` to mount the keys to the container:
```
  - ${HOME}/.ssh/id_rsa_backend-service:/root/.ssh/id_rsa:ro
  - ${HOME}/.ssh/id_rsa_backend-service.pub:/root/.ssh/id_rsa.pub:ro
```
4. (Optional) If you want to fetch the latest version of bountytasks, run:
```
cd bountytasks
git checkout main
git pull
```

We have also provide a bash script `dockerize_run.sh` that serves as an easy interface to run the application using docker.

### Sample Run

![Screen recording of a run](documentation/docs/media/sample_run.gif)

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

