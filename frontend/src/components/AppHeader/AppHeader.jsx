import React, { useEffect, useState } from 'react';
import { Box, Typography, Switch, FormControl, Select, MenuItem, TextField } from '@mui/material';
import { useNavigate } from 'react-router';

export const AppHeader = ({
  onInteractiveModeToggle,
  interactiveMode,
  selectedWorkflow,
  workflowStatus,
  currentPhase,
  onModelChange,
  onMaxIterationsChange,
}) => {
  // Example options
  const [modelMapping, setModelMapping] = useState([]);

  // State for currently selected values
  const [selectedModelType, setSelectedModelType] = useState('');
  const [selectedModelName, setSelectedModelName] = useState('');
  const [maxIterations, setMaxIterations] = useState(10);
  

  // Initialize navigate
  const navigate = useNavigate();

  // Fetch available models
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await fetch('http://localhost:8000/workflow/allmodels');
        const models = await response.json();

        setModelMapping(models.allModels);
        console.log(models.allModels)
      } catch (err) {
        console.log('Failed to fetch models. Make sure the backend server is running.');
      }
    };
    fetchModels();
  }, []);
    
  // Extracting modelTypes (prefixes) whenever modelMapping changes
  const allModelTypes = [...new Set(modelMapping.map(model => model.name.split('/')[0]))];

  // Determine modelNames based on selectedModelType
  const allModelNames = selectedModelType ? modelMapping
  .filter(model => model.name.startsWith(selectedModelType))  // Filter by selected model type
  .map(model => model.name.split('/')[1])  // Split the name and get the second part after "/"
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

  // Add effect to fetch max iterations when workflow is selected
  useEffect(() => {
    const fetchMaxIterations = async () => {
      if (selectedWorkflow) {
        try {
          const response = await fetch(`http://localhost:8000/workflow/${selectedWorkflow.id}/max-iterations`);
          if (response.ok) {
            const data = await response.json();
            setMaxIterations(data.max_iterations);
          }
        } catch (error) {
          console.error('Failed to fetch max iterations:', error);
        }
      }
    };
    fetchMaxIterations();
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

  const handleMaxIterationsChange = async (event) => {
    const value = event.target.value === '' ? '' : parseInt(event.target.value) || 1;
    try {
      if (value !== '') {  // Only update if there's a value
        setMaxIterations(value);
        if (onMaxIterationsChange) {
          await onMaxIterationsChange(value);
        }
      } else {
        setMaxIterations(''); // Allow empty field while typing
      }
    } catch (error) {
      console.error('Failed to update max iterations:', error);
      setMaxIterations(prevValue => prevValue); // Revert on error
    }
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
            {selectedWorkflow.model && (
              <>
                <FormControl variant="outlined" sx={{ mr: 2 }}>
                  <Select
                    value={selectedModelType}
                    onChange={(e) => setSelectedModelType(e.target.value)}
                    //displayEmpty
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
                    //displayEmpty
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
              <Typography variant="body2" sx={{ mr: 1 }}>Max Iterations:</Typography>
              <TextField
                type="number"
                size="small"
                value={maxIterations}
                onChange={(event) => {
                  // Just update local state while typing
                  const value = event.target.value === '' ? '' : parseInt(event.target.value) || 1;
                  setMaxIterations(value);
                }}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    if (maxIterations >= 1) {
                      onMaxIterationsChange(maxIterations);
                    }
                  }
                }}
                onBlur={() => {
                  if (!maxIterations || maxIterations < 1) {
                    setMaxIterations(1);
                    onMaxIterationsChange(1);
                  } else {
                    onMaxIterationsChange(maxIterations);
                  }
                }}
                inputProps={{ 
                  min: 1,
                  style: { 
                    padding: '4px 8px',
                    width: '60px',
                    color: 'white'
                  }
                }}
                sx={{
                  backgroundColor: 'rgba(255, 255, 255, 0.1)', // Semi-transparent background
                  borderRadius: 1,
                  '& .MuiOutlinedInput-root': {
                    height: '32px',
                    color: 'white', // Make text visible
                    '& fieldset': {
                      borderColor: 'rgba(255, 255, 255, 0.3)', // Lighter border
                    },
                    '&:hover fieldset': {
                      borderColor: 'rgba(255, 255, 255, 0.5)', // Lighter border on hover
                    },
                    '&.Mui-focused fieldset': {
                      borderColor: 'white', // White border when focused
                    }
                  },
                  '& input::-webkit-outer-spin-button, & input::-webkit-inner-spin-button': {
                    '-webkit-appearance': 'none',
                  }
                }}
              />
            </Box>

            <Box display="flex" alignItems="center" mr={2}>
              <Typography variant="body2" sx={{ mr: 1 }}>Interactive:</Typography>
              <Switch
                checked={interactiveMode}
                onChange={onInteractiveModeToggle}
                color="primary"
                size="small"
                disabled={!interactiveMode}
              />
            </Box>
          </>
        )}
      </Box>
    </Box>
  );
};
