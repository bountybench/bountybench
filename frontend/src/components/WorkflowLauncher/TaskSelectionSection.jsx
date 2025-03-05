import React from 'react';
import { TextField, MenuItem, Typography, Button, Box, IconButton } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';

export const TaskSelectionSection = ({
  formData,
  handleInputChange,
  shouldShowBounty,
  shouldShowVulnerabilityType,
  vulnerabilityTypes,
  addTask,
  removeTask
}) => {
  return (
    <>
      {shouldShowBounty(formData.workflow_name) && (
        <>
          <Box display="flex" alignItems="center" mb={2}>
            <TextField
              label="Task Repository Directory"
              name="task_dir"
              value={formData.task_dir || ''}
              onChange={handleInputChange}
              required
              margin="normal"
              placeholder="e.g., astropy"
              sx={{ mr: 2, flexGrow: 1 }}
            />
            <TextField
              label="Bounty Number"
              name="bounty_number"
              value={formData.bounty_number || '0'}
              onChange={handleInputChange}
              required
              margin="normal"
              placeholder="e.g., 0"
              sx={{ mr: 2, width: '150px' }}
            />
          </Box>
        </>
      )}
      
      {shouldShowVulnerabilityType(formData.workflow_name) && (
        <>
          {vulnerabilityTypes && vulnerabilityTypes.length > 0 ? (
            <TextField
              select
              fullWidth
              label="Vulnerability Type (Optional)"
              name="vulnerability_type"
              value={formData.vulnerability_type || ''}
              onChange={handleInputChange}
              margin="normal"
            >
              {vulnerabilityTypes.map((type) => (
                <MenuItem key={type.value} value={type.value}>
                  {type.name}
                </MenuItem>
              ))}
            </TextField>
          ) : (
            <TextField
              select
              fullWidth
              label="Vulnerability Type (Optional)"
              name="vulnerability_type"
              value=""
              disabled
              margin="normal"
            >
              <MenuItem value="">
                <Typography>No vulnerability types available</Typography>
              </MenuItem>
            </TextField>
          )}
        </>
      )}
    </>
  );
};