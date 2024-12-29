# cybountyagent

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

### Running the Workflow UI
To start, install the latest requirements.txt:
```
pip install -r requirements.txt
```

To run the workflow UI, use the following command:
```
cd frontend
npm install
npm run
```

To start the backend server, use the following command:
```
python server.py
```