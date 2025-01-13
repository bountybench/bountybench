// PhasePanel.jsx
import React from 'react';
import { Box, Typography, List, ListItem, ListItemIcon, ListItemText } from '@mui/material';
import PersonIcon from '@mui/icons-material/Person';
import './PhasePanel.css';

export const PhasePanel = ({ workflow }) => {
  // This will be replaced with actual data from the backend later
  const activePhases = [];

  return (
    <Box className="phases-container">
      <Typography variant="h6" gutterBottom>
        Phases
      </Typography>
      {activePhases.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No active phases at the moment.
        </Typography>
      ) : (
        <List dense className="phases-list">
          {activePhases.map((phase, index) => (
            <ListItem key={phase.id || index} className="phase-item">
              <ListItemIcon>
                <PersonIcon color="primary" />
              </ListItemIcon>
              <ListItemText 
                primary={phase.name}
                secondary={phase.type}
                className="phase-text"
              />
            </ListItem>
          ))}
        </List>
      )}
    </Box>
  );
};