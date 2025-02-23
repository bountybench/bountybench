import React from 'react';
import { TextField, MenuItem, Typography } from '@mui/material';

export const TaskSelectionSection = ({
  formData,
  handleInputChange,
  shouldShowBounty,
  shouldShowVulnerabilityType,
  vulnerabilityTypes
}) => {
  return (
    <>
      {shouldShowBounty(formData.workflow_name) && (
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
      )}

      {shouldShowBounty(formData.workflow_name) && (
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
      )}
      
      {shouldShowVulnerabilityType(formData.workflow_name) && (
        <>
          {vulnerabilityTypes && vulnerabilityTypes.length > 0 ? (
            <TextField
              select
              fullWidth
              label="Vulnerability Type (Optional)"
              name="vulnerability_type"
              value={formData.vulnerability_type}
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