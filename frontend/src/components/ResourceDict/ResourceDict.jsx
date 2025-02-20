import React, { useState } from 'react';
import { Box, Typography, Paper, List, ListItem, ListItemText, Divider, Collapse, IconButton } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import './ResourceDict.css';

const ResourceConfigItem = ({ label, value }) => {
  // Convert value to a displayable format
  let displayValue = value;

  if (typeof value === 'object' && value !== null) {
    displayValue = JSON.stringify(value, null, 2);
  } else if (typeof value === 'boolean') {
    displayValue = value ? 'true' : 'false';
  }

  return (
    <ListItem>
      <ListItemText
        primary={
          <Typography variant="subtitle2" color="textSecondary">
            {label}
          </Typography>
        }
        secondary={
          <Typography
            variant="body2"
            component="pre"
            style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}
          >
            {displayValue}
          </Typography>
        }
      />
    </ListItem>
  );
};

const ResourceItem = ({ resourceId, resource }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <Paper elevation={2} sx={{ mb: 2, p: 2 }}>
      <Box display="flex" alignItems="center" justifyContent="space-between">
        <Typography variant="subtitle1">{resourceId}</Typography>
        <IconButton size="small" onClick={() => setExpanded(!expanded)}>
          {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        </IconButton>
      </Box>
      <Typography variant="subtitle2" color="textSecondary" gutterBottom>
        Type: {resource.type}
      </Typography>
      
      {resource.config && (
        <Collapse in={expanded}>  
          <Divider sx={{ 
            my: 2,
            backgroundColor: 'white',
            }} 
          /> {/* Small horizontal line */}
          <List dense>
            {Object.entries(resource.config).map(([key, value]) => (
              <React.Fragment key={key}>
                <ResourceConfigItem label={key} value={value} />
                <Divider component="li" />
              </React.Fragment>
            ))}
          </List>
        </Collapse>
      )}
    </Paper>
  );
};

const ResourceDict = ({ resources }) => {
  return (
    <Box className="workflow-resources" sx={{ 
      overflowY: 'auto',
      pr: 2, // Add some padding to the right for the scrollbar
    }}>
      <h3>Workflow Resources</h3>
      {Object.entries(resources).map(([index, resource]) => (
        <ResourceItem key={index} resourceId={resource.id} resource={resource} />
      ))}
    </Box>
  );
};

export default ResourceDict;