import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router';
import {
  Box,
  CircularProgress,
  Alert,
  Typography,
  IconButton,
  FormControl,
  Select,
  MenuItem,
  Switch
} from '@mui/material';
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

export const WorkflowDashboard = ({
  workflowSettings = {},         // parent’s dictionary of toggles, per workflowId
  onUpdateWorkflowSettings,      // callback to update toggles in parent
  onWorkflowStateUpdate,         // callback to parent for status
  showInvalidWorkflowToast
}) => {
  const { workflowId } = useParams();
  const navigate = useNavigate();

  // Pull parent’s stored toggles for THIS workflow
  const parentSettings = workflowSettings[workflowId] || {};
  const {
    interactiveMode: parentInteractive = true,
    useMockModel: parentMock = false,
  } = parentSettings;

  // Local states for toggles
  const [localInteractiveMode, setLocalInteractiveMode] = useState(parentInteractive);
  const [localMockModel, setLocalMockModel] = useState(parentMock);

  // DEBUG: see what the parent gave us initially
  useEffect(() => {
    console.log(`DEBUG: [WorkflowDashboard] MOUNT for workflowId=${workflowId}`);
    console.log('DEBUG: parentSettings => ', parentSettings);
    console.log('DEBUG: parentInteractive => ', parentInteractive);
    console.log('DEBUG: parentMock => ', parentMock);
  }, [workflowId]);

  // If parent changes them after the fact, sync local
  useEffect(() => {
    console.log('DEBUG: [useEffect] parentInteractive changed => ', parentInteractive);
    setLocalInteractiveMode(parentInteractive);
  }, [parentInteractive]);

  useEffect(() => {
    console.log('DEBUG: [useEffect] parentMock changed => ', parentMock);
    setLocalMockModel(parentMock);
  }, [parentMock]);

  // WebSocket + workflow data
  const [workflowState, setWorkflowState] = useState({
    status: WorkflowState.LOADING,
    message: "Loading workflow instance...",
    error: null
  });

  const [isNextDisabled, setIsNextDisabled] = useState(false);
  const [hasCheckedValidity, setHasCheckedValidity] = useState(false);
  const [preservedMessages, setPreservedMessages] = useState([]);
  const [resources, setResources] = useState([]);
  const [isResourcePanelOpen, setIsResourcePanelOpen] = useState(false);
  const [restart, setRestart] = useState(0);

  // For model selection
  const [modelMapping, setModelMapping] = useState([]);
  const [selectedModelType, setSelectedModelType] = useState('');
  const [selectedModelName, setSelectedModelName] = useState('');
  

  // Confirm the workflowId is valid
  useEffect(() => {
    const checkIfWorkflowExists = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/workflow/active`);
        const data = await response.json();
        const exists = data.active_workflows.some(w => w.id === workflowId);
        if (!exists) {
          showInvalidWorkflowToast?.();
          navigate(`/`);
        }
      } catch (err) {
        console.error("Error checking if workflow exists:", err);
      }
    };

    if (!hasCheckedValidity) {
      checkIfWorkflowExists();
      setHasCheckedValidity(true);
    }
  }, [workflowId, navigate, showInvalidWorkflowToast, hasCheckedValidity]);


  useEffect(() => {
    async function fetchRealToggles() {
      try {
        // Some new endpoint that returns { use_mock_model: boolean, interactive: boolean }
        const res = await fetch(`${API_BASE_URL}/workflow/${workflowId}/config`);
        if (!res.ok) {
          console.error(`Failed to fetch toggles for ${workflowId}:`, await res.text());
          return;
        }
        const data = await res.json();
        console.log("DEBUG: Loaded real toggles from server =>", data);
  
        // Now set local states accordingly
        setLocalMockModel(data.use_mock_model);
        setLocalInteractiveMode(data.interactive);
  
        // Optionally also update the parent's dictionary
        onUpdateWorkflowSettings?.(workflowId, {
          interactiveMode: data.interactive,
          useMockModel: data.use_mock_model,
        });
      } catch (err) {
        console.error("Error fetching real toggles:", err);
      }
    }
  
    fetchRealToggles();
  }, [workflowId]);
  

  // Connect to WebSocket
  const {
    isConnected,
    workflowStatus,
    currentPhase,
    phaseMessages,
    error
  } = useWorkflowWebSocket(workflowId, restart);

  // DEBUG: see WebSocket events
  useEffect(() => {
    console.log('DEBUG: WebSocket state changed => ', {
      isConnected,
      workflowStatus,
      currentPhase,
      phaseMessagesCount: phaseMessages?.length,
      error
    });
  }, [isConnected, workflowStatus, currentPhase, phaseMessages, error]);

  // Fetch the complete model list
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/workflow/allmodels`);
        const models = await response.json();
        setModelMapping(models.allModels);
      } catch (err) {
        console.log('Failed to fetch models. Make sure the backend is running.', err);
      }
    };
    fetchModels();
  }, []);

  // Derive selectedModelType / selectedModelName from currentPhase.model if present
  useEffect(() => {
    if (currentPhase && currentPhase.model) {
      const [type, name] = currentPhase.model.split('/');
      if (type && name) {
        setSelectedModelType(type);
        setSelectedModelName(name);
      }
    }
  }, [currentPhase]);

  const allModelTypes = [...new Set(modelMapping.map(m => m.name.split('/')[0]))];
  const allModelNames = selectedModelType
    ? modelMapping
        .filter(m => m.name.startsWith(selectedModelType))
        .map(m => m.name.split('/')[1])
    : [];

  // Model change
  const handleModelChange = async (newName) => {
    console.log('DEBUG: handleModelChange => newName=', newName);
    setSelectedModelName(newName);
    const newModel = `${selectedModelType}/${newName}`;

    if (!workflowId) return;
    try {
      const requestBody = {
        new_model_name: newModel,
        use_mock_model: localMockModel
      };

      console.log('DEBUG: POST /model-change => ', requestBody);
      const response = await fetch(`${API_BASE_URL}/workflow/${workflowId}/model-change`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      console.log('Model updated successfully to:', newModel);
    } catch (error) {
      console.error('Error updating model:', error);
    }
  };

  // Toggle Interactive
  const handleInteractiveModeToggle = async () => {
    if (!workflowId) return;
    const newVal = !localInteractiveMode;
    console.log('DEBUG: Toggling interactiveMode => ', newVal);

    try {
      setLocalInteractiveMode(newVal); // optimistically update UI

      const response = await fetch(`${API_BASE_URL}/workflow/${workflowId}/interactive`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interactive: newVal })
      });
      if (!response.ok) {
        throw new Error('Failed to update interactive mode');
      }

      console.log('DEBUG: interactiveMode updated on backend => ', newVal);

      // Now let the parent store it
      onUpdateWorkflowSettings?.(workflowId, { interactiveMode: newVal });
      // Also call parent's workflow state update if needed
      onWorkflowStateUpdate?.(workflowStatus, currentPhase);
    } catch (err) {
      console.error('Error updating interactive mode:', err);
      // revert
      setLocalInteractiveMode(!newVal);
    }
  };

  // Toggle Mock Model
  const handleMockModelToggle = async () => {
    if (!workflowId) return;
    
    // Log current state before toggling
    console.log('DEBUG: Current mockModel state before toggle =>', localMockModel);
    
    // Calculate new value by inverting current state
    const newVal = !localMockModel;
    console.log('DEBUG: Toggling mockModel to =>', newVal);
  
    try {
      // 1. Update local state first for immediate UI feedback
      setLocalMockModel(newVal);
      console.log('DEBUG: Local state updated to =>', newVal);
  
      // 2. Send the update to the server with proper error handling
      console.log('DEBUG: Sending to server:', { use_mock_model: newVal });
      const response = await fetch(`${API_BASE_URL}/workflow/${workflowId}/mock-model`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ use_mock_model: newVal })
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Server error: ${response.status} - ${errorText}`);
        throw new Error('Failed to update mock model setting');
      }
  
      const data = await response.json();
      console.log('DEBUG: Server response =>', data);
  
      // 3. Update parent state
      console.log('DEBUG: Updating parent state with =>', { useMockModel: newVal });
      onUpdateWorkflowSettings?.(workflowId, { useMockModel: newVal });
      
      // 4. Notify parent about workflow state update
      onWorkflowStateUpdate?.(workflowStatus, currentPhase);
      
      
    } catch (error) {
      console.error('Error updating mock model:', error);
      // Revert local state if server update fails
      console.log('DEBUG: Error occurred, reverting local state to =>', !newVal);
      setLocalMockModel(!newVal);
    }
  };

  // Overall workflow state
  useEffect(() => {
    if (error) {
      setWorkflowState({
        status: WorkflowState.ERROR,
        message: "An error occurred",
        error
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
        message: "Starting workflow...",
        error: null
      });
    } else if (workflowStatus === 'restarting') {
      setWorkflowState({
        status: WorkflowState.RESTARTING,
        message: "Workflow restarting...",
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

    // Let the parent know about the new status
    onWorkflowStateUpdate?.(workflowStatus, currentPhase);
    console.log('DEBUG: Updated local workflowState => ', workflowStatus);
  }, [isConnected, workflowStatus, currentPhase, phaseMessages, error, onWorkflowStateUpdate]);

  // Resource fetching
  const fetchResources = useCallback(async () => {
    if (!workflowId) return;
    console.log('DEBUG: fetchResources => workflowId=', workflowId);
    try {
      const response = await fetch(`${API_BASE_URL}/workflow/${workflowId}/resources`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setResources(data.resources);
      console.log('DEBUG: resources => ', data.resources);
    } catch (error) {
      console.error('Error fetching resources:', error);
    }
  }, [workflowId]);

  // fetch resources whenever phase changes or mock changes
  useEffect(() => {
    console.log('DEBUG: [useEffect] re-fetching resources => phaseMessages or localMockModel changed');
    fetchResources();
  }, [phaseMessages, localMockModel, fetchResources]);

  const toggleResourcePanel = () => {
    setIsResourcePanelOpen(!isResourcePanelOpen);
  };

  // Identify tail message for next iteration
  const getTailMessageId = async () => {
    if (!phaseMessages?.length) return null;
    const lastPhase = phaseMessages[phaseMessages.length - 1];
    if (!lastPhase.current_children?.length) return null;

    const lastMessage = lastPhase.current_children[lastPhase.current_children.length - 1];
    return lastMessage.current_id;
  };

  // Next iteration
  const triggerNextIteration = async () => {
    if (workflowStatus === "stopped") {
      console.error("Cannot trigger next iteration: Workflow is stopped.");
      return;
    }
    if (!workflowId) {
      console.error('Workflow ID is not available');
      return;
    }
    setIsNextDisabled(true);
    try {
      const currentMessageId = await getTailMessageId();
      console.log('DEBUG: currentMessageId => ', currentMessageId);
      if (!currentMessageId) {
        console.warn("No tail message to run.");
        return;
      }
      const response = await fetch(`${API_BASE_URL}/workflow/${workflowId}/run-message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message_id: currentMessageId })
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      console.log('Next iteration triggered successfully:', data);
    } catch (error) {
      console.error('Error triggering next iteration:', error);
    } finally {
      setIsNextDisabled(false);
    }
  };

  // Update a message’s input
  const handleUpdateMessageInput = async (messageId, newInputData) => {
    if (!workflowId) return;
    console.log('DEBUG: handleUpdateMessageInput => ', { messageId, newInputData });
    setIsNextDisabled(true);

    try {
      const response = await fetch(`${API_BASE_URL}/workflow/${workflowId}/edit-message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message_id: messageId, new_input_data: newInputData })
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

  // Re-run a particular message
  const handleRunMessage = async (messageId) => {
    if (!workflowId) return;
    console.log('DEBUG: handleRunMessage => ', messageId);
    setIsNextDisabled(true);

    try {
      const response = await fetch(`${API_BASE_URL}/workflow/${workflowId}/run-message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message_id: messageId })
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
  };

  // Stop workflow
  const handleStopWorkflow = async () => {
    if (!workflowId) return;
    console.log('DEBUG: handleStopWorkflow => workflowId=', workflowId);
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
  };

  // Restart workflow
  const handleRestart = async () => {
    if (!workflowId) return;
    console.log('DEBUG: handleRestart => workflowId=', workflowId);
    try {
      const response = await fetch(`${API_BASE_URL}/workflow/restart/${workflowId}`, {
        method: 'POST'
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      console.log('Workflow restarted successfully');
    } catch (error) {
      console.error('Error restarting workflow:', error);
    } finally {
      setRestart(prev => prev + 1);
    }
  };

  // Toggle version
  const handleToggleVersion = useCallback(async (messageId, direction) => {
    if (!workflowId) return;
    console.log('DEBUG: handleToggleVersion => ', { messageId, direction });
    try {
      const response = await fetch(`${API_BASE_URL}/workflow/${workflowId}/toggle-version`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message_id: messageId, direction })
      });
      if (!response.ok) {
        throw new Error('Failed to toggle version');
      }
      const result = await response.json();
      console.log('Toggle version result => ', result);
      // The updated messages usually arrive via WebSocket
    } catch (error) {
      console.error('Error toggling version:', error);
    }
  }, [workflowId]);

  // Display logic
  if (workflowState.status === WorkflowState.ERROR) {
    return (
      <Box p={2}>
        <Alert severity="error">{workflowState.error || workflowState.message}</Alert>
      </Box>
    );
  }

  if (
    workflowState.status === WorkflowState.LOADING ||
    workflowState.status === WorkflowState.CONNECTING ||
    workflowState.status === WorkflowState.STARTING ||
    workflowState.status === WorkflowState.RESTARTING
  ) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="100%">
        <Box className="launcher-loading" display="flex" flexDirection="column" alignItems="center">
          <CircularProgress />
          <Typography>{workflowState.message}</Typography>
        </Box>
      </Box>
    );
  }

  // If workflow completed, show preserved messages
  const displayMessages = workflowState.status === WorkflowState.COMPLETED
    ? preservedMessages
    : phaseMessages;

  return (
    <Box height="100%" overflow="hidden" display="flex" flexDirection="column">
      {/* Dashboard Header */}
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
          {!localMockModel && (
            <>
              <FormControl variant="outlined" sx={{ mx: 2 }}>
                <Select
                  value={selectedModelType}
                  onChange={(e) => {
                    console.log('DEBUG: setSelectedModelType => ', e.target.value);
                    setSelectedModelType(e.target.value);
                  }}
                  size="small"
                >
                  {allModelTypes.map(type => (
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
                  {allModelNames.map(name => (
                    <MenuItem key={name} value={name}>
                      {name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </>
          )}

          <Typography variant="body2" sx={{ mr: 2 }}>
            Status: <strong>{workflowStatus || 'Unknown'}</strong>
          </Typography>
          
          {currentPhase && (
            <Typography variant="body2" sx={{ mr: 2 }}>
              Phase: <strong>{currentPhase.phase_id || 'N/A'}</strong>
            </Typography>
          )}

          {/* Interactive Toggle */}
          <Box display="flex" alignItems="center" mr={2}>
            <Typography variant="body2" sx={{ mr: 1 }}>Interactive:</Typography>
            <Switch
              checked={localInteractiveMode}
              onChange={handleInteractiveModeToggle}
              color="primary"
              size="small"
            />
          </Box>

          {/* Mock Model Toggle */}
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

        {/* Resource Panel */}
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
