// src/components/HomePage/HomePage.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { Box, Button, Typography, CircularProgress } from '@mui/material';
import './HomePage.css';

const HomePage = () => {
  const navigate = useNavigate();
  const [activeWorkflows, setActiveWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchActiveWorkflows();
  }, []);

  const fetchActiveWorkflows = async () => {
    try {
      const response = await fetch('http://localhost:8000/workflows/active');
      const data = await response.json();
      setActiveWorkflows(data.active_workflows);
    } catch (error) {
      console.error('Error fetching active workflows:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleNewWorkflowClick = () => {
    navigate('/create-workflow');
  };

  const handleWorkflowClick = (workflowId) => {
    navigate(`/workflow/${workflowId}`);
  };

  return (
    <Box className="homepage-container">
      <Typography variant="h4" gutterBottom>
        Workflows
      </Typography>
      
      <Button
        variant="contained"
        color="primary"
        onClick={handleNewWorkflowClick}
        style={{ marginBottom: '20px' }}
      >
        New Workflow
      </Button>

      {loading ? (
        <CircularProgress />
      ) : (
        <Box>
          <Typography variant="h5" gutterBottom>
            Active Workflows
          </Typography>
          {activeWorkflows.length === 0 ? (
            <Typography>No active workflows</Typography>
          ) : (
            activeWorkflows.map((workflow) => (
              <Button
                key={workflow.id}
                variant="outlined"
                onClick={() => handleWorkflowClick(workflow.id)}
                style={{ margin: '5px' }}
              >
                {workflow.name} - {workflow.bounty_number} ({workflow.status})
              </Button>
            ))
          )}
        </Box>
      )}
    </Box>
  );
};

export default HomePage;