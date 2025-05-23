import React, { useEffect, useState } from 'react';
import { Box, Typography, Switch, FormControl, Select, MenuItem } from '@mui/material';
import { useNavigate } from 'react-router';

import { API_BASE_URL } from '../../config';

export const AppHeader = ({
  onInteractiveModeToggle,
  interactiveMode,
  selectedWorkflow,
  workflowStatus,
  currentPhase,
  onModelChange,
  onMockModelToggle, // New handler
  useMockModel, // New state

}) => {
  // Example options
  const [modelMapping, setModelMapping] = useState([]);

  // State for currently selected values
  const [selectedModelType, setSelectedModelType] = useState('');
  const [selectedModelName, setSelectedModelName] = useState('');
  

  // Initialize navigate
  const navigate = useNavigate();

// Fetch available models
useEffect(() => {
  const fetchModels = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/workflow/allmodels`);
      
      if (!response.ok) {
        console.error(`Failed to fetch models: ${response.status}`);
        setModelMapping([]); 
        return;
      }
      
      const models = await response.json();
      setModelMapping(models.allModels || []);
    } catch (err) {
      console.error('Failed to fetch models. Make sure the backend server is running.');
      setModelMapping([]);
    }
  };
  fetchModels();
}, []);

  // Extracting modelTypes (prefixes) whenever modelMapping changes
const allModelTypes = [...new Set((modelMapping || []).map(model => model?.name?.split('/')[0] || ''))];

  // Determine modelNames based on selectedModelType
const allModelNames = selectedModelType ? (modelMapping || [])
  .filter(model => model?.name?.startsWith(selectedModelType))  // Filter by selected model type
  .map(model => model?.name?.split('/')[1] || '') // Split the name and get the second part after "/"
  : [];

  // Effect to set defaults based on selectedWorkflow
  useEffect(() => {
    if (selectedWorkflow) {
      console.log("selectedworkflow", selectedWorkflow);
      const model = selectedWorkflow.model.split('/');
      setSelectedModelType(model[0]);
      setSelectedModelName(model[1]);
    }
  }, [selectedWorkflow]);

  const handleModelChange = async (name) => {
    setSelectedModelName(name); 
    const new_model_name = `${selectedModelType}/${name}`;
    try {
      await onModelChange(new_model_name);
    } catch (error) {
      console.log('Error updating action message:', error);
    }

  };
  
  // Navigate to home when Workflow Agent is clicked
  const handleHeaderClick = () => {
    navigate('/'); // Navigate to the homepage
  };
  
  return (
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
        sx={{ flexGrow: 1, cursor: 'pointer' }} 
        onClick={handleHeaderClick} 
      >
        Workflow Agent
      </Typography>
  
      <Box display="flex" alignItems="center">
        {selectedWorkflow && (
          <>
            {/* Hide model selection when Mock Mode is enabled */}
            {!useMockModel && selectedWorkflow.model && (
              <>
                <FormControl variant="outlined" sx={{ mr: 2 }}>
                  <Select
                    value={selectedModelType}
                    onChange={(e) => setSelectedModelType(e.target.value)}
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
                checked={!!interactiveMode}
                onChange={onInteractiveModeToggle}
                color="primary"
                size="small"
                disabled={!interactiveMode}
              />
            </Box>
      
            <Box display="flex" alignItems="center" mr={2}>
              <Typography variant="body2" sx={{ mr: 1 }}>Mock Model:</Typography>
              <Switch
                checked={!!useMockModel}
                onChange={onMockModelToggle}
                color="primary"
                size="small"
              />
            </Box>
          </>
        )}
      </Box>
    </Box>
  );
};
