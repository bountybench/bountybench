import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router';
import { Box, CircularProgress, Alert, Typography } from '@mui/material';
import AgentInteractions from '../AgentInteractions/AgentInteractions';
import { useWorkflowWebSocket } from '../../hooks/useWorkflowWebSocket';
import './WorkflowDashboard.css';

const WorkflowState = {
  LOADING: 'LOADING',
  CONNECTING: 'CONNECTING',
  STARTING: 'STARTING',
  RUNNING: 'RUNNING',
  COMPLETED: 'COMPLETED',
  ERROR: 'ERROR',
  STOPPED: 'STOPPED'
};

export const WorkflowDashboard = ({ interactiveMode, onWorkflowStateUpdate, showInvalidWorkflowToast }) => {
  const { workflowId } = useParams();
  const [isNextDisabled, setIsNextDisabled] = useState(false);
  const [preservedMessages, setPreservedMessages] = useState([]);
  const [hasCheckedValidity, setHasCheckedValidity] = useState(false);
  
  const [workflowState, setWorkflowState] = useState({
    status: WorkflowState.LOADING,
    message: "Loading workflow instance...",
    error: null
  });

  const navigate = useNavigate();
  
  // Fetch active workflows to check if given workflowId exists
  useEffect(() => {
    const checkIfWorkflowExists = async () => {
      const response = await fetch('http://localhost:8000/workflow/active');
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
    currentIteration,
    messages,
    error,
  } = useWorkflowWebSocket(workflowId);
  
  console.log('WebSocket state:', { 
    isConnected, 
    workflowStatus, 
    currentPhase, 
    currentIteration,
    error,
    messageCount: messages?.length 
  }); // Debug log

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
    } else if (workflowStatus === 'completed') {
      setWorkflowState({
        status: WorkflowState.COMPLETED,
        message: "Workflow completed",
        error: null
      });
      setPreservedMessages(messages);
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
  }, [isConnected, workflowStatus, currentPhase, messages, error, onWorkflowStateUpdate]);

  const triggerNextIteration = async () => {
    if (workflowStatus === "stopped") {
      console.error("Cannot trigger next iteration: Workflow is stopped.");
      return;
    }
    if (workflowId) {
      setIsNextDisabled(true);
      try {
        const response = await fetch(`http://localhost:8000/workflow/${workflowId}/next`, {
          method: 'POST',
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
    const url = `http://localhost:8000/workflow/${workflowId}/edit-message`;
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

  const handleRerunMessage = async (messageId) => {
    if (workflowId) {
      setIsNextDisabled(true);
      try {
        const response = await fetch(`http://localhost:8000/workflow/${workflowId}/rerun-message`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ message_id: messageId }),
        });
        const data = await response.json();
        if (data.error) {
          console.error('Error rerunning action:', data.error);
        } else {
          console.log('Action rerun successfully', data);
        }
      } catch (error) {
        console.error('Error rerunning action:', error);
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
        const response = await fetch(`http://localhost:8000/workflow/${workflowId}/stop`, {
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

  if (workflowState.status === WorkflowState.ERROR) {
    return (
      <Box p={2}>
        <Alert severity="error">{workflowState.error || workflowState.message}</Alert>
      </Box>
    );
  }

  if (workflowState.status === WorkflowState.LOADING || 
      workflowState.status === WorkflowState.CONNECTING ||
      workflowState.status === WorkflowState.STARTING) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="100%">
        <Box className="launcher-loading" display="flex" flexDirection="column" alignItems="center">
          <CircularProgress />
          <Typography>{workflowState.message}</Typography>
        </Box>
      </Box>
    );
  }

  const displayMessages = workflowState.status === WorkflowState.COMPLETED ? preservedMessages : messages;

  return (
    <Box height="100%" overflow="auto">
      <AgentInteractions
        interactiveMode={interactiveMode}
        workflowStatus={workflowStatus}  // Pass the workflow status
        currentPhase={currentPhase}
        currentIteration={currentIteration}
        isNextDisabled={isNextDisabled}
        messages={displayMessages}
        onUpdateMessageInput={handleUpdateMessageInput}
        onRerunMessage={handleRerunMessage}
        onTriggerNextIteration={triggerNextIteration}
        onStopWorkflow={handleStopWorkflow}
      />
    </Box>
  );
};