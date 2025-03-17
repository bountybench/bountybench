import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router';
import { Box, CircularProgress, Alert, Typography, IconButton } from '@mui/material';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import AgentInteractions from '../AgentInteractions/AgentInteractions';
import ResourceDict from '../ResourceDict/ResourceDict';
import { useWorkflowWebSocket } from '../../hooks/useWorkflowWebSocket';
import './WorkflowDashboard.css';

import { API_BASE_URL } from '../../config';

const WorkflowState = {
  LOADING: 'LOADING',
  CONNECTING: 'CONNECTING',
  STARTING: 'STARTING',
  RUNNING: 'RUNNING',
  COMPLETED: 'COMPLETED',
  ERROR: 'ERROR',
  STOPPED: 'STOPPED',
  RESTARTING: 'RESTARTING'
};

export const WorkflowDashboard = ({ interactiveMode, onWorkflowStateUpdate, showInvalidWorkflowToast,   useMockModel,
  setUseMockModel }) => {
  const { workflowId } = useParams();
  const [isNextDisabled, setIsNextDisabled] = useState(false);
  const [hasCheckedValidity, setHasCheckedValidity] = useState(false);
  const [preservedMessages, setPreservedMessages] = useState([]);
  
  const [resources, setResources] = useState([]);
  const [isResourcePanelOpen, setIsResourcePanelOpen] = useState(false);
  const [restart, setRestart] = useState(0);

  const [workflowState, setWorkflowState] = useState({
    status: WorkflowState.LOADING,
    message: "Loading workflow instance...",
    error: null
  });

  const navigate = useNavigate();
   
  // Fetch active workflows to check if given workflowId exists
  useEffect(() => {
    const checkIfWorkflowExists = async () => {
      const response = await fetch(`${API_BASE_URL}/workflow/active`);
      const data = await response.json();

      if (!data.active_workflows.some(workflow => workflow.id === workflowId)) {
        showInvalidWorkflowToast();
        navigate(`/`); 
      }
    };

    if (!hasCheckedValidity) { // Check if validity has already been checked
      checkIfWorkflowExists();
      setHasCheckedValidity(true);
    }
  }, [workflowId, navigate, showInvalidWorkflowToast, hasCheckedValidity]);

  const {
    isConnected,
    workflowStatus,
    currentPhase,
    phaseMessages,
    error,
  } = useWorkflowWebSocket(workflowId, restart);
  
  console.log('WebSocket state:', { 
    isConnected, 
    workflowStatus, 
    currentPhase,
    error,
    phaseMessagesCount: phaseMessages?.length
  });

  const getTailMessageId = async () => {
    if (phaseMessages?.length > 0 && phaseMessages[phaseMessages.length - 1].current_children?.length > 0) {
      const lastMessage = phaseMessages[phaseMessages.length - 1].current_children[phaseMessages[phaseMessages.length - 1].current_children.length - 1];
      return lastMessage.current_id;
    }
    return null;
  };
  
  useEffect(() => {
    if (error) {
      setWorkflowState({
        status: WorkflowState.ERROR,
        message: "An error occurred",
        error: error
      });
    } else if (!isConnected) {
      setWorkflowState({
        status: WorkflowState.CONNECTING,
        message: "Connecting to workflow...",
        error: null
      });
    } else if (workflowStatus === 'starting') {
      setWorkflowState({
        status: WorkflowState.STARTING,
        message: "Starting workflow, setting up first phase...",
        error: null
      });
    } else if (workflowStatus === 'restarting') {
      setWorkflowState({
        status: WorkflowState.RESTARTING,
        message: "Workflow restarting",
        error: null
      });
    } else if (workflowStatus === 'completed') {
      setWorkflowState({
        status: WorkflowState.COMPLETED,
        message: "Workflow completed",
        error: null
      });
      setPreservedMessages(phaseMessages);
    } else if (workflowStatus === 'stopped') {
      setWorkflowState({
        status: WorkflowState.STOPPED,
        message: "Workflow stopped",
        error: null
      });
    } else if (workflowStatus) {
      setWorkflowState({
        status: WorkflowState.RUNNING,
        message: `Workflow ${workflowStatus}`,
        error: null
      });
    }

    console.log(`Workflow state updated to ${workflowStatus}`)
    onWorkflowStateUpdate(workflowStatus, currentPhase);
  }, [isConnected, workflowStatus, currentPhase, phaseMessages, error, onWorkflowStateUpdate]);

  const handleRestart = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/workflow/restart/${workflowId}`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      console.log('Workflow restarted successfully');
    } catch (error) {
      console.error('Error restarting workflow:', error);
    } finally {
      setRestart((prev) => prev + 1);
    }
  };

  const fetchResources = useCallback(async () => {
    if (!workflowId) {
      console.log('Skipping resource fetch - no workflow ID available');
      return;
    }

    if (workflowId) {
      try {
        const response = await fetch(`${API_BASE_URL}/workflow/${workflowId}/resources`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log("resources: ", data)
        setResources(data.resources);
      } catch (error) {
        console.error('Error fetching resources:', error);
      }
    }
  }, [workflowId]);


  useEffect(() => {
    fetchResources();
  }, [phaseMessages, useMockModel, fetchResources]);

  const toggleResourcePanel = () => {
    setIsResourcePanelOpen(!isResourcePanelOpen);
  };

  const triggerNextIteration = async (iterNum, iterType) => {
    if (workflowStatus === "stopped") {
      console.error("Cannot trigger next iteration: Workflow is stopped.");
      return;
    }
    if (workflowId) {
      setIsNextDisabled(true);
      try {
        const currentMessageId = await getTailMessageId();
        console.log(`Tail message id is ${currentMessageId}, proceed to next ${iterNum} ${iterType} iteration(s)`)
        const response = await fetch(`${API_BASE_URL}/workflow/${workflowId}/run-message`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ message_id: currentMessageId, num_iter: iterNum, type_iter: iterType }),
        });
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log('Next iteration triggered successfully', data);
      } catch (error) {
        console.error('Error triggering next iteration:', error);
      } finally {
        setIsNextDisabled(false);
      }
    } else {
      console.error('Workflow ID is not available');
    }
  };

  const handleUpdateMessageInput = async (messageId, newInputData) => {
    const url = `${API_BASE_URL}/workflow/${workflowId}/edit-message`;
    const requestBody = { message_id: messageId, new_input_data: newInputData };
    
    console.log('Sending request to:', url);
    console.log('Request body:', JSON.stringify(requestBody));
  
    setIsNextDisabled(true);
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });
  
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response body:', errorText);
        throw new Error(`HTTP error! status: ${response.status}`);
      }
  
      const data = await response.json();
      console.log('Action updated successfully', data);
    } catch (error) {
      console.error('Error updating action:', error);
    } finally {
      setIsNextDisabled(false);
    }
  };

  const handleRunMessage = async (messageId) => {
    if (workflowId) {
      setIsNextDisabled(true);
      try {
        const response = await fetch(`${API_BASE_URL}/workflow/${workflowId}/run-message`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ message_id: messageId }),
        });
        const data = await response.json();
        if (data.error) {
          console.error('Error running action:', data.error);
        } else {
          console.log('Action run successfully', data);
        }
      } catch (error) {
        console.error('Error running action:', error);
      } finally {
        setIsNextDisabled(false);
      }
    } else {
      console.error('Workflow ID is not available');
    }
  };


  const handleStopWorkflow = async () => {
    if (workflowId) {
      try {
        const response = await fetch(`${API_BASE_URL}/workflow/${workflowId}/stop`, {
          method: 'POST',
        });
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        console.log('Workflow stopped successfully');
      } catch (error) {
        console.error('Error stopping workflow:', error);
      }
    } else {
      console.error('Workflow ID is not available');
    }
  };

  const handleToggleVersion = useCallback(async (messageId, direction) => {
    try {
      const response = await fetch(`${API_BASE_URL}/workflow/${workflowId}/toggle-version`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message_id: messageId, direction }),
      });

      if (!response.ok) {
        throw new Error('Failed to toggle version');
      }

      const result = await response.json();
      console.log(`Toggle version: ${result}`);
      // Updating messages should be triggered by call
    } catch (error) {
      console.error('Error toggling version:', error);
    }
  }, [workflowId]);

  if (workflowState.status === WorkflowState.ERROR) {
    return (
      <Box p={2}>
        <Alert severity="error">{workflowState.error || workflowState.message}</Alert>
      </Box>
    );
  }

  if (workflowState.status === WorkflowState.LOADING || 
      workflowState.status === WorkflowState.CONNECTING ||
      workflowState.status === WorkflowState.STARTING ||
      workflowState.status === WorkflowState.RESTARTING) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="100%">
        <Box className="launcher-loading" display="flex" flexDirection="column" alignItems="center">
          <CircularProgress />
          <Typography>{workflowState.message}</Typography>
        </Box>
      </Box>
    );
  }

  const displayMessages = workflowState.status === WorkflowState.COMPLETED ? preservedMessages : phaseMessages;

  return (
    <Box height="100%" overflow="hidden" display="flex">
      <Box flexGrow={1} overflow="auto">
        <AgentInteractions
          interactiveMode={interactiveMode}
          workflowStatus={workflowStatus}
          currentPhase={currentPhase}
          isNextDisabled={isNextDisabled}
          phaseMessages={displayMessages}
          onUpdateMessageInput={handleUpdateMessageInput}
          onRunMessage={handleRunMessage}
          onTriggerNextIteration={triggerNextIteration}
          onStopWorkflow={handleStopWorkflow}
          onRestart={handleRestart}
          onToggleVersion={handleToggleVersion}
        />
      </Box>
      <Box className={`resource-panel ${isResourcePanelOpen ? 'open' : ''}`}>
        <IconButton
          className="toggle-panel"
          onClick={toggleResourcePanel}
          size="small"
        >
          {isResourcePanelOpen ? <ChevronRightIcon /> : <ChevronLeftIcon />}
        </IconButton>
        <ResourceDict resources={resources} />
      </Box>
    </Box>
  );
};