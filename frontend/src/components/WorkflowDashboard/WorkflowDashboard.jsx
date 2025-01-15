import React, { useState } from 'react';
import { Box, Typography, CircularProgress, Alert, Button, Grid, IconButton } from '@mui/material';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import { AgentInteractions } from '../AgentInteractions/AgentInteractions';
import { PhasePanel } from '../PhasePanel/PhasePanel';
import { AgentPanel } from '../AgentPanel/AgentPanel';
import { ResourcePanel } from '../ResourcePanel/ResourcePanel';
import { useWorkflowWebSocket } from '../../hooks/useWorkflowWebSocket';
import './WorkflowDashboard.css';

export const WorkflowDashboard = ({ selectedWorkflow, interactiveMode }) => {
  console.log('WorkflowDashboard props:', { selectedWorkflow, interactiveMode }); // Debug log
  
  const [isNextDisabled, setIsNextDisabled] = useState(false);
  const [isPanelExpanded, setIsPanelExpanded] = useState(true);

  const {
    isConnected,
    workflowStatus,
    currentPhase,
    currentIteration,
    messages,
    error,
    sendMessage,
    restartWorkflow
  } = useWorkflowWebSocket(selectedWorkflow?.id);

  console.log('WebSocket state:', { 
    isConnected, 
    workflowStatus, 
    currentPhase, 
    currentIteration,
    messageCount: messages?.length 
  }); // Debug log

  
  const triggerNextIteration = async () => {
    if (selectedWorkflow?.id) {
      setIsNextDisabled(true);
      try {
        const response = await fetch(`http://localhost:8000/workflow/next/${selectedWorkflow.id}`, {
          method: 'POST',
        });
        const data = await response.json();
        if (data.error) {
          console.error('Error triggering next iteration:', data.error);
        } else {
          console.log('Next iteration triggered successfully');
        }
      } catch (error) {
        console.error('Error triggering next iteration:', error);
      } finally {
        setIsNextDisabled(false);
      }
    } else {
      console.error('Workflow ID is not available');
    }
  };

  
  const handleUpdateActionInput = async (actionId, newInputData) => {
    const url = `http://localhost:8000/workflow/edit_action_input/${selectedWorkflow.id}`;
    const requestBody = { action_id: actionId, new_input_data: newInputData };
    
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
  
  const togglePanel = () => {
    setIsPanelExpanded(!isPanelExpanded);
  };

  const handleRestart = async () => {
    if (window.confirm('Are you sure you want to restart the workflow? This will terminate the current workflow and start a new one with the same configuration.')) {
      await restartWorkflow();
    }
  };

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

  return (
    <Box className="dashboard-container">
      <Box className="dashboard-header" display="flex" alignItems="center" justifyContent="space-between" p={2}>
        <Typography variant="h5">
          {selectedWorkflow?.name || 'Workflow Dashboard'}
        </Typography>
        <Box>
          <IconButton
            onClick={handleRestart}
            disabled={!isConnected}
            title="Restart Workflow"
            color="primary"
          >
            <RestartAltIcon />
          </IconButton>
          <IconButton
            onClick={togglePanel}
            title={isPanelExpanded ? 'Collapse Panel' : 'Expand Panel'}
          >
            {isPanelExpanded ? <ChevronRightIcon /> : <ChevronLeftIcon />}
          </IconButton>
        </Box>
      </Box>
        
      <Grid container spacing={2} className="dashboard-content">
        <Grid item xs={12} md={isPanelExpanded ? 8 : 11} className="main-content">
          <AgentInteractions
            workflow={selectedWorkflow}
            interactiveMode={interactiveMode}
            currentPhase={currentPhase}
            currentIteration={currentIteration}
            messages={messages}
            onSendMessage={sendMessage}
            onUpdateActionInput={handleUpdateActionInput}
          />
        </Grid>
        <Grid item xs={12} md={isPanelExpanded ? 4 : 1} className="side-panel-container">
          <Box className="side-panel-wrapper">
            <IconButton
              onClick={togglePanel}
              className="panel-toggle-button"
              size="small"
              color="primary"
            >
              {isPanelExpanded ? <ChevronRightIcon /> : <ChevronLeftIcon />}
            </IconButton>
            {isPanelExpanded && (
              <Box className="side-panel">
                <PhasePanel workflow={selectedWorkflow} /> 
                <AgentPanel workflow={selectedWorkflow} />
                <ResourcePanel workflow={selectedWorkflow} />
              </Box>
            )}
          </Box>
        </Grid>
      </Grid>
      {interactiveMode && (
        <Box className="dashboard-footer" display="flex" justifyContent="center" p={2}>
          <Button
            variant="contained"
            color="primary"
            onClick={triggerNextIteration}
            startIcon={<ArrowForwardIcon />}
            disabled={isNextDisabled}
          >
            Next Iteration
          </Button>
        </Box>
      )}
    </Box>
  );
};
