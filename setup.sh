#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Function to print error messages and exit
function error_exit {
    echo "Error: $1" >&2
    exit 1
}

# Parse command line arguments
INIT_ALL=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --all)
            INIT_ALL=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# 1. Check if the Python version is 3.11
echo "Checking Python version..."
PYTHON_VERSION=$(python --version 2>&1)

if [[ "$PYTHON_VERSION" != *"3.11"* ]]; then
    error_exit "Python 3.11 is required. Please install it first."
fi

# 2. Install tree command if missing
echo "Checking for 'tree' command..."
if ! command -v tree &> /dev/null; then
    echo "⏳ Installing tree utility..."
    
    # Detect package manager
    if command -v brew &> /dev/null; then
        brew install tree || error_exit "Failed to install tree via Homebrew"
    elif command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y tree || error_exit "Failed to install tree via apt-get"
    else
        error_exit "Could not detect supported package manager (brew/apt-get) for tree installation"
    fi
    
    echo "✅ Successfully installed tree"
else
    echo "✅ tree already installed"
fi

# 2. Set up a virtual environment and install requirements
VENV_DIR="venv"

if [ -d "$VENV_DIR" ]; then
    echo "🔄 Virtual environment already exists. Activating..."
    source "$VENV_DIR/bin/activate"
else
    echo "🛠️ Creating a new virtual environment..."
    python -m venv "$VENV_DIR" || error_exit "Failed to create virtual environment."
    source "$VENV_DIR/bin/activate" || error_exit "Failed to activate virtual environment."
fi

echo "📦 Upgrading pip..."
pip install --upgrade pip || error_exit "Failed to upgrade pip."

echo "📄 Installing requirements from requirements.txt..."
pip install -r requirements.txt || error_exit "Failed to install requirements."

# 3. Initialize git submodules
echo "🔗 Initializing git submodules..."
git submodule update --init || error_exit "Failed to initialize submodules."

# Check if the 'bountybench' directory exists before updating its submodules
if [ -d "bountybench" ]; then
    echo "🔗 Initializing submodules within 'bountybench'..."
    cd bountybench
    if [ "$INIT_ALL" = true ]; then
        git submodule update --init || error_exit "Failed to initialize all submodules in 'bountybench'."
    else
        echo "⚠️ Initializing test submodules..."
        TEST_SUBMODULES=(
            "astropy"
            "lunary"
            "gunicorn"
            "setuptools"
        )
        
        if [ ${#TEST_SUBMODULES[@]} -eq 0 ]; then
            echo "⚠️ No test submodules specified. Skipping initialization."
        else
            git submodule update --init "${TEST_SUBMODULES[@]}" || error_exit "Failed to initialize test submodules in 'bountybench'."
        fi
    fi
    cd ..
else
    echo "⚠️ Directory 'bountybench' does not exist."
    error_exit "Failed to initialize submodules in 'bountybench'."
fi

# 4. Check for a .env file; create one from .env_template if it doesn't exist
ENV_FILE=".env"
ENV_TEMPLATE_FILE=".env_template"

if [ -f "$ENV_FILE" ]; then
    echo "📄 .env file already exists."
else
    if [ -f "$ENV_TEMPLATE_FILE" ]; then
        echo "📝 .env file not found. Creating one from .env_template..."
        cp "$ENV_TEMPLATE_FILE" "$ENV_FILE" || error_exit "Failed to copy from .env_template to .env."
        echo "✅ .env file created from .env_template."
    else
        error_exit ".env_template file does not exist. Cannot create .env file."
    fi
fi


# 5. Verify Docker is installed
echo "🐳 Checking if Docker is installed..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo "✅ Docker is installed: $DOCKER_VERSION"
else
    error_exit "Docker is not installed. Please install Docker and try again."
fi

echo "🎉 Setup completed successfully!"
