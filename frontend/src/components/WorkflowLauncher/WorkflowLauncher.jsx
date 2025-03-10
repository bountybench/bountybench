import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router';
import { useServerAvailability } from '../../hooks/useServerAvailability';
import { toast } from "react-toastify";
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
} from '@mui/material';
import { formDataToYaml } from './utils/formDataToYaml';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import SaveIcon from '@mui/icons-material/Save';
import './WorkflowLauncher.css';
import { SaveConfigDialog } from './SaveConfigDialog';
import { TaskSelectionSection } from './TaskSelectionSection';
import { ModelSelectionSection } from './ModelSelectionSection';
import { API_BASE_URL } from '../../config';

const LauncherState = {
  CHECKING_SERVER: 'CHECKING_SERVER',
  SERVER_ERROR: 'SERVER_ERROR',
  LOADING_DATA: 'LOADING_DATA',
  READY: 'READY',
  CREATING_WORKFLOW: 'CREATING_WORKFLOW',
};

const DEFAULT_NON_HELM_MODEL = 'openai/o3-mini-2025-01-14';
const DEFAULT_HELM_MODEL = 'anthropic/claude-3-5-sonnet-20240620';

export const WorkflowLauncher = ({ onWorkflowStart }) => {
  const navigate = useNavigate();

  // Local toggles for interactive + mock model
  const [launcherInteractiveMode, setLauncherInteractiveMode] = useState(true);
  const [launcherUseMockModel, setLauncherUseMockModel] = useState(false);

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
  const [vulnerabilityTypes, setVulnerabilityTypes] = useState([]);
  const [configDefaults, setConfigDefaults] = useState({
    max_input_tokens: "",
    max_output_tokens: ""
  });
  
  const [openSaveDialog, setOpenSaveDialog] = useState(false);
  const [fileName, setFileName] = useState('workflow_config.yaml'); 
  const [saveStatus, setSaveStatus] = useState(null);

  // Form data for tasks, iterations, model info, etc.
  const [formData, setFormData] = useState({
    workflow_name: '',
    tasks: [{ task_dir: 'lunary', bounty_number: '0' }],
    vulnerability_type: '',
    interactive: true, // for YAML generation only, not used as the actual toggle
    iterations: 30,
    api_key_name: '',
    api_key_value: '',
    model: '',
    use_helm: false,
    max_input_tokens: '',
    max_output_tokens: '',
  });

  // Decide if we show vulnerability type & bounty fields
  const shouldShowVulnerabilityType = (workflowName) => {
    return workflowName.toLowerCase().includes('detect');
  };

  const shouldShowBounty = (workflowName) => {
    const lowercaseName = workflowName.toLowerCase();
    return lowercaseName.includes('detect') || lowercaseName.includes('exploit') || lowercaseName.includes('patch');
  };

  const [allModels, setAllModels] = useState({});
  const [selectedModels, setSelectedModels] = useState([]);
  const [topLevelSelection, setTopLevelSelection] = useState("Non-HELM");

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
      use_helm: isHelmModel,
    }));
  };

  const [apiKeys, setApiKeys] = useState({});
  const [showApiKey, setShowApiKey] = useState(false);
  const [apiStatus, setApiStatus] = useState({ type: "", message: "" });
  const [isCustomApiKey, setIsCustomApiKey] = useState(false);

  /** Data Fetching */
  const fetchWorkflows = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/workflow/list`);
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
      const response = await fetch(`${API_BASE_URL}/workflow/models`);
      const models = await response.json();
      setAllModels(models);
      
      // Set default model
      const isHelmModel = topLevelSelection === "HELM";
      const modelList = isHelmModel ? models.helmModels : models.nonHelmModels;
      const defaultModelName = isHelmModel ? DEFAULT_HELM_MODEL : DEFAULT_NON_HELM_MODEL;
      
      const defaultModel = setDefaultModel(modelList, defaultModelName);
      
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
  }, [topLevelSelection]);  

  const fetchConfigDefaults = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/workflow/config-defaults`);
      const data = await response.json();
      setConfigDefaults(data);
    } catch (err) {
      console.error('Failed to fetch config defaults:', err);
    }
  }, []);
  
  const fetchApiKeys = useCallback(async () => { 
    try {
      const response = await fetch(`${API_BASE_URL}/service/api-service/get`);
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

  const fetchVulnerabilityTypes = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/workflow/vulnerability-types`);
      const data = await response.json();
      setVulnerabilityTypes(data.vulnerability_types);
    } catch (error) {
      console.error('Failed to fetch vulnerability types:', error);
    }
  };

  /** End Data Fetching */

  const handleInputChange = (e) => {
    const { name, value, checked } = e.target;
    if (name.startsWith('tasks[')) {
      const [, index, field] = name.match(/tasks\[(\d+)\]\.(.+)/);
      setFormData((prev) => ({
        ...prev,
        tasks: prev.tasks.map((task, i) => 
          i === parseInt(index) ? { ...task, [field]: value } : task
        ),
      }));
    } else {
      setFormData((prev) => ({
        ...prev,
        [name]: name === 'interactive' ? checked : value,
        ...(name === 'api_key_name' ? { api_key_value: apiKeys[value] || '' } : {})
      }));
    }
  };

  const handleRevealToggle = () => {
    setShowApiKey((prev) => !prev);
  };

  const handleApiKeyChange = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/service/api-service/update`, {
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

  const handleSaveConfiguration = () => {
    setOpenSaveDialog(true);
  };

  const handleSaveDialogClose = () => {
    setOpenSaveDialog(false);
    setSaveStatus(false);
  };

  const handleFileNameChange = (event) => {
    setFileName(event.target.value);
  };

  const addTask = () => {
    setFormData((prev) => ({
      ...prev,
      tasks: [...prev.tasks, { task_dir: '', bounty_number: '' }],
    }));
  };

  const removeTask = (index) => {
    setFormData((prev) => ({
      ...prev,
      tasks: prev.tasks.filter((_, i) => i !== index),
    }));
  };

  const handleSaveConfirm = async () => {
    // We now pass the local launcherUseMockModel instead of a prop
    const yamlConfig = formDataToYaml(formData, launcherUseMockModel);
    const saveFileName = fileName.endsWith('.yaml') ? fileName : `${fileName}.yaml`;

    try {
      const response = await fetch(`${API_BASE_URL}/workflow/save-config`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          fileName: saveFileName,
          config: yamlConfig,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to save configuration');
      }

      const result = await response.json();
      setSaveStatus({ type: 'success', message: result.message });
    } catch (error) {
      setSaveStatus({ type: 'error', message: error.message });
    }
  };

  const startRun = async (e) => {
    e.preventDefault();
    setLauncherState({
      status: LauncherState.CREATING_WORKFLOW,
      message: "Creating workflow instance...",
      error: null
    });

    try {
      // Prepare tasks
      const tasks = formData.tasks.map(task => ({
        task_dir: task.task_dir.replace(/^bountybench\//, ''),
        bounty_number: task.bounty_number
      }));
  
      // Prepare models
      const models = [{
        name: formData.model,
        use_helm: formData.use_helm
      }];
  
      // Create the request payload
      const payload = {
        workflow_name: formData.workflow_name,
        tasks: tasks,
        models: models,
        vulnerability_type: formData.vulnerability_type,
        interactive: launcherInteractiveMode,
        phase_iterations: [parseInt(formData.iterations)],
        use_mock_model: launcherUseMockModel,
        trials_per_config: 1
      };

      console.log("Starting workflow with payload:", payload);
  
      // Send the request
      const response = await fetch(`${API_BASE_URL}/workflow/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
  
      if (!response.ok) {
        throw new Error('Failed to start parallel workflows');
      }
      
      const data = await response.json();
      if (data.error) {
        console.error("Failed to start parallel run:", data.error);
        return;
      }
      
      // Check if we got a single workflow or multiple
      if (data.workflow_id) {
        // Single workflow
        onWorkflowStart(data.workflow_id, data.model, launcherInteractiveMode, launcherUseMockModel);
        navigate(`/workflow/${data.workflow_id}`);
      } else if (data.workflows && data.workflows.length > 0) {
        // Multiple workflows
        const setupPromises = data.workflows.map(workflow => 
          setupWorkflowWebSocket(workflow.workflow_id)
        );
        await Promise.all(setupPromises);

        const firstWorkflow = data.workflows[0];

        console.log("==========DEBUG: data.workflows =>", data.workflows);

        data.workflows.forEach(workflow => {
          //setupWorkflowWebSocket(workflow.workflow_id);
          onWorkflowStart(workflow.workflow_id, workflow.model, launcherInteractiveMode, launcherUseMockModel);
        });
        
        //onWorkflowStart(firstWorkflow.workflow_id, firstWorkflow.model, launcherInteractiveMode, launcherUseMockModel);
        navigate(`/workflow/${firstWorkflow.workflow_id}`);
        
        const otherWorkflowsCount = data.workflows.length - 1;
        if (otherWorkflowsCount > 0) {
          toast.info(`Started ${data.workflows.length} workflows. You are viewing the first. ${otherWorkflowsCount} others are running in the background.`);
        }
      } else {
        console.error("Invalid response format", data);
      }
    } catch (error) {
      console.error("Error starting parallel run:", error);
      setLauncherState({
        status: LauncherState.SERVER_ERROR,
        message: "Failed to create workflows",
        error: error.message
      });
    }
  };
  
  // Helper function to set up WebSocket connections
  const setupWorkflowWebSocket = (workflowId) => {
    const ws = new WebSocket(`${API_BASE_URL.replace('http://', 'ws://')}/ws/${workflowId}`);
    ws.onopen = () => {
      console.log(`WebSocket connection established for workflow ${workflowId}`);
    };
    ws.onmessage = (event) => {
      console.log(`Received message from workflow ${workflowId}`, event.data);
    };
    ws.onerror = (error) => {
      console.error(`WebSocket error for workflow ${workflowId}:`, error);
    };
    ws.onclose = () => {
      console.log(`WebSocket connection closed for workflow ${workflowId}`);
    };
  };

  // 2. Load data once server is confirmed available
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
        error: serverError || "Server is not responding."
      });
    } else if (launcherState.status === LauncherState.LOADING_DATA) {
      const loadData = async () => {
        try {
          await Promise.all([
            fetchWorkflows(),
            fetchApiKeys(),
            fetchModels(),
            fetchVulnerabilityTypes(),
            fetchConfigDefaults()
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
            error: error.message || "An error occurred while loading data."
          });
        }
      };
      loadData();
    }
  }, [
    isChecking,
    isAvailable,
    serverError,
    launcherState.status,
    fetchApiKeys,
    fetchWorkflows,
    fetchModels,
    fetchConfigDefaults
  ]);
  
  // Show appropriate loading or error
  if (launcherState.status === LauncherState.CHECKING_SERVER ||
      launcherState.status === LauncherState.LOADING_DATA) {
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

  // Otherwise, render the form
  return (
    <Box className="launcher-container">
      <Typography variant="h5" gutterBottom>
        Start New Workflow
      </Typography>

      <form onSubmit={startRun} className="launcher-form">
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

        <TaskSelectionSection
          formData={formData}
          handleInputChange={handleInputChange}
          shouldShowBounty={shouldShowBounty}
          shouldShowVulnerabilityType={shouldShowVulnerabilityType}
          vulnerabilityTypes={vulnerabilityTypes}
          addTask={addTask}
          removeTask={removeTask}
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

        {/* Toggle for Mock Model */}
        <FormControlLabel
          control={
            <Switch
              checked={launcherUseMockModel}
              onChange={(e) => setLauncherUseMockModel(e.target.checked)}
              color="primary"
            />
          }
          label="Use Mock Model"
        />

        {/* If not using Mock Model, show model selection */}
        {!launcherUseMockModel && (
          <ModelSelectionSection
            formData={formData}
            handleInputChange={handleInputChange}
            topLevelSelection={topLevelSelection}
            handleTopLevelChange={handleTopLevelChange}
            selectedModels={selectedModels}
            apiKeys={apiKeys}
            isCustomApiKey={isCustomApiKey}
            setIsCustomApiKey={setIsCustomApiKey}
            showApiKey={showApiKey}
            handleRevealToggle={handleRevealToggle}
            handleApiKeyChange={handleApiKeyChange}
            apiStatus={apiStatus}
            configDefaults={configDefaults}
            setFormData={setFormData}
          />
        )}

        {/* Toggle for Interactive Mode */}
        <FormControlLabel
          control={
            <Switch
              checked={launcherInteractiveMode}
              onChange={(e) => setLauncherInteractiveMode(e.target.checked)}
              color="primary"
            />
          }
          label="Interactive Mode"
        />

        <Box display="flex" flexDirection="column" gap={2} mt={2}>
          <Button
            type="submit"
            variant="contained"
            color="primary"
            startIcon={<PlayArrowIcon />}
          >
            Run Workflow(s)
          </Button>

          <Button
            variant="outlined"
            color="secondary"
            onClick={handleSaveConfiguration}
            startIcon={<SaveIcon />}
          >
            Save Configuration
          </Button>
        </Box>
      </form>

      <SaveConfigDialog
        open={openSaveDialog}
        onClose={handleSaveDialogClose}
        fileName={fileName}
        onFileNameChange={handleFileNameChange}
        onSave={handleSaveConfirm}
        saveStatus={saveStatus}
      />
    </Box>
  );
};
