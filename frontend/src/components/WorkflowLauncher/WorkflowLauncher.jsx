// src/components/WorkflowLauncher/WorkflowLauncher.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useServerAvailability } from '../../hooks/useServerAvailability';
import {
  Box,
  Button,
  TextField,
  FormControlLabel,
  Switch,
  Typography,
  MenuItem,
  CircularProgress,
  Alert
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import './WorkflowLauncher.css';

export const WorkflowLauncher = ({ onWorkflowStart, interactiveMode, setInteractiveMode }) => {
  // 1. Use the hook to poll for server availability
  const { isServerAvailable, isChecking } = useServerAvailability(() => {
    console.log('Server is available!');
  });

  const navigate = useNavigate();

  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);

  const [formData, setFormData] = useState({
    workflow_name: '',
    task_dir: '',
    bounty_number: '0',
    interactive: true,
    iterations: 10
  });

  // 2. Fetch workflows only once server is confirmed available
  useEffect(() => {
    if (!isChecking && isServerAvailable) {
      fetchWorkflows();
    }
  }, [isChecking, isServerAvailable]);

  const fetchWorkflows = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/workflow/list');
      const data = await response.json();
      setWorkflows(data.workflows || []);
    } catch (err) {
      console.error('Failed to fetch workflows. Make sure the backend server is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const response = await fetch('http://localhost:8000/workflow/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow_name: formData.workflow_name,
          task_dir: `bountybench/${formData.task_dir.replace(/^bountybench\//, '')}`,
          bounty_number: formData.bounty_number,
          interactive: interactiveMode,
          iterations: formData.iterations
        }),
      });

      if (!response) {
        throw new Error('Failed to get response from server');
      }

      if (!response.ok) {
        let errorData;
        try {
          errorData = await response.json();
        } catch {
          throw new Error('Failed to parse error response');
        }
        throw new Error(errorData.error || 'Failed to start workflow');
      }

      let data;
      try {
        data = await response.json();
      } catch {
        throw new Error('Failed to parse response data');
      }

      if (data.error) {
        console.error(data.error);
      } else {
        onWorkflowStart(data.workflow_id, interactiveMode);
        navigate(`/workflow/${data.workflow_id}`); // Navigate to workflow page after start
      }
    } catch (err) {
      console.error(err.message || 'Failed to start workflow. Make sure the backend server is running.');
    }
  };

  const handleInputChange = (e) => {
    const { name, value, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'interactive' ? checked : value
    }));
  };

  // 3. Render different states

  // While still checking server
  if (isChecking) {
    return (
      <Box className="launcher-loading">
        <CircularProgress />
        <Typography>Checking server availability...</Typography>
      </Box>
    );
  }

  // Server not available (will keep polling in background)
  if (!isServerAvailable) {
    return (
      <Alert severity="error" className="launcher-alert">
        Cannot reach server. Retrying...
      </Alert>
    );
  }

  // Server available but workflows still loading
  if (loading) {
    return (
      <Box className="launcher-loading">
        <CircularProgress />
        <Typography>Loading workflows...</Typography>
      </Box>
    );
  }

  // All good: show the form
  return (
    <Box className="launcher-container">
      <Typography variant="h5" gutterBottom>
        Start New Workflow
      </Typography>

      <form onSubmit={handleSubmit} className="launcher-form">
        <TextField
          select
          fullWidth
          label="Workflow Type"
          name="workflow_name"
          value={formData.workflow_name}
          onChange={handleInputChange}
          required
          margin="normal"
        >
        {(workflows.length > 0) ? (
          workflows.map((workflow) => (
              <MenuItem key={workflow.name} value={workflow.name}>
                <Box display="flex" flexDirection="column">
                  <Typography>{workflow.name}</Typography>
                  <Typography variant="caption" color="textSecondary">
                    {workflow.description}
                  </Typography>
                </Box>
              </MenuItem>
            ))
          ) : (
            <MenuItem value="">
              <Typography>No workflows available</Typography>
            </MenuItem>
          )}
        </TextField>

        <TextField
          fullWidth
          label="Task Repository Directory"
          name="task_dir"
          value={formData.task_dir}
          onChange={handleInputChange}
          required
          margin="normal"
          placeholder="e.g., astropy"
        />

        <TextField
          fullWidth
          label="Bounty Number"
          name="bounty_number"
          value={formData.bounty_number}
          onChange={handleInputChange}
          required
          margin="normal"
          placeholder="e.g., 0"
        />

        <TextField
          fullWidth
          label="Iterations (per phase)"
          name="iterations"
          value={formData.iterations}
          onChange={handleInputChange}
          required
          margin="normal"
          placeholder="e.g., 10"
        />

        <FormControlLabel
          control={
            <Switch
              checked={interactiveMode}
              onChange={(e) => setInteractiveMode(e.target.checked)}
              name="interactive"
              color="primary"
            />
          }
          label="Interactive Mode"
        />

        <Button
          type="submit"
          variant="contained"
          color="primary"
          startIcon={<PlayArrowIcon />}
        >
          Start Workflow
        </Button>
      </form>
    </Box>
  );
};