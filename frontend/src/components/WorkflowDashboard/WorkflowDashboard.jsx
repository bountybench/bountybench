import React from 'react';
import { Box, Typography, CircularProgress, Alert } from '@mui/material';
import { AgentInteractions } from '../AgentInteractions/AgentInteractions';
import { useWorkflowWebSocket } from '../../hooks/useWorkflowWebSocket';
import './WorkflowDashboard.css';

export const WorkflowDashboard = ({ selectedWorkflow, interactiveMode }) => {
  const {
    isConnected,
    workflowStatus,
    currentPhase,
    currentIteration,
    error,
    sendMessage
  } = useWorkflowWebSocket(selectedWorkflow?.id);

  if (!isConnected) {
    return (
      <Box className="dashboard-container" display="flex" justifyContent="center" alignItems="center">
        <CircularProgress />
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
          Workflow Status: {workflowStatus}
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
          onSendMessage={sendMessage}
        />
      </Box>
    </Box>
  );
};
