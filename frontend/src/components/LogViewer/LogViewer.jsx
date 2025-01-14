import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import './LogViewer.css';

export const LogViewer = ({ workflow }) => {
  return (
    <Box className="log-container">
      <Typography variant="h6" gutterBottom>
        Workflow Logs
      </Typography>
      <Paper className="log-content">
        <div className="log-info">[INFO] Initializing workflow...</div>
        <div className="log-info">[INFO] Setting up resources...</div>
        <div className="log-info">[INFO] Loading agents...</div>
      </Paper>
    </Box>
  );
};
