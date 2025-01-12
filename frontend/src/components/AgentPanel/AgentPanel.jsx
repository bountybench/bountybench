// AgentPanel.jsx
import React from 'react';
import { Box, Typography, List, ListItem, ListItemIcon, ListItemText } from '@mui/material';
import PersonIcon from '@mui/icons-material/Person';
import './AgentPanel.css';

export const AgentPanel = ({ workflow }) => {
  // This will be replaced with actual data from the backend later
  const activeAgents = [];

  return (
    <Box className="agents-container">
      <Typography variant="h6" gutterBottom>
        Agents
      </Typography>
      {activeAgents.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No active agents at the moment.
        </Typography>
      ) : (
        <List dense className="agents-list">
          {activeAgents.map((agent, index) => (
            <ListItem key={agent.id || index} className="agent-item">
              <ListItemIcon>
                <PersonIcon color="primary" />
              </ListItemIcon>
              <ListItemText 
                primary={agent.name}
                secondary={agent.type}
                className="agent-text"
              />
            </ListItem>
          ))}
        </List>
      )}
    </Box>
  );
};