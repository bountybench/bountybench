// src/components/HomePage/HomePage.jsx

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Button, Typography } from '@mui/material';
import './HomePage.css';

const HomePage = () => {
  const navigate = useNavigate();

  const handleNewWorkflowClick = () => {
    navigate('/create-workflow');
  };

  return (
    <Box className="homepage-container">
      <Button
        variant="contained"
        color="primary"
        onClick={handleNewWorkflowClick}
      >
        New Workflow
      </Button>
    </Box>
  );
};

export default HomePage;