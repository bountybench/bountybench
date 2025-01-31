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
  Alert,
  Grid,
  InputAdornment,
  IconButton,
  Divider,
} from '@mui/material';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import ListIcon from '@mui/icons-material/List';
import './WorkflowLauncher.css';

export const WorkflowLauncher = ({ onWorkflowStart, interactiveMode, setInteractiveMode }) => {
  // 1. Use the hook to poll for server availability
  const { isServerAvailable, isChecking } = useServerAvailability(() => {
    console.log('Server is available!');
  });

  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);

  const [formData, setFormData] = useState({
    workflow_name: '',
    task_dir: '',
    bounty_number: '0',
    interactive: true,
    iterations: 10,
    api_key_name: 'HELM_API_KEY',
    api_key_value: '',
  });

  const [apiKeys, setApiKeys] = useState({"HELM_API_KEY": ""});
  const [showApiKey, setShowApiKey] = useState(false);
  const [apiStatus, setApiStatus] = useState({ type: "", message: "" });
  const [isCustomApiKey, setIsCustomApiKey] = useState(false);

  // 2. Fetch workflows only once server is confirmed available
  useEffect(() => {
    if (!isChecking && isServerAvailable) {
      fetchWorkflows();
      fetchApiKeys();
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

  const fetchApiKeys = async () => {
    try {
      const response = await fetch('http://localhost:8000/service/api-service/get');
      const data = await response.json();
      console.log(data);
      setApiKeys(data);
      setFormData((prev) => ({
        ...prev,
        api_key_value: data[formData.api_key_name] || '',
      }));
    } catch (err) {
      console.error('Failed to fetch API keys:', err);
    }
  }

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


    if (name === 'api_key_name') {
      setFormData((prev) => ({
        ...prev,
        api_key_value: apiKeys[value] || '',
      }));
    }
  };

  const handleRevealToggle = () => {
    setShowApiKey((prev) => !prev);
  };

  const handleApiKeyChange = async () => {
    try {
      const response = await fetch('http://localhost:8000/service/api-service/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key_name: formData.api_key_name || "",
          api_key_value: formData.api_key_value || "",
        }),
      });

      const responseData = await response.json();

      if (!response.ok) {
        setApiStatus({ 
          type: "error", 
          message: `Failed to update API key. Please double-check your entry. Here's the full log:\n${responseData.detail || "Failed to update API key"}` 
        });
        
      } else {
        let successMessage = `${formData.api_key_name} updated successfully!`;

        if (responseData.warning) {
          setApiStatus({
            type: "warning",
            message: `${successMessage}\n\n Warning: ${responseData.warning}`,
          });
        } else {
          setApiStatus({ type: "success", message: successMessage });
          setTimeout(() => setApiStatus({ type: "", message: "" }), 3000);
        }
      }

      console.log(`${formData.api_key_name} updated successfully.`);
      fetchApiKeys();
    } catch (err) {
      console.log(err.message);
    }
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

        <Grid container spacing={2} alignItems="center">
          <Grid item xs={5}>
            <TextField
              select={!isCustomApiKey} // Turns into input when "Enter new key" is selected
              fullWidth
              label="API Key Name"
              name="api_key_name"
              value={formData.api_key_name || ""}
              onChange={handleInputChange}
              required
              margin="normal"
              InputProps={{
                endAdornment: (
                  <IconButton onClick={() => {
                    if (isCustomApiKey) {
                      setIsCustomApiKey(!isCustomApiKey);

                      handleInputChange({ // Reset to default
                        target: {
                          name: "api_key_name",
                          value: "HELM_API_KEY",
                        },
                      });
                    }
                  }}>
                    {isCustomApiKey ? <ListIcon /> : null}
                  </IconButton>
                )
              }}
            >
              {Object.keys(apiKeys).map((key) => (
                <MenuItem key={key} value={key}>
                  {key}
                </MenuItem>
              ))}
              <Divider />
              <MenuItem onClick={() => {
                setIsCustomApiKey(true);
                setFormData((prev) => ({
                  ...prev,
                  api_key_name: "my_custom_key",
                }));
                
              }}>
                Enter a New API Key:
              </MenuItem>
            </TextField>
          </Grid>

          <Grid item xs={5.5}>
            <TextField
              fullWidth
              type={showApiKey ? 'text' : 'password'}
              label="API Key Value"
              name="api_key_value"
              value={formData.api_key_value}
              onChange={handleInputChange}
              required
              margin="normal"
              placeholder="Enter API key"
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={handleRevealToggle} size="large">
                      {showApiKey ? <Visibility /> : <VisibilityOff />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
          </Grid>

          <Grid item xs={1}>
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Button
                variant="contained"
                color="primary"
                onClick={handleApiKeyChange}
                size="small"
              >
                Update
              </Button>
            </Box>
          </Grid>

          <Grid item xs={10}>
            {apiStatus.message && (
              <Alert severity={apiStatus.type} className="launcher-alert" sx={{ whiteSpace: "pre-line" }}>
                {apiStatus.message}
              </Alert>
            )}
          </Grid>


        </Grid>

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