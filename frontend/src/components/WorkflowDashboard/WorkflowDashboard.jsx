import React, { useState } from 'react';
import { Box, Typography, CircularProgress, Alert, Button, Grid, IconButton, Dialog, DialogTitle, DialogContent, DialogActions, TextField } from '@mui/material';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import { AgentInteractions } from '../AgentInteractions/AgentInteractions';
import { PhasePanel } from '../PhasePanel/PhasePanel';
import { AgentPanel } from '../AgentPanel/AgentPanel';
import { ResourcePanel } from '../ResourcePanel/ResourcePanel';
import { useWorkflowWebSocket } from '../../hooks/useWorkflowWebSocket';
import './WorkflowDashboard.css';

export const WorkflowDashboard = ({ selectedWorkflow, interactiveMode }) => {
  const [isPanelExpanded, setIsPanelExpanded] = useState(true);
  const [editedMessage, setEditedMessage] = useState("");

  const {
    isConnected,
    workflowStatus,
    currentPhase,
    messages,
    error,
    pendingUserInput,
    sendUserResponse
  } = useWorkflowWebSocket(selectedWorkflow?.id, interactiveMode);

  const handleUserResponse = () => {
    if (pendingUserInput) {
      sendUserResponse(pendingUserInput.messageId, {
        message: {
          content: editedMessage,
          ...pendingUserInput.message
        }
      });
      setEditedMessage("");
    }
  };

  return (
    <Box className="dashboard-container">
      <Grid container spacing={2}>
        {/* Left Panel */}
        <Grid item xs={isPanelExpanded ? 3 : 1}>
          <Box className="left-panel">
            <IconButton 
              onClick={() => setIsPanelExpanded(!isPanelExpanded)}
              className="panel-toggle"
            >
              {isPanelExpanded ? <ChevronLeftIcon /> : <ChevronRightIcon />}
            </IconButton>
            
            {isPanelExpanded && (
              <>
                <PhasePanel currentPhase={currentPhase} />
                <AgentPanel />
                <ResourcePanel />
              </>
            )}
          </Box>
        </Grid>

        {/* Main Content */}
        <Grid item xs={isPanelExpanded ? 9 : 11}>
          <Box className="main-content">
            {/* Connection Status */}
            {!isConnected && (
              <Alert severity="warning" className="status-alert">
                Connecting to workflow...
              </Alert>
            )}

            {/* Error Display */}
            {error && (
              <Alert severity="error" className="status-alert">
                {error}
              </Alert>
            )}

            {/* Workflow Status */}
            <Typography variant="h6" className="status-text">
              Status: {workflowStatus || 'Initializing'}
            </Typography>

            {/* Messages Display */}
            <AgentInteractions messages={messages} />

            {/* Interactive Mode Dialog */}
            <Dialog 
              open={Boolean(pendingUserInput)} 
              onClose={() => {/* Don't allow closing */}}
              maxWidth="md"
              fullWidth
            >
              <DialogTitle>
                Agent {pendingUserInput?.agentName} Requests Input
              </DialogTitle>
              <DialogContent>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle1" gutterBottom>
                    Original Message:
                  </Typography>
                  <Typography variant="body1">
                    {pendingUserInput?.message?.content}
                  </Typography>
                </Box>
                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  variant="outlined"
                  label="Edit Message"
                  value={editedMessage}
                  onChange={(e) => setEditedMessage(e.target.value)}
                  defaultValue={pendingUserInput?.message?.content}
                />
              </DialogContent>
              <DialogActions>
                <Button 
                  onClick={handleUserResponse}
                  variant="contained" 
                  color="primary"
                  endIcon={<ArrowForwardIcon />}
                >
                  Send Response
                </Button>
              </DialogActions>
            </Dialog>
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
};
