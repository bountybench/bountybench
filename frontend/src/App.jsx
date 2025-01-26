import React, { useState, useEffect } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import { WorkflowDashboard } from './components/WorkflowDashboard/WorkflowDashboard';
import { WorkflowLauncher } from './components/WorkflowLauncher/WorkflowLauncher';
import { AppHeader } from './components/AppHeader/AppHeader'; 
import { darkTheme } from './theme';
import './App.css';

function App() {  
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [interactiveMode, setInteractiveMode] = useState(true);
  const [workflowStatus, setWorkflowStatus] = useState(null);
  const [currentPhase, setCurrentPhase] = useState(null);
  
  const handleWorkflowStart = (workflowId, isInteractive) => {
    setSelectedWorkflow({ id: workflowId });
    setInteractiveMode(isInteractive);
  };

  const handleInteractiveModeToggle = async () => {
    const newInteractiveMode = !interactiveMode;
    setInteractiveMode(newInteractiveMode);
    
    if (selectedWorkflow) {
      try {
        const response = await fetch(`http://localhost:8000/workflow/${selectedWorkflow.id}/interactive`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ interactive: newInteractiveMode }),
        });
        
        if (!response.ok) {
          throw new Error('Failed to update interactive mode');
        }
        console.log("Backend updated with new interactive mode:", newInteractiveMode);
      } catch (error) {
        // Don't just show on console, make it obvious to user in UI, e.g. SnackBar
        console.error("Error updating interactive mode:", error);
        setInteractiveMode(!newInteractiveMode); // Revert state on error
      }
    }
  };

  const handleWorkflowStateUpdate = (status, phase) => {
    setWorkflowStatus(status);
    setCurrentPhase(phase);
  };

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Box className="app-container" display="flex" flexDirection="column" height="100vh">
        <AppHeader 
          onInteractiveModeToggle={handleInteractiveModeToggle}
          interactiveMode={interactiveMode}
          selectedWorkflow={selectedWorkflow}
          workflowStatus={workflowStatus}
          currentPhase={currentPhase}
        />
        <Box flexGrow={1} overflow="auto">
          {selectedWorkflow ? (
            <WorkflowDashboard 
              selectedWorkflow={selectedWorkflow}
              interactiveMode={interactiveMode}
              onWorkflowStateUpdate={handleWorkflowStateUpdate}
            />
          ) : (
            <WorkflowLauncher 
              onWorkflowStart={handleWorkflowStart}
              interactiveMode={interactiveMode}
              setInteractiveMode={setInteractiveMode}
            />
          )}
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App;
