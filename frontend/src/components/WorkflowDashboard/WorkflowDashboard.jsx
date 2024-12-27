import React from 'react';
import { Box, Grid, Paper } from '@mui/material';
import { WorkflowPhases } from '../WorkflowPhases/WorkflowPhases';
import { AgentInteractions } from '../AgentInteractions/AgentInteractions';
import { ResourcePanel } from '../ResourcePanel/ResourcePanel';
import { LogViewer } from '../LogViewer/LogViewer';
import './WorkflowDashboard.css';

export const WorkflowDashboard = ({ selectedWorkflow, interactiveMode }) => {
  return (
    <Box className="dashboard-container">
      <Grid container spacing={2} className="dashboard-grid">
        {/* Left Panel - Workflow Phases */}
        <Grid item xs={3}>
          <Paper className="dashboard-panel">
            <WorkflowPhases workflow={selectedWorkflow} />
          </Paper>
        </Grid>

        {/* Center Panel - Agent Interactions */}
        <Grid item xs={6}>
          <Paper className="dashboard-panel">
            <AgentInteractions 
              workflow={selectedWorkflow}
              interactiveMode={interactiveMode}
            />
          </Paper>
        </Grid>

        {/* Right Panel - Resources and Logs */}
        <Grid item xs={3}>
          <Grid container spacing={2} direction="column" className="right-panel">
            <Grid item xs={6}>
              <Paper className="dashboard-panel">
                <ResourcePanel workflow={selectedWorkflow} />
              </Paper>
            </Grid>
            <Grid item xs={6}>
              <Paper className="dashboard-panel">
                <LogViewer workflow={selectedWorkflow} />
              </Paper>
            </Grid>
          </Grid>
        </Grid>
      </Grid>
    </Box>
  );
};
