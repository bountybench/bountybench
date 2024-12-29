import React from 'react';
import { Box, Typography, CircularProgress, Alert } from '@mui/material';
import { AgentInteractions } from '../AgentInteractions/AgentInteractions';
import { useWorkflowWebSocket } from '../../hooks/useWorkflowWebSocket';
import './WorkflowDashboard.css';

export const WorkflowDashboard = ({ selectedWorkflow, interactiveMode }) => {
  console.log('WorkflowDashboard props:', { selectedWorkflow, interactiveMode }); // Debug log
  
  const {
    isConnected,
    workflowStatus,
    currentPhase,
    currentIteration,
    messages,
    error,
    sendMessage
  } = useWorkflowWebSocket(selectedWorkflow?.id);

  console.log('WebSocket state:', { 
    isConnected, 
    workflowStatus, 
    currentPhase, 
    currentIteration,
    messageCount: messages?.length 
  }); // Debug log

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
      <Box className="dashboard-header">
        <Typography variant="h5">
          Workflow Status: {workflowStatus || 'Unknown'}
        </Typography>
        {currentPhase && (
          <Typography variant="h6">
            Current Phase: {currentPhase.phase_name} (Phase {currentPhase.phase_idx + 1})
          </Typography>
        )}
      </Box>
      
      <Box className="dashboard-content">
        <AgentInteractions
          workflow={selectedWorkflow}
          interactiveMode={interactiveMode}
          currentPhase={currentPhase}
          currentIteration={currentIteration}
          messages={messages}
          onSendMessage={sendMessage}
        />
      </Box>
    </Box>
  );
};
