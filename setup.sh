#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Function to print error messages and exit
function error_exit {
    echo "Error: $1" >&2
    exit 1
}

# 1. Check if the Python version is 3.11
echo "Checking Python version..."
PYTHON_VERSION=$(python --version 2>&1)

if [[ $PYTHON_VERSION == "Python 3.11"* ]]; then
    echo "✅ Python version is 3.11."
else
    error_exit "Python 3.11 is required. Current version: $PYTHON_VERSION"
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
    git submodule update --init || error_exit "Failed to initialize submodules in 'bountybench'."
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
