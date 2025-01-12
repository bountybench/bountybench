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
  Alert,
  Select,
  FormControl,
  InputLabel
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import './WorkflowLauncher.css';

export const WorkflowLauncher = ({ onWorkflowStart, interactiveMode, setInteractiveMode }) => {
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [formData, setFormData] = useState({
    workflow_type: '',
    task_dir: '',
    bounty_number: '',
    interactive: true
  });

  // Fetch available workflows
  useEffect(() => {
    const fetchWorkflows = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/workflow/list');
        if (!response.ok) {
          throw new Error('Failed to fetch workflows');
        }
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
      const response = await fetch('http://localhost:8000/api/workflow/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          workflow_type: formData.workflow_type,
          task_dir: formData.task_dir,
          bounty_number: formData.bounty_number,
          interactive: interactiveMode,
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
        onWorkflowStart(data.workflow_id, interactiveMode);
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
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <form onSubmit={handleSubmit}>
        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel>Workflow Type</InputLabel>
          <Select
            name="workflow_type"
            value={formData.workflow_type}
            onChange={handleInputChange}
            required
            label="Workflow Type"
          >
            {workflows.map((workflow) => (
              <MenuItem key={workflow.id} value={workflow.id}>
                {workflow.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <TextField
          fullWidth
          label="Task Directory"
          name="task_dir"
          value={formData.task_dir}
          onChange={handleInputChange}
          required
          sx={{ mb: 2 }}
        />

        <TextField
          fullWidth
          label="Bounty Number"
          name="bounty_number"
          value={formData.bounty_number}
          onChange={handleInputChange}
          required
          sx={{ mb: 2 }}
        />

        <FormControlLabel
          control={
            <Switch
              checked={interactiveMode}
              onChange={(e) => setInteractiveMode(e.target.checked)}
              name="interactive"
            />
          }
          label="Interactive Mode"
          sx={{ mb: 2 }}
        />

        <Button
          type="submit"
          variant="contained"
          color="primary"
          startIcon={<PlayArrowIcon />}
          fullWidth
        >
          Start Workflow
        </Button>
      </form>
    </Box>
  );
};
