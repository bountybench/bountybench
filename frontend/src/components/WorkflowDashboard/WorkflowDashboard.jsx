import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router';
import { Box, CircularProgress, Alert, Typography, IconButton, FormControl, Select, MenuItem, Switch } from '@mui/material';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import AgentInteractions from '../AgentInteractions/AgentInteractions';
import ResourceDict from '../ResourceDict/ResourceDict';
import { useWorkflowWebSocket } from '../../hooks/useWorkflowWebSocket';
import './WorkflowDashboard.css';

import { API_BASE_URL } from '../../config';

const WorkflowState = {
  LOADING: 'LOADING',
  CONNECTING: 'CONNECTING',
  STARTING: 'STARTING',
  RUNNING: 'RUNNING',
  COMPLETED: 'COMPLETED',
  ERROR: 'ERROR',
  STOPPED: 'STOPPED',
  RESTARTING: 'RESTARTING'
};

export const WorkflowDashboard = ({ interactiveMode, onWorkflowStateUpdate, showInvalidWorkflowToast, useMockModel}) => {
  const { workflowId } = useParams();
  const [isNextDisabled, setIsNextDisabled] = useState(false);
  const [hasCheckedValidity, setHasCheckedValidity] = useState(false);
  const [preservedMessages, setPreservedMessages] = useState([]);
  const navigate = useNavigate();
  
  const [resources, setResources] = useState([]);
  const [isResourcePanelOpen, setIsResourcePanelOpen] = useState(false);
  const [restart, setRestart] = useState(0);

  // Dashboard Header State
  const [modelMapping, setModelMapping] = useState([]);
  const [selectedModelType, setSelectedModelType] = useState('');
  const [selectedModelName, setSelectedModelName] = useState('');

  // Initialize local state with props
  const [localInteractiveMode, setInteractiveMode] = useState(interactiveMode);
  const [localMockModel, setUseMockModel] = useState(useMockModel); 

  const [workflowState, setWorkflowState] = useState({
    status: WorkflowState.LOADING,
    message: "Loading workflow instance...",
    error: null
  });
   
  // Fetch active workflows to check if given workflowId exists
  useEffect(() => {
    const checkIfWorkflowExists = async () => {
      const response = await fetch(`${API_BASE_URL}/workflow/active`);
      const data = await response.json();

      if (!data.active_workflows.some(workflow => workflow.id === workflowId)) {
        showInvalidWorkflowToast();
        navigate(`/`); 
      }
    };

    if (!hasCheckedValidity) {
      checkIfWorkflowExists();
      setHasCheckedValidity(true);
    }
  }, [workflowId, navigate, showInvalidWorkflowToast, hasCheckedValidity]);

  // Update local state when props change
  useEffect(() => {
    setInteractiveMode(interactiveMode);
  }, [interactiveMode]);

  // Update local mock model state when prop changes
  useEffect(() => {
    console.log(`===========Workflow ${workflowId} - useMockModel updated to:===========`, useMockModel);
    setUseMockModel(useMockModel);
  }, [useMockModel]);

  const {
    isConnected,
    workflowStatus,
    currentPhase,
    phaseMessages,
    error,
  } = useWorkflowWebSocket(workflowId, restart);
  
  console.log('WebSocket state:', { 
    isConnected, 
    workflowStatus, 
    currentPhase,
    error,
    phaseMessagesCount: phaseMessages?.length
  });

  // Fetch available models for the header
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/workflow/allmodels`);
        const models = await response.json();
        setModelMapping(models.allModels);
      } catch (err) {
        console.log('Failed to fetch models. Make sure the backend server is running.');
      }
    };
    fetchModels();
  }, []);
  
  // Effect to set defaults based on WebSocket data
  useEffect(() => {
    if (currentPhase && currentPhase.model) {
      const model = currentPhase.model.split('/');
      if (model.length === 2) {
        setSelectedModelType(model[0]);
        setSelectedModelName(model[1]);
      }
    }
  }, [currentPhase]);

  // Model change handler
  const handleModelChange = async (name) => {
    setSelectedModelName(name);
    const new_model_name = `${selectedModelType}/${name}`;
    
    try {
      const url = `${API_BASE_URL}/workflow/${workflowId}/model-change`;
      const requestBody = { 
        new_model_name: new_model_name,
        use_mock_model: localMockModel 
      };
  
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });
  
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
  
      console.log('Model updated successfully to:', new_model_name);
    } catch (error) {
      console.error('Error updating model:', error);
    }
  };

  // Handle interactive mode toggle
  const handleInteractiveModeToggle = async () => {
    // Store the new intended state
    const newInteractiveMode = !localInteractiveMode;
    
    if (workflowId) {
      try {
        // Update UI state immediately for responsive feedback
        setInteractiveMode(newInteractiveMode);
        
        const response = await fetch(`${API_BASE_URL}/workflow/${workflowId}/interactive`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ interactive: newInteractiveMode }),
        });

        if (!response.ok) {
          throw new Error('Failed to update interactive mode');
        }

        console.log('Backend updated with new interactive mode:', newInteractiveMode);
        
        // Notify the parent App component about the change
        onWorkflowStateUpdate(workflowStatus, currentPhase);
      } catch (error) {
        console.error('Error updating interactive mode:', error);
        // Revert UI state on error
        setInteractiveMode(!newInteractiveMode);
      }
    }
  };

  // Handle mock model toggle
  const handleMockModelToggle = async () => {
    const newMockState = !localMockModel;
    
    if (workflowId) {
      try {
        // Update UI state immediately for responsive feedback
        setUseMockModel(newMockState);
        
        const response = await fetch(`${API_BASE_URL}/workflow/${workflowId}/mock-model`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ use_mock_model: newMockState }),
        });
  
        if (!response.ok) {
          throw new Error('Failed to update mock model setting');
        }
  
        console.log('Mock model updated successfully:', newMockState);
        onWorkflowStateUpdate(workflowStatus, currentPhase);

      } catch (error) {
        console.error('Error updating mock model:', error);
        setUseMockModel(!newMockState); // Revert on error
      }
    }
  };

  const getTailMessageId = async () => {
    if (phaseMessages?.length > 0 && phaseMessages[phaseMessages.length - 1].current_children?.length > 0) {
      const lastMessage = phaseMessages[phaseMessages.length - 1].current_children[phaseMessages[phaseMessages.length - 1].current_children.length - 1];
      return lastMessage.current_id;
    }
    return null;
  };
  
  useEffect(() => {
    if (error) {
      setWorkflowState({
        status: WorkflowState.ERROR,
        message: "An error occurred",
        error: error
      });
    } else if (!isConnected) {
      setWorkflowState({
        status: WorkflowState.CONNECTING,
        message: "Connecting to workflow...",
        error: null
      });
    } else if (workflowStatus === 'starting') {
      setWorkflowState({
        status: WorkflowState.STARTING,
        message: "Starting workflow, setting up first phase...",
        error: null
      });
    } else if (workflowStatus === 'restarting') {
      setWorkflowState({
        status: WorkflowState.RESTARTING,
        message: "Workflow restarting",
        error: null
      });
    } else if (workflowStatus === 'completed') {
      setWorkflowState({
        status: WorkflowState.COMPLETED,
        message: "Workflow completed",
        error: null
      });
      setPreservedMessages(phaseMessages);
    } else if (workflowStatus === 'stopped') {
      setWorkflowState({
        status: WorkflowState.STOPPED,
        message: "Workflow stopped",
        error: null
      });
    } else if (workflowStatus) {
      setWorkflowState({
        status: WorkflowState.RUNNING,
        message: `Workflow ${workflowStatus}`,
        error: null
      });
    }

    console.log(`Workflow state updated to ${workflowStatus}`)
    onWorkflowStateUpdate(workflowStatus, currentPhase);
  }, [isConnected, workflowStatus, currentPhase, phaseMessages, error, onWorkflowStateUpdate]);

  const handleRestart = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/workflow/restart/${workflowId}`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      console.log('Workflow restarted successfully');
    } catch (error) {
      console.error('Error restarting workflow:', error);
    } finally {
      setRestart((prev) => prev + 1);
    }
  };

  const fetchResources = useCallback(async () => {
    if (!workflowId) {
      console.log('Skipping resource fetch - no workflow ID available');
      return;
    }

    if (workflowId) {
      try {
        const response = await fetch(`${API_BASE_URL}/workflow/${workflowId}/resources`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log("resources: ", data)
        setResources(data.resources);
      } catch (error) {
        console.error('Error fetching resources:', error);
      }
    }
  }, [workflowId]);

  useEffect(() => {
    fetchResources();
  }, [phaseMessages, useMockModel, fetchResources]);

  const toggleResourcePanel = () => {
    setIsResourcePanelOpen(!isResourcePanelOpen);
  };

  const triggerNextIteration = async () => {
    if (workflowStatus === "stopped") {
      console.error("Cannot trigger next iteration: Workflow is stopped.");
      return;
    }
    if (workflowId) {
      setIsNextDisabled(true);
      try {
        const currentMessageId = await getTailMessageId();
        console.log(`Tail message id is ${currentMessageId}`)
        const response = await fetch(`${API_BASE_URL}/workflow/${workflowId}/run-message`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ message_id: currentMessageId }),
        });
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log('Next iteration triggered successfully', data);
      } catch (error) {
        console.error('Error triggering next iteration:', error);
      } finally {
        setIsNextDisabled(false);
      }
    } else {
      console.error('Workflow ID is not available');
    }
  };

  const handleUpdateMessageInput = async (messageId, newInputData) => {
    const url = `${API_BASE_URL}/workflow/${workflowId}/edit-message`;
    const requestBody = { message_id: messageId, new_input_data: newInputData };
    
    console.log('Sending request to:', url);
    console.log('Request body:', JSON.stringify(requestBody));
  
    setIsNextDisabled(true);
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });
  
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response body:', errorText);
        throw new Error(`HTTP error! status: ${response.status}`);
      }
  
      const data = await response.json();
      console.log('Action updated successfully', data);
    } catch (error) {
      console.error('Error updating action:', error);
    } finally {
      setIsNextDisabled(false);
    }
  };

  const handleRunMessage = async (messageId) => {
    if (workflowId) {
      setIsNextDisabled(true);
      try {
        const response = await fetch(`${API_BASE_URL}/workflow/${workflowId}/run-message`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ message_id: messageId }),
        });
        const data = await response.json();
        if (data.error) {
          console.error('Error running action:', data.error);
        } else {
          console.log('Action run successfully', data);
        }
      } catch (error) {
        console.error('Error running action:', error);
      } finally {
        setIsNextDisabled(false);
      }
    } else {
      console.error('Workflow ID is not available');
    }
  };

  const handleStopWorkflow = async () => {
    if (workflowId) {
      try {
        const response = await fetch(`${API_BASE_URL}/workflow/${workflowId}/stop`, {
          method: 'POST',
        });
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        console.log('Workflow stopped successfully');
      } catch (error) {
        console.error('Error stopping workflow:', error);
      }
    } else {
      console.error('Workflow ID is not available');
    }
  };

  const handleToggleVersion = useCallback(async (messageId, direction) => {
    try {
      const response = await fetch(`${API_BASE_URL}/workflow/${workflowId}/toggle-version`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message_id: messageId, direction }),
      });

      if (!response.ok) {
        throw new Error('Failed to toggle version');
      }

      const result = await response.json();
      console.log(`Toggle version: ${result}`);
      // Updating messages should be triggered by call
    } catch (error) {
      console.error('Error toggling version:', error);
    }
  }, [workflowId]);

  // Extracting model types and names
  const allModelTypes = [...new Set(modelMapping.map(model => model.name.split('/')[0]))];
  const allModelNames = selectedModelType ? modelMapping
    .filter(model => model.name.startsWith(selectedModelType))
    .map(model => model.name.split('/')[1])
    : [];

  if (workflowState.status === WorkflowState.ERROR) {
    return (
      <Box p={2}>
        <Alert severity="error">{workflowState.error || workflowState.message}</Alert>
      </Box>
    );
  }

  if (workflowState.status === WorkflowState.LOADING || 
      workflowState.status === WorkflowState.CONNECTING ||
      workflowState.status === WorkflowState.STARTING ||
      workflowState.status === WorkflowState.RESTARTING) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="100%">
        <Box className="launcher-loading" display="flex" flexDirection="column" alignItems="center">
          <CircularProgress />
          <Typography>{workflowState.message}</Typography>
        </Box>
      </Box>
    );
  }

  const displayMessages = workflowState.status === WorkflowState.COMPLETED ? preservedMessages : phaseMessages;

  return (
    <Box height="100%" overflow="hidden" display="flex" flexDirection="column">
      {/* Workflow-specific header */}
      <Box 
        display="flex" 
        justifyContent="space-between" 
        alignItems="center" 
        p={1} 
        bgcolor="#266798"
        borderBottom="1px solid #444"
      >
        <Typography 
          variant="h6" 
          component="div" 
          sx={{ flexGrow: 0, cursor: 'pointer' }} 
          onClick={() => navigate('/')} 
        >
          Workflow Agent
        </Typography>

        <Box display="flex" alignItems="center" flexGrow={1} justifyContent="flex-end">
          {/* Only show model selection when not using mock model */}
          {!localMockModel && (
            <>
              <FormControl variant="outlined" sx={{ mx: 2 }}>
                <Select
                  value={selectedModelType}
                  onChange={(e) => setSelectedModelType(e.target.value)}
                  size="small"
                >
                  {allModelTypes.map((type) => (
                    <MenuItem key={type} value={type}>
                      {type}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl variant="outlined" sx={{ mr: 2 }}>
                <Select
                  value={selectedModelName}
                  onChange={(e) => handleModelChange(e.target.value)}
                  size="small"
                >
                  {allModelNames.map((name) => (
                    <MenuItem key={name} value={name}>
                      {name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </>
          )}

          <Typography variant="body2" sx={{ mr: 2 }}>
            Status: <span style={{ fontWeight: 'bold' }}>{workflowStatus || 'Unknown'}</span>
          </Typography>
          
          {currentPhase && (
            <Typography variant="body2" sx={{ mr: 2 }}>
              Phase: <span style={{ fontWeight: 'bold' }}>{currentPhase.phase_id || 'N/A'}</span>
            </Typography>
          )}
          
          <Box display="flex" alignItems="center" mr={2}>
            <Typography variant="body2" sx={{ mr: 1 }}>Interactive:</Typography>
            <Switch
              checked={localInteractiveMode}
              onChange={handleInteractiveModeToggle}
              color="primary"
              size="small"
              disabled={interactiveMode === false}
            />
          </Box>

          <Box display="flex" alignItems="center" mr={2}>
            <Typography variant="body2" sx={{ mr: 1 }}>Mock Model:</Typography>
            <Switch
              checked={localMockModel}
              onChange={handleMockModelToggle}
              color="primary"
              size="small"
            />
          </Box>
        </Box>
      </Box>

      {/* Main content */}
      <Box display="flex" flexGrow={1} overflow="hidden">
        <Box flexGrow={1} overflow="auto">
          <AgentInteractions
            interactiveMode={localInteractiveMode}
            workflowStatus={workflowStatus}
            currentPhase={currentPhase}
            isNextDisabled={isNextDisabled}
            phaseMessages={displayMessages}
            onUpdateMessageInput={handleUpdateMessageInput}
            onRunMessage={handleRunMessage}
            onTriggerNextIteration={triggerNextIteration}
            onStopWorkflow={handleStopWorkflow}
            onRestart={handleRestart}
            onToggleVersion={handleToggleVersion}
          />
        </Box>
        <Box className={`resource-panel ${isResourcePanelOpen ? 'open' : ''}`}>
          <IconButton
            className="toggle-panel"
            onClick={toggleResourcePanel}
            size="small"
          >
            {isResourcePanelOpen ? <ChevronRightIcon /> : <ChevronLeftIcon />}
          </IconButton>
          <ResourceDict resources={resources} />
        </Box>
      </Box>
    </Box>
  );
};