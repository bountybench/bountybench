import React from 'react';
import { TextField, MenuItem, Button, Box, IconButton } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';

export const TaskSelectionSection = ({
  formData,
  handleInputChange,
  shouldShowBounty,
  shouldShowVulnerabilityType,
  vulnerabilityTypes,
  tasks,
  addTask,
  removeTask
}) => {

  const handleTaskDirChange = (index, taskDir) => {
    const selectedTask = tasks.find(task => task.task_dir === taskDir);
    const bountyNumbers = selectedTask ? selectedTask.bounty_nums : [];
    
    // Update bounty number state to selected one, as it will be empty initially
    handleInputChange({
      target: {
        name: `tasks[${index}].bounty_number`,
        value: bountyNumbers[0]
      }
    });
    
    // Update the task directory in the form input
    handleInputChange({
      target: {
        name: `tasks[${index}].task_dir`,
        value: taskDir
      }
    });
  };

  return (
    <>
      {shouldShowBounty(formData.workflow_name) && (
        <>
          {formData.tasks.map((task, index) => (
            <Box key={index} display="flex" alignItems="center" mb={2}>
              <TextField
                select
                label="Task Repository Directory"
                name={`tasks[${index}].task_dir`}
                value={task.task_dir || ''}
                onChange={(e) => handleTaskDirChange(index, e.target.value)}
                required
                margin="normal"
                sx={{ mr: 2, flexGrow: 1 }}
              >
                {tasks.length > 0 ? (
                    tasks.map(t => (
                      <MenuItem key={t.task_dir} value={t.task_dir}>
                        {t.task_dir}
                      </MenuItem>
                    ))
                  ) : (
                    <MenuItem value="" disabled>
                      <em>No task directories available</em>
                    </MenuItem>
                  )}
              </TextField>
              
              <TextField
                select
                label="Bounty Number"
                name={`tasks[${index}].bounty_number`}
                value={task.bounty_number}
                onChange={handleInputChange}
                required
                margin="normal"
                sx={{ mr: 2, width: '150px' }}
              >
                {tasks.find(t => t.task_dir === task.task_dir)?.bounty_nums.map(bountyNum => (
                  <MenuItem key={bountyNum} value={bountyNum}>
                    {bountyNum}
                  </MenuItem>
                )) || (
                  <MenuItem value="">
                    <em>No bounties available</em>
                  </MenuItem>
                )}
              </TextField>
              
              {index > 0 && (
                <IconButton onClick={() => removeTask(index)} color="error">
                  <DeleteIcon />
                </IconButton>
              )}
            </Box>
          ))}
          <Button
            startIcon={<AddIcon />}
            onClick={addTask}
            variant="outlined"
            sx={{ mt: 1, mb: 2 }}
          >
            Add Task
          </Button>
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
                <em>No vulnerability types available</em>
              </MenuItem>
            </TextField>
          )}
        </>
      )}
    </>
  );
};