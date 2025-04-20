#!/bin/bash

# Pod Monitor UI Deployment Script
# This script installs dependencies and starts the Pod Monitor UI

# ANSI color codes for better readability
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Get the absolute path to the script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Set the UI directory path
UI_DIR="${SCRIPT_DIR}/pod-monitor-ui"

# Function to check if kubectl is available
check_kubectl() {
  echo -e "${BLUE}Checking if kubectl is installed...${NC}"
  if ! command -v kubectl &> /dev/null; then
    echo -e "${YELLOW}Warning: kubectl is not installed or not in PATH${NC}"
    echo -e "The Pod Monitor UI requires kubectl to communicate with your Kubernetes cluster."
    echo -e "Please install kubectl before using this application."
    exit 1
  fi
  echo -e "${GREEN}kubectl is installed.${NC}"
}

# Function to check if we can access the cluster
check_cluster_access() {
  echo -e "${BLUE}Checking Kubernetes cluster access...${NC}"
  if ! kubectl cluster-info &> /dev/null; then
    echo -e "${YELLOW}Warning: Cannot connect to Kubernetes cluster${NC}"
    echo -e "Please check your kubeconfig or cluster connection"
    exit 1
  fi
  echo -e "${GREEN}Kubernetes cluster is accessible.${NC}"
}

# Function to check if Node.js is installed
check_nodejs() {
  echo -e "${BLUE}Checking if Node.js is installed...${NC}"
  if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}Warning: Node.js is not installed or not in PATH${NC}"
    echo -e "The Pod Monitor UI requires Node.js to run."
    echo -e "Please install Node.js before using this application."
    exit 1
  fi
  echo -e "${GREEN}Node.js is installed: $(node --version)${NC}"
}

# Function to check if npm is installed
check_npm() {
  echo -e "${BLUE}Checking if npm is installed...${NC}"
  if ! command -v npm &> /dev/null; then
    echo -e "${YELLOW}Warning: npm is not installed or not in PATH${NC}"
    echo -e "The Pod Monitor UI requires npm to install dependencies."
    echo -e "Please install npm before using this application."
    exit 1
  fi
  echo -e "${GREEN}npm is installed: $(npm --version)${NC}"
}

# Function to install dependencies
install_dependencies() {
  echo -e "${BLUE}Installing Node.js dependencies...${NC}"
  
  if [ ! -d "$UI_DIR" ]; then
    echo -e "${YELLOW}Error: Pod Monitor UI directory not found at: $UI_DIR${NC}"
    echo -e "Please make sure the pod-monitor-ui directory exists."
    exit 1
  fi
  
  cd "$UI_DIR" || exit 1
  npm install
  if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Warning: Failed to install dependencies${NC}"
    echo -e "Please check the error messages above and try again."
    exit 1
  fi
  echo -e "${GREEN}Dependencies installed successfully.${NC}"
}

# Function to check for backend pods
check_backend_pods() {
  echo -e "${BLUE}Checking for backend pods...${NC}"
  local pods=$(kubectl get pods -l app=backend -o name 2>/dev/null)
  if [ -z "$pods" ]; then
    echo -e "${YELLOW}Warning: No backend pods found${NC}"
    echo -e "The Pod Monitor UI is designed to monitor backend pods."
    echo -e "You can still start the UI, but it won't show any pods until they are deployed."
  else
    local pod_count=$(echo "$pods" | wc -l | tr -d ' ')
    echo -e "${GREEN}Found $pod_count backend pod(s).${NC}"
  fi
}

# Function to start the Pod Monitor UI
start_ui() {
  echo -e "${BLUE}Starting Pod Monitor UI...${NC}"
  
  if [ ! -d "$UI_DIR" ]; then
    echo -e "${YELLOW}Error: Pod Monitor UI directory not found at: $UI_DIR${NC}"
    echo -e "Please make sure the pod-monitor-ui directory exists."
    exit 1
  fi
  
  cd "$UI_DIR" || exit 1
  echo -e "${GREEN}${BOLD}Pod Monitor UI is starting...${NC}"
  echo -e "${YELLOW}Press Ctrl+C to stop the UI server${NC}"
  node server.js
}

# Main function
main() {
  echo -e "${BOLD}${BLUE}===== Pod Monitor UI Deployment =====${NC}"
  
  # Run checks
  check_kubectl
  check_cluster_access
  check_nodejs
  check_npm
  check_backend_pods
  
  # Install dependencies and start UI
  install_dependencies
  start_ui
}

# Run the main function
main
