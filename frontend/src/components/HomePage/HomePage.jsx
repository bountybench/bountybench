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
        <Box
          display="flex"
          flexDirection="column"
          alignItems="center"
        >
          <Typography variant="h5" gutterBottom>
            Active Workflows
          </Typography>
          {activeWorkflows && activeWorkflows.length === 0 ? (
            <Typography>No active workflows</Typography>
          ) : (
            activeWorkflows.map((workflow) => {
              // Set button color based on the status
              let buttonColor;

              switch (workflow.status) {
                case 'error':
                  buttonColor = 'error';
                  break;
                case 'running':
                  buttonColor = 'success'; 
                  break;
                default:
                  buttonColor = 'secondary'; // Default color
              }

              return (
                <Button
                  key={workflow.id}
                  variant="outlined"
                  color={buttonColor} // Set the color dynamically based on the status
                  onClick={() => handleWorkflowClick(workflow.id)}
                  style={{ 
                    margin: '5px', 
                    width: '100%',   
                  }}
                >
                  {workflow.task?.task_dir} {workflow.task?.bounty_number} - {workflow.name} ({workflow.status})
                </Button>
              );
            })
          )}
        </Box>
       )}
    </Box>
  );
};

export default HomePage;