import React, { useState, useEffect } from 'react';
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

export const WorkflowLauncher = ({ onWorkflowStart }) => {
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [formData, setFormData] = useState({
    workflow_name: '',
    task_repo_dir: '',
    bounty_number: '',
    interactive: true
  });

  // Fetch available workflows
  useEffect(() => {
    const fetchWorkflows = async () => {
      try {
        const response = await fetch('http://localhost:8000/workflow/list');
        const data = await response.json();
        setWorkflows(data.workflows);
        setLoading(false);
      } catch (err) {
        setError('Failed to fetch workflows. Make sure the backend server is running.');
        setLoading(false);
      }
    };

    fetchWorkflows();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    try {
      const response = await fetch('http://localhost:8000/workflow/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          workflow_name: formData.workflow_name,
          task_repo_dir: formData.task_repo_dir,
          bounty_number: formData.bounty_number,
          interactive: formData.interactive
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to start workflow');
      }

      const data = await response.json();
      if (data.error) {
        setError(data.error);
      } else {
        onWorkflowStart(data.workflow_id);
      }
    } catch (err) {
      setError(err.message || 'Failed to start workflow. Make sure the backend server is running.');
    }
  };

  const handleInputChange = (e) => {
    const { name, value, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'interactive' ? checked : value
    }));
  };

  if (loading) {
    return (
      <Box className="launcher-loading">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box className="launcher-container">
      <Typography variant="h5" gutterBottom>
        Start New Workflow
      </Typography>

      {error && (
        <Alert severity="error" className="launcher-alert">
          {error}
        </Alert>
      )}

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
          {workflows.map((workflow) => (
            <MenuItem key={workflow.name} value={workflow.name}>
              {workflow.name}
              <Typography variant="caption" color="textSecondary" className="workflow-description">
                {workflow.description}
              </Typography>
            </MenuItem>
          ))}
        </TextField>

        <TextField
          fullWidth
          label="Task Repository Directory"
          name="task_repo_dir"
          value={formData.task_repo_dir}
          onChange={handleInputChange}
          required
          margin="normal"
          placeholder="e.g., bountybench/astropy"
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

        <FormControlLabel
          control={
            <Switch
              checked={formData.interactive}
              onChange={handleInputChange}
              name="interactive"
              color="primary"
            />
          }
          label="Interactive Mode"
          className="launcher-switch"
        />

        <Button
          type="submit"
          variant="contained"
          color="primary"
          startIcon={<PlayArrowIcon />}
          className="launcher-button"
        >
          Start Workflow
        </Button>
      </form>
    </Box>
  );
};
