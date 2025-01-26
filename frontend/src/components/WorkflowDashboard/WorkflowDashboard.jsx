import React, { useState, useEffect } from 'react';
import { Box, Typography, CircularProgress, Alert, Button, Grid, IconButton } from '@mui/material';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import AgentInteractions from '../AgentInteractions/AgentInteractions';
import { useWorkflowWebSocket } from '../../hooks/useWorkflowWebSocket';
import './WorkflowDashboard.css';

export const WorkflowDashboard = ({ selectedWorkflow, interactiveMode, onWorkflowStateUpdate }) => {
  console.log('WorkflowDashboard props:', { selectedWorkflow, interactiveMode });
  
  const [isNextDisabled, setIsNextDisabled] = useState(false);
  const [preservedMessages, setPreservedMessages] = useState([]);

  const {
    isConnected,
    workflowStatus,
    currentPhase,
    currentIteration,
    messages,
    error,
    sendMessage,
  } = useWorkflowWebSocket(selectedWorkflow?.id);

  // Update parent component with workflow state
  useEffect(() => {
    onWorkflowStateUpdate(workflowStatus, currentPhase);
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
  }, [selectedWorkflow]);
  
  const triggerNextIteration = async () => {
    if (selectedWorkflow?.id) {
      setIsNextDisabled(true);
      try {
        const response = await fetch(`http://localhost:8000/workflow/next/${selectedWorkflow.id}`, {
          method: 'POST',
        });
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log('Next iteration triggered successfully', data);
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
    const url = `http://localhost:8000/workflow/edit-message/${selectedWorkflow.id}`;
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
  
      console.log('Response status:', response.status);
      console.log('Response headers:', response.headers);
  
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
    if (selectedWorkflow?.id) {
      try {
        const response = await fetch(`http://localhost:8000/workflow/rerun-message/${selectedWorkflow.id}`, {
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

  if (!isConnected) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="100%">
        <CircularProgress size={24} />
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
      />
    </Box>
  );
};