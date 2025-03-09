import React, { useState } from 'react';
import { Box, Typography, Paper, List, ListItem, ListItemText, Divider, Collapse, IconButton } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ResourceDict from './ResourceDict';
import './WorkflowMetadataPanel.css';

const WorkflowMetadataPanel = ({ resources }) => {
  return (
    <ResourceDict resources={resources} />
  );
};

export default WorkflowMetadataPanel;