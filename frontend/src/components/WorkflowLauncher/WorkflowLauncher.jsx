// src/components/WorkflowLauncher/WorkflowLauncher.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router';
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

const LauncherState = {
  CHECKING_SERVER: 'CHECKING_SERVER',
  SERVER_ERROR: 'SERVER_ERROR',
  LOADING_DATA: 'LOADING_DATA',
  READY: 'READY',
  CREATING_WORKFLOW: 'CREATING_WORKFLOW',
};

const DEFAULT_NON_HELM_MODEL = 'openai/o3-mini-2025-01-14';
const DEFAULT_HELM_MODEL = 'anthropic/claude-3-5-sonnet-20240620';

const STORAGE_KEY = 'workflowLauncherSettings';
const DEFAULT_SETTINGS = {
  topLevelSelection: "Non-HELM",
  task_dir: '',
  bounty_number: '0',
  iterations: 10,
  model: '',
  workflow_name: '',
  interactive: true
};

export const WorkflowLauncher = ({ onWorkflowStart, interactiveMode, setInteractiveMode }) => {
  const navigate = useNavigate();
  
  const [launcherState, setLauncherState] = useState({
    status: LauncherState.CHECKING_SERVER,
    message: "Checking server availability...",
    error: null
  });

  const { isAvailable, isChecking, error: serverError } = useServerAvailability();
  
  useEffect(() => {
    if (isAvailable && !isChecking) {
      setLauncherState({
        status: LauncherState.LOADING_DATA,
        message: "Loading workflows...",
        error: null
      });
    }
  }, [isAvailable, isChecking]);

  const [workflows, setWorkflows] = useState([]);
  
  // Load all saved settings at once
  const loadSavedSettings = useCallback(() => {
    const savedSettings = localStorage.getItem(STORAGE_KEY);
    return savedSettings ? JSON.parse(savedSettings) : DEFAULT_SETTINGS;
  }, []);

  const [formData, setFormData] = useState(() => {
    const saved = loadSavedSettings();
    return {
      workflow_name: saved.workflow_name || '',
      task_dir: saved.task_dir || '',
      bounty_number: saved.bounty_number || '0',
      interactive: saved.interactive ?? true,
      iterations: saved.iterations || 10,
      api_key_name: '',
      api_key_value: '',
      model: saved.model || '',
      use_helm: saved.topLevelSelection === "HELM"
    };
  });

  const [allModels, setAllModels] = useState({});
  const [selectedModels, setSelectedModels] = useState([]);
  const [topLevelSelection, setTopLevelSelection] = useState(() => {
    const saved = loadSavedSettings();
    return saved.topLevelSelection || DEFAULT_SETTINGS.topLevelSelection;
  });

  const setDefaultModel = (modelList, defaultModelName) => {
    return modelList.find(m => m.name === defaultModelName) || modelList[0];
  };

  const handleTopLevelChange = (event) => {
    const { value } = event.target;
    setTopLevelSelection(value);
    
    const isHelmModel = value === "HELM";
    const modelList = isHelmModel ? allModels.helmModels : allModels.nonHelmModels;
    const defaultModelName = isHelmModel ? DEFAULT_HELM_MODEL : DEFAULT_NON_HELM_MODEL;
    
    const defaultModel = setDefaultModel(modelList, defaultModelName);
    
    setSelectedModels(modelList);
    setFormData(prev => ({
      ...prev,
      model: defaultModel ? defaultModel.name : '',
      use_helm: isHelmModel
    }));
  };

  const [apiKeys, setApiKeys] = useState({});
  const [showApiKey, setShowApiKey] = useState(false);
  const [apiStatus, setApiStatus] = useState({ type: "", message: "" });
  const [isCustomApiKey, setIsCustomApiKey] = useState(false);

  const fetchWorkflows = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/workflow/list');
      const data = await response.json();
      setWorkflows(data.workflows);
      
      // Set default workflow_name
      const defaultWorkflow = data.workflows.find(w => w.name === "Detect Patch Workflow") || data.workflows[0];
      setFormData(prev => ({
        ...prev,
        workflow_name: defaultWorkflow ? defaultWorkflow.name : ''
      }));
    } catch (err) {
      setLauncherState({
        status: LauncherState.SERVER_ERROR,
        message: "Failed to fetch workflows",
        error: err.message
      });
    } 
  }, []);
  
  const fetchModels = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/workflow/models');
      const models = await response.json();
      setAllModels(models);
      
      const isHelmModel = topLevelSelection === "HELM";
      const modelList = isHelmModel ? models.helmModels : models.nonHelmModels;
      
      // Try to use saved model first, fall back to defaults
      const savedSettings = loadSavedSettings();
      const savedModel = modelList.find(m => m.name === savedSettings.model);
      const defaultModelName = isHelmModel ? DEFAULT_HELM_MODEL : DEFAULT_NON_HELM_MODEL;
      const defaultModel = savedModel || setDefaultModel(modelList, defaultModelName);
      
      setSelectedModels(modelList);
      setFormData(prev => ({
        ...prev,
        model: defaultModel ? defaultModel.name : '',
        use_helm: isHelmModel
      }));
    } catch (err) {
      setLauncherState({
        status: LauncherState.SERVER_ERROR,
        message: "Failed to fetch models",
        error: err.message
      });
    }
  }, [topLevelSelection, loadSavedSettings]);  
  
  const fetchApiKeys = useCallback(async () => { 
    try {
      const response = await fetch('http://localhost:8000/service/api-service/get');
      const data = await response.json();
      setApiKeys(data);
      
      // Get the first API key name
      const firstApiKeyName = Object.keys(data)[0] || '';
      
      setFormData((prev) => ({
        ...prev,
        api_key_name: firstApiKeyName,
        api_key_value: data[firstApiKeyName] || '',
      }));
    } catch (err) {
      console.error('Failed to fetch API keys:', err);
    }
  }, []);


  const handleSubmit = async (e) => {
    e.preventDefault();
    setLauncherState({
      status: LauncherState.CREATING_WORKFLOW,
      message: "Creating workflow instance...",
      error: null
    });
  
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
          model: formData.model,
          use_helm: formData.use_helm
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to start workflow');
      }
  
      const data = await response.json();
  
      if (data.error) {
        throw new Error(data.error);
      } else {
        await onWorkflowStart(data.workflow_id, data.model, interactiveMode);
        navigate(`/workflow/${data.workflow_id}`);
      }
    } catch (err) {
      setLauncherState({
        status: LauncherState.SERVER_ERROR,
        message: "Failed to create workflow",
        error: err.message
      });
    }
  };

  const handleInputChange = (e) => {
    const { name, value, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'interactive' ? checked : value,
      ...(name === 'api_key_name' ? { api_key_value: apiKeys[value] || '' } : {})
    }));
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

  // 2. Fetch workflows only once server is confirmed available
  useEffect(() => {
    if (isChecking) {
      setLauncherState({
        status: LauncherState.CHECKING_SERVER,
        message: "Checking server availability...",
        error: null
      });
    } else if (!isAvailable) {
      setLauncherState({
        status: LauncherState.SERVER_ERROR,
        message: "Cannot reach server",
        error: serverError || "Server is not responding. Please check if the backend is running and refresh the page."
      });
    } else if (launcherState.status === LauncherState.LOADING_DATA) {
      const loadData = async () => {
        try {
          await Promise.all([
            fetchWorkflows(),
            fetchApiKeys(),
            fetchModels()
          ]);
          setLauncherState({
            status: LauncherState.READY,
            message: "",
            error: null
          });
        } catch (error) {
          setLauncherState({
            status: LauncherState.SERVER_ERROR,
            message: "Failed to load necessary data",
            error: error.message || "An error occurred while loading data. Please try again."
          });
        }
      };
  
      loadData();
    }
  }, [isChecking, isAvailable, serverError, launcherState.status, fetchApiKeys, fetchWorkflows, fetchModels]);
  
  // Save all settings in one effect
  useEffect(() => {
    const settingsToSave = {
      topLevelSelection,
      task_dir: formData.task_dir,
      bounty_number: formData.bounty_number,
      iterations: formData.iterations,
      model: formData.model,
      workflow_name: formData.workflow_name,
      interactive: interactiveMode
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settingsToSave));
  }, [
    topLevelSelection, 
    formData.task_dir, 
    formData.bounty_number, 
    formData.iterations,
    formData.model,
    formData.workflow_name,
    interactiveMode
  ]);

  if (launcherState.status === LauncherState.CHECKING_SERVER || launcherState.status === LauncherState.LOADING_DATA) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="100%">
        <Box className="launcher-loading" display="flex" flexDirection="column" alignItems="center">
          <CircularProgress />
          <Typography>{launcherState.message}</Typography>
        </Box>
      </Box>
    );
  }

  if (launcherState.status === LauncherState.SERVER_ERROR) {
    return (
      <Alert severity="error" className="launcher-alert">
        {launcherState.error}
      </Alert>
    );
  }

  if (launcherState.status === LauncherState.CREATING_WORKFLOW) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="100%">
        <Box className="launcher-loading" display="flex" flexDirection="column" alignItems="center">
          <CircularProgress />
          <Typography>{launcherState.message}</Typography>
        </Box>
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
        {(workflows?.length > 0) ? (
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

        <TextField
          select
          fullWidth
          label="Model Type"
          name="type"
          value={topLevelSelection}
          onChange={handleTopLevelChange}
          margin="normal"
        >
          <MenuItem value="HELM">HELM</MenuItem>
          <MenuItem value="Non-HELM">Non-HELM</MenuItem>
        </TextField>

        {/* Conditionally render the second dropdown based on top-level selection */}
        {selectedModels && (
          <TextField
            select
            fullWidth
            label="Model Name"
            name="model"
            value={formData.model}
            onChange={handleInputChange}
            margin="normal"
          >
            {selectedModels.map((model) => (
            <MenuItem key={model.name} value={model.name}>
              <Box display="flex" flexDirection="column">
                <Typography>{model.name}</Typography>
              </Box>
            </MenuItem>
          ))}
          </TextField>
          )}

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