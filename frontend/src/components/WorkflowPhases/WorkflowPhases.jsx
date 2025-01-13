import React from 'react';
import { Box, Typography, Stepper, Step, StepLabel, StepContent } from '@mui/material';
import './WorkflowPhases.css';

export const WorkflowPhases = ({ workflow }) => {
  const phases = [
    {
      label: 'Exploit Phase',
      description: 'Agents work to identify and exploit vulnerabilities',
      agents: ['ExecutorAgent', 'ExploitAgent'],
      status: 'active'
    },
    {
      label: 'Patch Phase',
      description: 'Develop and verify security patches',
      agents: ['ExecutorAgent', 'PatchAgent'],
      status: 'pending'
    }
  ];

  return (
    <Box className="phases-container">
      <Typography variant="h6" gutterBottom>
        Workflow Phases
      </Typography>
      
      <Stepper orientation="vertical" className="phases-stepper">
        {phases.map((phase, index) => (
          <Step 
            key={index} 
            active={phase.status === 'active'} 
            completed={phase.status === 'completed'}
          >
            <StepLabel className="phase-label">
              <Typography variant="subtitle1">{phase.label}</Typography>
            </StepLabel>
            <StepContent>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {phase.description}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Active Agents:
              </Typography>
              {phase.agents.map((agent, idx) => (
                <Typography key={idx} variant="caption" display="block" className="agent-name">
                  • {agent}
                </Typography>
              ))}
            </StepContent>
          </Step>
        ))}
      </Stepper>
    </Box>
  );
};
