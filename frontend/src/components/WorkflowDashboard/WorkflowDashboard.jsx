import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router';
import { Box, CircularProgress, Alert, Typography } from '@mui/material';
import AgentInteractions from '../AgentInteractions/AgentInteractions';
import { useWorkflowWebSocket } from '../../hooks/useWorkflowWebSocket';
import './WorkflowDashboard.css';

export const WorkflowDashboard = ({ interactiveMode, onWorkflowStateUpdate, showInvalidWorkflowToast }) => {
  const { workflowId } = useParams();
  const [isNextDisabled, setIsNextDisabled] = useState(false);
  const [preservedMessages, setPreservedMessages] = useState([]);
  const [hasCheckedValidity, setHasCheckedValidity] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("Loading workflow instance..."); // Initial loading message
  const [isLoading, setIsLoading] = useState(true); // State to manage loading visibility

  const navigate = useNavigate();
  
  // Fetch active workflows to check if given workflowId exists
  useEffect(() => {
    const checkIfWorkflowExists = async () => {
      const response = await fetch('http://localhost:8000/workflows/active');
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
    sendMessage,
  } = useWorkflowWebSocket(workflowId);

  // Update parent component with workflow state
  useEffect(() => {
    onWorkflowStateUpdate(workflowStatus, currentPhase);

    // Update loading messages based on workflow status
    if (workflowStatus === 'starting') {
      setLoadingMessage('Starting workflow, setting up first phase...');
    } else if (workflowStatus && workflowStatus !== 'starting') {
      setIsLoading(false);
    }

  }, [workflowStatus, currentPhase, onWorkflowStateUpdate]);
  
  console.log('WebSocket state:', { 
    isConnected, 
    workflowStatus, 
    currentPhase, 
    currentIteration,
    error,
    messageCount: messages?.length 
  }); // Debug log

  useEffect(() => {
    if (workflowStatus === 'completed') {
      console.log('Workflow completed. Preserving messages:', messages);
      setPreservedMessages(messages);
    }
  }, [workflowStatus, messages]);
  
  // Next iteration via ctrl + enter
  useEffect(() => {
    const handleKeyDown = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
        event.preventDefault();
        triggerNextIteration();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [workflowId]);
  
  const triggerNextIteration = async () => {
    if (workflowId) {
      setIsNextDisabled(true);
      try {
        const response = await fetch(`http://localhost:8000/workflow/next/${workflowId}`, {
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

  const handleUpdateActionInput = async (messageId, newInputData) => {
    const url = `http://localhost:8000/workflow/edit-message/${workflowId}`;
    const requestBody = { message_id: messageId, new_input_data: newInputData };
    
    console.log('Sending request to:', url);
    console.log('Request body:', JSON.stringify(requestBody));
  
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
    }
  };

  const handleRerunAction = async (messageId) => {
    if (workflowId) {
      try {
        const response = await fetch(`http://localhost:8000/workflow/rerun-message/${workflowId}`, {
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
      }
    } else {
      console.error('Workflow ID is not available');
    }
  };
  
  console.log('Rendering WorkflowDashboard with messages:', workflowStatus === 'completed' ? preservedMessages : messages);

  if (error) {
    return (
      <Box p={2}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }


  const handleStopWorkflow = async () => {
    if (workflowId) {
      try {
        const response = await fetch(`http://localhost:8000/workflow/stop/${workflowId}`, {
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

  if (error) {
    return (
      <Box p={2}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!isConnected || isLoading) { // Show loading state
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="100%">
        <Box className="launcher-loading" display="flex" flexDirection="column" alignItems="center">
          <CircularProgress />
          <Typography>{loadingMessage}</Typography>
        </Box>
      </Box>
    );
  }

  const displayMessages = workflowStatus === 'completed' ? preservedMessages : messages;

  return (
    <Box height="100%" overflow="auto">
      <AgentInteractions
        interactiveMode={interactiveMode}
        currentPhase={currentPhase}
        currentIteration={currentIteration}
        isNextDisabled={isNextDisabled}
        messages={displayMessages}
        onSendMessage={sendMessage}
        onUpdateActionInput={handleUpdateActionInput}
        onRerunAction={handleRerunAction}
        onTriggerNextIteration={triggerNextIteration}
        onStopWorkflow={handleStopWorkflow}
      />
    </Box>
  );
};