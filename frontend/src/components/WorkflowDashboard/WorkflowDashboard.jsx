import React, { useState, useEffect } from 'react';
import { Box, Typography, CircularProgress, Alert, Button, Grid, IconButton } from '@mui/material';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import { AgentInteractions } from '../AgentInteractions/AgentInteractions';
import { useWorkflowWebSocket } from '../../hooks/useWorkflowWebSocket';
import './WorkflowDashboard.css';

export const WorkflowDashboard = ({ selectedWorkflow, interactiveMode }) => {
  console.log('WorkflowDashboard props:', { selectedWorkflow, interactiveMode }); // Debug log
  
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

  console.log('WebSocket state:', { 
    isConnected, 
    workflowStatus, 
    currentPhase, 
    currentIteration,
    messageCount: messages?.length 
  }); // Debug log

  useEffect(() => {
    if (workflowStatus === 'completed') {
      console.log('Workflow completed. Preserving messages:', messages);
      setPreservedMessages(messages);
    }
  }, [workflowStatus, messages]);

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
          // You might want to update the UI or refetch messages here
        }
      } catch (error) {
        console.error('Error rerunning action:', error);
      }
    } else {
      console.error('Workflow ID is not available');
    }
  };

  console.log('Rendering WorkflowDashboard with messages:', workflowStatus === 'completed' ? preservedMessages : messages);

  if (!isConnected) {
    return (
      <Box className="dashboard-container" display="flex" justifyContent="center" alignItems="center">
        <CircularProgress />
        <Typography variant="body2" color="text.secondary" sx={{ ml: 2 }}>
          Connecting to workflow...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box className="dashboard-container">
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  const displayMessages = workflowStatus === 'completed' ? preservedMessages : messages;

  return (
    <Box className="dashboard-container">
      <Box className="dashboard-header">
        <Typography variant="h5">
          Workflow Status: {workflowStatus || 'Unknown'}
        </Typography>
        {currentPhase && (
          <Typography variant="h6">
            Current Phase: {currentPhase.phase_id}
          </Typography>
        )}
        {interactiveMode && (
          <Button
            variant="contained"
            color="primary"
            onClick={triggerNextIteration}
            startIcon={<ArrowForwardIcon />}
            disabled={isNextDisabled || workflowStatus === 'completed'}
            sx={{ margin: 1 }}
          >
            Next Iteration
          </Button>
        )}
      </Box>
        
      <Grid container spacing={2} className="dashboard-content">
        <Grid item xs={12} md={12} className="main-content">
          <AgentInteractions
            workflow={selectedWorkflow}
            interactiveMode={interactiveMode}
            currentPhase={currentPhase}
            currentIteration={currentIteration}
            messages={displayMessages}
            onSendMessage={sendMessage}
            onUpdateActionInput={handleUpdateActionInput}
            onRerunAction={handleRerunAction}
          />
        </Grid>
      </Grid>
    </Box>
  );
};