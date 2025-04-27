
## Installation
### Environment Setup

You can quickly set up the dev environment by running the following command:
```
./setup.sh
source venv/bin/activate
```

To initialize all submodules, run:
```
./setup.sh --all
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

Additionally, please install `tree`:

macOS (using Homebrew):
```
brew install tree
```

or Debian/Ubuntu (using APT):
```
sudo apt-get install tree
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
HACKERONE_API_IDENTIFIER={HACKERONE_API_IDENTIFIER}
HACKERONE_API_KEY={HACKERONE_API_KEY}
```
Replace {KEY_NAME} with your actual API key values (make sure you don't include {} when adding the key, e.g. KEY=XYZ...). You only need to fill in whichever keys you will use. 

### 5. Setup Docker Desktop App. 
Make sure that you have started up your Docker Desktop App before proceeding with running a workflow. 

#### (OPTIONAL) HackerOne API Setup

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
It should list the contents of your current working directory. If you encounter a mounting issue, please follow [Docker Mount Issue](usage.md#troubleshooting) for next steps.
