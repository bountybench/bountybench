#!/bin/bash

# Pod Monitor Script for Backend Pods
# This script provides a terminal-based interface to monitor Kubernetes backend pods

# ANSI color codes for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Function to check if kubectl is available
check_kubectl() {
  if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl is not installed or not in PATH${NC}"
    exit 1
  fi
}

# Function to check if we can access the cluster
check_cluster_access() {
  if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}Error: Cannot connect to Kubernetes cluster${NC}"
    echo -e "Please check your kubeconfig or cluster connection"
    exit 1
  fi
}

# Function to get all backend pods
get_backend_pods() {
  kubectl get pods -o jsonpath='{.items[?(@.metadata.labels.app=="backend")].metadata.name}'
}

# Function to count backend pods
count_backend_pods() {
  local pods=$(get_backend_pods)
  if [ -z "$pods" ]; then
    echo 0
  else
    echo "$pods" | wc -w | tr -d ' '
  fi
}

# Function to display pod status
display_pod_status() {
  echo -e "\n${BOLD}${BLUE}===== Backend Pod Status =====${NC}"
  kubectl get pods -l app=backend -o wide
  echo ""
}

# Function to display pod details
display_pod_details() {
  local pod_name=$1
  echo -e "\n${BOLD}${BLUE}===== Pod Details: $pod_name =====${NC}"
  kubectl describe pod "$pod_name" | grep -E 'Name:|Namespace:|Status:|IP:|Node:|Start Time:|Containers:|Ready:|Restart Count:|Image:|State:|Reason:|Message:|Mounts:|Environment:|Conditions:'
  echo ""
}

# Function to stream logs from a pod
stream_logs() {
  local pod_name=$1
  local lines=$2
  
  if [ -z "$lines" ]; then
    lines=50
  fi
  
  clear
  echo -e "${BOLD}${CYAN}Streaming logs from pod: $pod_name${NC}"
  echo -e "${YELLOW}Press Ctrl+C to stop streaming and return to menu${NC}\n"
  
  kubectl logs -f "$pod_name" --tail="$lines"
}

# Function to display the menu
display_menu() {
  local pods=($@)
  local pod_count=${#pods[@]}
  
  clear
  echo -e "${BOLD}${GREEN}=======================================${NC}"
  echo -e "${BOLD}${GREEN}      BACKEND POD MONITOR TOOL         ${NC}"
  echo -e "${BOLD}${GREEN}=======================================${NC}\n"
  
  display_pod_status
  
  echo -e "${BOLD}Available Actions:${NC}"
  
  for i in "${!pods[@]}"; do
    echo -e "${CYAN}$((i+1))${NC}) View logs for pod: ${BOLD}${pods[$i]}${NC}"
    echo -e "${CYAN}$((i+1))d${NC}) View details for pod: ${BOLD}${pods[$i]}${NC}"
  done
  
  echo -e "${CYAN}r${NC}) Refresh pod list"
  echo -e "${CYAN}q${NC}) Quit"
  echo ""
  echo -e "${BOLD}Enter your choice:${NC} "
}

# Main function
main() {
  check_kubectl
  check_cluster_access
  
  echo -e "${BOLD}${BLUE}Checking for backend pods...${NC}"
  
  local pod_count=$(count_backend_pods)
  
  if [ "$pod_count" -eq 0 ]; then
    echo -e "${RED}No backend pods found!${NC}"
    echo -e "Make sure the backend deployment is running with:"
    echo -e "${YELLOW}kubectl apply -f backend.yaml${NC}"
    exit 1
  fi
  
  echo -e "${GREEN}Found $pod_count backend pod(s)${NC}"
  
  while true; do
    local pods=($(get_backend_pods))
    
    # If pods disappeared during runtime
    if [ ${#pods[@]} -eq 0 ]; then
      echo -e "${RED}No backend pods available anymore. Exiting...${NC}"
      exit 1
    fi
    
    display_menu "${pods[@]}"
    
    read -r choice
    
    case $choice in
      [0-9]*d)
        # Extract the numeric part by removing the 'd' at the end
        number_part=$(echo "$choice" | sed 's/d$//')
        index=$((number_part-1))
        if [ "$index" -ge 0 ] && [ "$index" -lt "${#pods[@]}" ]; then
          display_pod_details "${pods[$index]}"
          echo -e "Press any key to continue..."
          read -n 1
        else
          echo -e "${RED}Invalid choice. Press any key to continue...${NC}"
          read -n 1
        fi
        ;;
      [0-9]*)
        index=$((choice-1))
        if [ "$index" -ge 0 ] && [ "$index" -lt "${#pods[@]}" ]; then
          stream_logs "${pods[$index]}" 50
        else
          echo -e "${RED}Invalid choice. Press any key to continue...${NC}"
          read -n 1
        fi
        ;;
      r|R)
        echo -e "${BLUE}Refreshing pod list...${NC}"
        ;;
      q|Q)
        echo -e "${GREEN}Exiting. Goodbye!${NC}"
        exit 0
        ;;
      *)
        echo -e "${RED}Invalid choice. Press any key to continue...${NC}"
        read -n 1
        ;;
    esac
  done
}

# Run the main function
main
