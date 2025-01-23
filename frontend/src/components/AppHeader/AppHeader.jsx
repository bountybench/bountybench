import React from 'react';
import { Box, Typography, Switch } from '@mui/material';

export const AppHeader = ({
  onInteractiveModeToggle,
  interactiveMode,
  selectedWorkflow,
  workflowStatus,
  currentPhase
}) => {
  return (
    <Box 
      display="flex" 
      justifyContent="space-between" 
      alignItems="center" 
      p={1} 
      bgcolor="#266798"
      borderBottom="1px solid #444"
    >
      <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
        Workflow Agent
      </Typography>
      <Box display="flex" alignItems="center">
        {selectedWorkflow && (
          <>
            <Typography variant="body2" sx={{ mr: 2 }}>
              Status: <span style={{ fontWeight: 'bold' }}>{workflowStatus || 'Unknown'}</span>
            </Typography>
            {currentPhase && (
              <Typography variant="body2" sx={{ mr: 2 }}>
                Phase: <span style={{ fontWeight: 'bold' }}>{currentPhase.phase_id || 'N/A'}</span>
              </Typography>
            )}
          </>
        )}
        <Box display="flex" alignItems="center" mr={2}>
          <Typography variant="body2" sx={{ mr: 1 }}>Interactive:</Typography>
          <Switch
            checked={interactiveMode}
            onChange={onInteractiveModeToggle}
            color="primary"
            size="small"
            disabled={!interactiveMode} // Disable when not in interactive mode
          />
        </Box>
      </Box>
    </Box>
  );
};
