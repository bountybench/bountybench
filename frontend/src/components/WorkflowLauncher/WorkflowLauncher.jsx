import React, { useState, useEffect } from 'react';
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

  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [formData, setFormData] = useState({
    workflow_name: '',
    task_dir: '',
    bounty_number: '0',
    interactive: true,
    iterations: 10,
    model: '',
  });
  const [allModels, setAllModels] = useState([]);
  const [topLevelSelection, setTopLevelSelection] = useState("");

  const handleTopLevelChange = (event) => {
    const { value } = event.target;
    setTopLevelSelection(value);
    // Set the model field based on top-level selection
    if (value === "Non-HELM") {
      handleInputChange({ target: { name: 'model', value: 'openai/o3-mini-2024-12-17' } }); // Set to default model for Non-HELM
    } else {
      handleInputChange({ target: { name: 'model', value: '' } }); // Reset model field for HELM
    }
  };

  // 2. Fetch workflows only once server is confirmed available
  useEffect(() => {
    if (!isChecking && isServerAvailable) {
      fetchWorkflows();
    }
  }, [isChecking, isServerAvailable]);

  const fetchWorkflows = async () => {
    setError(null);
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/workflow/list');
      const data = await response.json();
      setWorkflows(data.workflows);
    } catch (err) {
      setError('Failed to fetch workflows. Make sure the backend server is running.');
    } finally {
      setLoading(false);
    }
  };

  // Fetch available models
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await fetch('http://localhost:8000/workflow/helmmodels');
        const all_models = await response.json();
        setAllModels(all_models);
        setLoading(false);
      } catch (err) {
        setError('Failed to fetch models. Make sure the backend server is running.');
        setLoading(false);
      }
    };

    fetchModels();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    try {
      const response = await fetch('http://localhost:8000/workflow/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow_name: formData.workflow_name,
          task_dir: `bountybench/${formData.task_dir.replace(/^bountybench\//, '')}`,
          bounty_number: formData.bounty_number,
          interactive: interactiveMode,
          iterations: formData.iterations,
          model: formData.model
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
              <Box display="flex" flexDirection="column">
                <Typography>{workflow.name}</Typography>
                <Typography variant="caption" color="textSecondary">
                  {workflow.description}
                </Typography>
              </Box>
            </MenuItem>
          ))}
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

        <TextField
          select
          fullWidth
          label="Model Type"
          name="type"
          value={topLevelSelection}
          onChange={handleTopLevelChange}
          required
          margin="normal"
        >
          <MenuItem value="HELM">HELM</MenuItem>
          <MenuItem value="Non-HELM">Non-HELM</MenuItem>
        </TextField>

        {/* Conditionally render the second dropdown based on top-level selection */}
        {topLevelSelection === "HELM" && (
          <TextField
            select
            fullWidth
            label="Model Name"
            name="model"
            value={formData.model}
            onChange={handleInputChange}
            required
            margin="normal"
          >
            {Object.entries(allModels).map(([k, v]) => (
              <MenuItem key={k} value={k}>
                <Box display="flex" flexDirection="column">
                  <Typography>{k}</Typography>
                  <Typography variant="caption" color="textSecondary" className="workflow-description">
                    {v}
                  </Typography>
                </Box>
              </MenuItem>
            ))}
          </TextField>
          )}

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
